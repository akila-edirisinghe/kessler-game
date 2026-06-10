# -*- coding: utf-8 -*-
# Copyright © 2022 Thales. All Rights Reserved.

from src.kesslergame import KesslerController
from typing import Dict, Tuple
from impact_time_cal import predict_collision, solve_quadratic
import math, json, time

# ── Print / logging config ───────────────────────────────────────────────────
PRINT_EXPLANATION = True
NO_PRINTS         = False

_last_print_time           = 0.0
_last_firing_print_time    = 0.0
_last_mine_drop_print_time = 0.0
_print_interval            = 1.0
_firing_print_interval     = 3.0
_mine_dropped_last         = False


def log_explanation(message: str):
    global _last_print_time, _last_firing_print_time, _last_mine_drop_print_time, _mine_dropped_last
    if NO_PRINTS:
        return

    message_lower = message.lower()
    is_mine_drop  = "mine"   in message_lower
    is_firing     = "action" in message_lower or "decision" in message_lower
    current_time  = time.time()

    if PRINT_EXPLANATION:
        if is_mine_drop:
            if not _mine_dropped_last:
                print(message)
                _last_mine_drop_print_time = current_time
                _mine_dropped_last = True
        else:
            _mine_dropped_last = False
            if is_firing:
                if current_time - _last_firing_print_time >= _firing_print_interval:
                    print(message)
                    _last_firing_print_time = current_time
            else:
                if current_time - _last_print_time >= _print_interval:
                    print(message)
                    _last_print_time = current_time
    else:
        with open('explanations_akila.txt', 'a+') as f:
            f.write(message + '\n')


# ── Analytic bullet intercept ────────────────────────────────────────────────
def aim_intercept(ship_pos: tuple, asteroid: dict,
                  bullet_speed_px_per_frame: float) -> tuple:
    """
    Solves exactly for where a bullet fired from ship_pos at speed B px/frame
    will meet an asteroid moving at (avx, avy) px/s.

    Math: let dx = ax-sx, dy = ay-sy, avx/avy in px/FRAME (divide by 30).
    We need: (dx + avx*t)^2 + (dy + avy*t)^2 = (B*t)^2
    => (avx^2 + avy^2 - B^2)*t^2 + 2*(dx*avx + dy*avy)*t + (dx^2 + dy^2) = 0

    Uses solve_quadratic from impact_time_cal.py.
    Returns (angle_deg, tof_frames, intercept_x, intercept_y).

    angle_deg is a raw atan2 result in (-180, 180] — do NOT apply % 360.
    The turn logic uses angle_diff() which already handles wrap-around.
    """
    sx, sy = ship_pos
    ax, ay = asteroid["position"]
    # convert px/s → px/frame
    avx = asteroid["velocity"][0] / 30.0
    avy = asteroid["velocity"][1] / 30.0
    B   = bullet_speed_px_per_frame

    dx = ax - sx
    dy = ay - sy

    a_coef = avx * avx + avy * avy - B * B
    b_coef = 2.0 * (dx * avx + dy * avy)
    c_coef = dx * dx + dy * dy

    t1, t2 = solve_quadratic(a_coef, b_coef, c_coef)

    # Pick smallest positive root
    tof = None
    for t in (t1, t2):
        if not math.isnan(t) and t > 0.0:
            if tof is None or t < tof:
                tof = t

    # Fallback for stationary asteroid or numerical edge case
    if tof is None or tof <= 0.0:
        dist = math.sqrt(dx * dx + dy * dy)
        tof  = dist / B if B > 0.0 else 1.0

    ix    = ax + avx * tof
    iy    = ay + avy * tof
    # IMPORTANT: return raw atan2, do NOT wrap to [0, 360).
    # angle_diff() handles the [-180, 180] range correctly for turn direction.
    angle = math.degrees(math.atan2(iy - sy, ix - sx))
    return angle, tof, ix, iy


# ── Shortest signed angular difference ──────────────────────────────────────
def angle_diff(target_deg: float, current_deg: float) -> float:
    """
    Signed shortest path from current_deg to target_deg.
    Result is always in [-180, 180].
    Works correctly for all values including near 0/360 wraparound.
    """
    return (target_deg - current_deg + 180.0) % 360.0 - 180.0


# ── Impact-time frames from predict_collision interval ───────────────────────
def impact_frames(interval: tuple) -> float:
    """
    Convert (t_start, t_end) seconds to frames for the fuzzy table.
    0    = currently colliding / always colliding
    300  = no future collision
    t*30 = frames until impact (capped at 300)
    """
    t0, t1 = interval
    if math.isinf(t0):   return 0.0    # permanently inside
    if math.isnan(t0):   return 300.0  # no collision
    if t0 <= 0.0 <= t1:  return 0.0    # currently colliding
    if t1 <= 0.0:        return 300.0  # collision already passed
    return min(t0 * 30.0, 300.0)


# ── Main Controller ──────────────────────────────────────────────────────────
class AkilaController(KesslerController):

    def __init__(self):
        self.delay                  = 0
        self.asteroids_shot         = []
        self.rest_counter           = 0
        self.lookup_table           = {}
        self.prev_best_ast          = None
        self.last_logged_target_pos = None

        with open('priorty_lookup_table.json', 'r') as f:
            self.lookup_table = json.load(f)

        # 800 px/s bullet at 30 fps
        self.bsf = 800.0 / 30.0

    # ── Fuzzy lookup ─────────────────────────────────────────────────────────
    def get_fuzzy_values(self, size: int, impact_time: int, turn_time: int) -> float:
        impact_time = min(impact_time, 300)
        turn_time   = min(turn_time,   29)   # table keys only go 0-29
        key = f"{size},{impact_time},{turn_time}"
        return self.lookup_table.get(key, 1.0)

    # ── Main action method ────────────────────────────────────────────────────
    def actions(self, ship_state: Dict, game_state: Dict) -> Tuple[float, float, bool, bool]:

        current_frame = game_state["frame"]

        if game_state["time"] == 0:
            self.delay                  = 0
            self.asteroids_shot         = []
            self.rest_counter           = 0
            self.prev_best_ast          = None
            self.last_logged_target_pos = None

        ship_pos  = ship_state['position']
        heading   = ship_state['heading']
        fire      = False
        drop_mine = False

        best_ast            = None
        highest_prio        = -math.inf
        found_prev_best_ast = False

        # Prune expired shot records
        self.asteroids_shot = [
            a for a in self.asteroids_shot
            if a["sim_frame"] > current_frame
        ]

        # ── Score every un-shot asteroid ──────────────────────────────────────
        for asteroid in game_state['asteroids']:

            already_shot = any(
                s["velocity"] == asteroid["velocity"] and s["size"] == asteroid["size"]
                for s in self.asteroids_shot
            )
            if already_shot:
                continue

            asteroid_size        = asteroid['size']
            impact_time_interval = predict_collision(
                ship_pos, (0, 0), 20,
                asteroid['position'], asteroid['velocity'], asteroid['radius']
            )
            imp_time = impact_frames(impact_time_interval)

            # Analytic intercept angle for turn_time estimate
            aim_angle, tof, _, _ = aim_intercept(ship_pos, asteroid, self.bsf)
            diff      = abs(angle_diff(aim_angle, heading))
            turn_time = min(round(diff / 6.0), 29)

            priority = round(self.get_fuzzy_values(
                asteroid_size, round(imp_time), turn_time
            ))

            # Mine drop: asteroid about to hit us within 7 frames
            if (not ship_state["is_respawning"]
                    and ship_state["mines_remaining"] > 0
                    and imp_time != 0.0
                    and impact_time_interval[0] > 0
                    and impact_time_interval[1] > 0
                    and imp_time <= 7.0):
                drop_mine = True

            # Track whether this is the same asteroid as last frame
            if self.prev_best_ast is not None:
                pa     = self.prev_best_ast
                pred_x = pa["position"][0] + pa["velocity"][0] / 30.0
                pred_y = pa["position"][1] + pa["velocity"][1] / 30.0
                if (math.isclose(pred_x, asteroid["position"][0], abs_tol=1.0)
                        and math.isclose(pred_y, asteroid["position"][1], abs_tol=1.0)
                        and pa["size"] == asteroid["size"]):
                    prev_prio                      = pa["priority"]
                    self.prev_best_ast             = asteroid.dict
                    self.prev_best_ast["priority"] = prev_prio
                    found_prev_best_ast            = True

            if best_ast is None or priority > highest_prio:
                best_ast     = asteroid.dict
                highest_prio = priority

        # ── No asteroids remaining ────────────────────────────────────────────
        if best_ast is None:
            if self.delay == 1:
                fire = True
                log_explanation("[Action] Fired a bullet (default behavior, no target)")
                self.delay = 0
            return 0, 0, fire, False

        best_ast["priority"] = highest_prio

        # ── Target selection / logging ────────────────────────────────────────
        if not found_prev_best_ast:
            pos_key = tuple(best_ast["position"])
            if self.last_logged_target_pos != pos_key:
                log_explanation(
                    f"[Target] New asteroid at "
                    f"{tuple(round(x,1) for x in best_ast['position'])} "
                    f"priority={highest_prio}"
                )
                self.last_logged_target_pos = pos_key
            self.prev_best_ast = best_ast
        else:
            if abs(self.prev_best_ast["priority"] - best_ast["priority"]) <= 1:
                best_ast = self.prev_best_ast
                log_explanation(
                    f"[Decision] Holding target at "
                    f"({round(best_ast['position'][0],1):.2f}, "
                    f"{round(best_ast['position'][1],1):.2f})"
                )
            else:
                pos_key = tuple(best_ast["position"])
                if self.last_logged_target_pos != pos_key:
                    log_explanation(
                        f"[Target] Switching → priority={highest_prio} at "
                        f"{tuple(round(x,1) for x in best_ast['position'])}"
                    )
                    self.last_logged_target_pos = pos_key
                self.prev_best_ast = best_ast

        # ── Analytic intercept for the chosen target ──────────────────────────
        aim_angle, tof, ix, iy = aim_intercept(ship_pos, best_ast, self.bsf)

        # aim_angle is raw atan2 in (-180, 180] — pass directly to angle_diff.
        # Do NOT apply % 360 here; that is the bug that broke near-0° targets.
        diff     = angle_diff(aim_angle, heading)   # signed, in [-180, 180]
        abs_diff = abs(diff)

        # ── Turn rate ─────────────────────────────────────────────────────────
        if abs_diff > 6.0:
            turn_rate = math.copysign(180.0, diff)
        else:
            # Proportional slow-down as we close in on the target angle
            turn_rate = 30.0 * diff

            # Aligned — arm fire delay
            if current_frame - self.rest_counter >= 2:
                self.delay = 1
                if best_ast is not None:
                    record              = dict(best_ast)
                    record["sim_frame"] = current_frame + int(tof) + 5
                    self.asteroids_shot.append(record)

        # ── Fire ──────────────────────────────────────────────────────────────
        if self.delay == 1:
            self.rest_counter = current_frame
            fire       = True
            self.delay = 0

        # Suppress fire while respawn-invulnerable
        if ship_state["is_respawning"]:
            fire = False

        # ── Logging ──────────────────────────────────────────────────────────
        if fire:
            log_explanation(
                f"[Action] Firing → intercept ({round(ix,1):.1f}, {round(iy,1):.1f}) "
                f"tof={tof:.1f}f err={abs_diff:.2f}°"
            )
        else:
            log_explanation(
                f"[Decision] Turning, err={abs_diff:.1f}° "
                f"aim={aim_angle:.1f}° heading={heading:.1f}°"
            )

        if drop_mine:
            log_explanation(
                f"[Action] Dropping mine, asteroid at "
                f"{tuple(round(x,1) for x in best_ast['position'])}"
            )

        return 0, turn_rate, fire, drop_mine

    @property
    def name(self) -> str:
        return "hitormiss v1.0"

    @property
    def custom_sprite_path(self) -> str:
        return "akila's turtle fortress spaceship sprite.png"