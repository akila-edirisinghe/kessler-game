# -*- coding: utf-8 -*-
# Copyright © 2022 Thales. All Rights Reserved.

from src.kesslergame import KesslerController
from typing import Dict, Tuple
from impact_time_cal import predict_collision
import math, json, time

# ── Print / logging config ───────────────────────────────────────────────────
PRINT_EXPLANATION = True
NO_PRINTS         = False

_last_print_time           = 0.0
_last_firing_print_time    = 0.0
_last_mine_drop_print_time = 0.0
_print_interval            = 1.0
_firing_print_interval     = 3.0
_mine_drop_cooldown        = 10.0
_mine_dropped_last         = False


def log_explanation(message: str):
    global _last_print_time, _last_firing_print_time, _last_mine_drop_print_time, _mine_dropped_last
    if NO_PRINTS:
        return

    message_lower = message.lower()
    is_mine_drop  = "mine"     in message_lower
    is_firing     = "action"   in message_lower or "decision" in message_lower
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


# ── Iterative intercept ──────────────────────────────────────────────────────
def predict_intercept(ship_pos: tuple, asteroid: dict,
                      bullet_speed_per_frame: float,
                      iterations: int = 4) -> tuple:
    """
    Returns (future_x, future_y, time_bullet_frames).

    Iteratively refines the intercept point:
      1. Estimate travel time to current asteroid position.
      2. Project asteroid forward by that time.
      3. Re-estimate travel time to the new projected position.
      4. Repeat until converged (4 iterations is enough for any speed).

    No +1 fudge-factor needed — the iteration handles moving targets correctly.
    """
    ax, ay   = asteroid["position"]
    avx, avy = asteroid["velocity"]

    dist = math.sqrt((ax - ship_pos[0])**2 + (ay - ship_pos[1])**2)
    t    = dist / bullet_speed_per_frame      # frames

    for _ in range(iterations):
        # asteroid velocity is px/s; divide by 30 to get px/frame
        fx = ax + t * (avx / 30.0)
        fy = ay + t * (avy / 30.0)
        new_dist = math.sqrt((fx - ship_pos[0])**2 + (fy - ship_pos[1])**2)
        t = new_dist / bullet_speed_per_frame

    fx = ax + t * (avx / 30.0)
    fy = ay + t * (avy / 30.0)
    return fx, fy, t


# ── Shortest signed angular difference ──────────────────────────────────────
def angle_diff(target_deg: float, current_deg: float) -> float:
    """Signed shortest path from current_deg to target_deg, result in [-180, 180]."""
    return (target_deg - current_deg + 180.0) % 360.0 - 180.0


# ── Impact-time frames from predict_collision interval ───────────────────────
def impact_frames(interval: tuple) -> float:
    """
    Convert a (t_start, t_end) collision interval (seconds) to frames.
    Returns:
      0    — currently colliding / permanently inside
      300  — no future collision
      t_start*30 — future collision, capped at 300
    """
    t0, t1 = interval
    if math.isinf(t0):   return 0.0
    if math.isnan(t0):   return 300.0
    if t0 <= 0.0 <= t1:  return 0.0
    if t1 <= 0.0:        return 300.0
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

        # bullet speed in pixels-per-frame  (800 px/s ÷ 30 fps)
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

        # Reset everything at scenario start
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

        # ── Prune expired shot records ────────────────────────────────────────
        self.asteroids_shot = [
            a for a in self.asteroids_shot
            if a["sim_frame"] > current_frame
        ]

        # ── Score every un-shot asteroid ──────────────────────────────────────
        for asteroid in game_state['asteroids']:

            # Skip if we already have a bullet en-route to this asteroid
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

            # Collision interval → frame count safe for fuzzy table
            imp_time = impact_frames(impact_time_interval)

            # Iterative intercept for turn-time estimate
            fx, fy, t_bullet = predict_intercept(ship_pos, asteroid, self.bsf)
            desired_angle    = math.degrees(math.atan2(fy - ship_pos[1], fx - ship_pos[0]))

            # Shortest-path angular error → turn_time in frames
            diff      = abs(angle_diff(desired_angle, heading))
            turn_time = min(round(diff / 6.0), 29)

            # Fuzzy priority
            priority = round(self.get_fuzzy_values(
                asteroid_size, round(imp_time), turn_time
            ))

            # Mine logic: drop when asteroid is about to hit us
            if (not ship_state["is_respawning"]
                    and ship_state["mines_remaining"] > 0
                    and imp_time != 0.0
                    and impact_time_interval[0] > 0
                    and impact_time_interval[1] > 0
                    and imp_time <= 7.0):
                drop_mine = True

            # Check if this is the same asteroid we targeted last frame
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
                    f"[Target] New asteroid selected at "
                    f"{tuple(round(x,1) for x in best_ast['position'])} "
                    f"with priority {highest_prio}"
                )
                self.last_logged_target_pos = pos_key
            self.prev_best_ast = best_ast
        else:
            if abs(self.prev_best_ast["priority"] - best_ast["priority"]) <= 1:
                best_ast = self.prev_best_ast
                log_explanation(
                    f"[Decision] Staying on target at "
                    f"({round(best_ast['position'][0],1):.2f}, "
                    f"{round(best_ast['position'][1],1):.2f}) "
                    f"— priority change insignificant "
                    f"({best_ast['priority']} vs {self.prev_best_ast['priority']})"
                )
            else:
                pos_key = tuple(best_ast["position"])
                if self.last_logged_target_pos != pos_key:
                    log_explanation(
                        f"[Target] Switching to new higher-priority asteroid at "
                        f"{tuple(round(x,1) for x in best_ast['position'])}"
                    )
                    self.last_logged_target_pos = pos_key
                self.prev_best_ast = best_ast

        # ── Compute firing angle with iterative intercept ─────────────────────
        fx, fy, t_bullet = predict_intercept(ship_pos, best_ast, self.bsf)

        desired_angle  = math.degrees(math.atan2(fy - ship_pos[1], fx - ship_pos[0]))
        desired_angle %= 360.0      # normalise to [0, 360)

        # ── Turn rate using signed shortest-path diff ─────────────────────────
        diff     = angle_diff(desired_angle, heading)   # signed, [-180, 180]
        abs_diff = abs(diff)

        if abs_diff > 6.0:
            # Full-speed turn in the correct direction
            turn_rate = math.copysign(180.0, diff)
        else:
            # Proportional slow-down as we close on the target angle
            turn_rate = 30.0 * diff

            # Aligned — arm the delay so we fire on the next eligible frame
            if current_frame - self.rest_counter >= 2:
                self.delay = 1
                if best_ast is not None:
                    record              = dict(best_ast)
                    record["sim_frame"] = current_frame + int(t_bullet) + 5
                    self.asteroids_shot.append(record)

        # ── Fire when delay has been armed ────────────────────────────────────
        if self.delay == 1:
            self.rest_counter = current_frame
            fire       = True
            self.delay = 0

        thrust = 0

        # Suppress fire while respawn-invulnerable
        if ship_state["is_respawning"]:
            fire = False

        # ── Logging ──────────────────────────────────────────────────────────
        if fire:
            log_explanation(
                f"[Action] Firing at asteroid at predicted position "
                f"({round(fx,1):.1f}, {round(fy,1):.1f})"
            )
        else:
            log_explanation("[Decision] Holding fire — no valid target or wrong angle")

        if drop_mine:
            log_explanation(
                f"[Action] Dropping mine for asteroid at "
                f"{tuple(round(x,1) for x in best_ast['position'])}"
            )

        return thrust, turn_rate, fire, drop_mine

    @property
    def name(self) -> str:
        return "hitormiss v1.0"

    @property
    def custom_sprite_path(self) -> str:
        return "akila's turtle fortress spaceship sprite.png"