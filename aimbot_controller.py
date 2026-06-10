# -*- coding: utf-8 -*-
# Aimbot controller for Kessler Game
# Uses fuzzy-logic priority targeting + analytic bullet intercept.

from src.kesslergame import KesslerController
from typing import Dict, Tuple
from impact_time_cal import predict_collision, solve_quadratic
import math, json

# ─────────────────────────────────────────────────────────────────────────────
# KESSLER COORDINATE SYSTEM (confirmed from scenario source)
#
#   Screen coords: x increases RIGHT, y increases DOWNWARD.
#   Angles (heading, asteroid angle): CW from east (right).
#     angle=0   → rightward   (+x screen)
#     angle=90  → downward    (+y screen)
#     angle=180 → leftward    (-x screen)
#     angle=270 → upward      (-y screen)
#
#   Velocity from angle: vx = speed*cos(angle_rad), vy = speed*sin(angle_rad)
#   This is confirmed by ex_adv_asteroids_down_up: asteroid at y=100, angle=90
#   must move DOWN (toward center) → vy = +100 = sin(90°)*100. ✓
#
#   Therefore: atan2(screen_dy, screen_dx) → Kessler heading directly. No flip.
#
# FIRE TIMING
#   The controller arms (delay=1) on the frame it first aligns.
#   The bullet actually leaves on the NEXT frame.
#   So the intercept must be computed with the asteroid advanced 1 frame forward.
#   This is done ONLY on the arming frame; the stored angle is reused on fire frame.
# ─────────────────────────────────────────────────────────────────────────────

BULLET_SPEED   = 800.0          # px/s (confirmed from original controller)
FPS            = 30.0           # frames/s
BULLET_SPF     = BULLET_SPEED / FPS   # px/frame
FIRE_THRESHOLD = 0.5            # degrees — tight enough for sub-1px miss at 300px
TURN_FAST      = 180.0          # deg/frame when far from target
SHIP_RADIUS    = 20             # px (used for collision prediction)


# ─── Math helpers ─────────────────────────────────────────────────────────────

def angle_diff(target: float, current: float) -> float:
    """Signed shortest angular distance, result in [-180, 180]."""
    return (target - current + 180.0) % 360.0 - 180.0


def intercept_angle(ship_pos: tuple, ast_pos: tuple, ast_vel: tuple,
                    advance_frames: int = 0) -> tuple:
    """
    Solve for where a bullet fired from ship_pos meets an asteroid.

    advance_frames: advance asteroid position this many frames before solving.
                    Use 1 on the arming frame so the bullet (which fires next
                    frame) meets the asteroid at the correct future position.

    Returns (heading_deg, tof_frames, intercept_x, intercept_y).
    heading_deg is in (-180, 180] in Kessler convention (CW from east, screen y-down).
    """
    sx, sy = ship_pos

    # Advance asteroid starting position to account for fire delay
    ax = ast_pos[0] + ast_vel[0] / FPS * advance_frames
    ay = ast_pos[1] + ast_vel[1] / FPS * advance_frames

    avx = ast_vel[0] / FPS   # px/frame
    avy = ast_vel[1] / FPS
    B   = BULLET_SPF

    dx = ax - sx
    dy = ay - sy

    # Quadratic: (avx²+avy²-B²)t² + 2(dx·avx+dy·avy)t + (dx²+dy²) = 0
    a_c = avx*avx + avy*avy - B*B
    b_c = 2.0 * (dx*avx + dy*avy)
    c_c = dx*dx + dy*dy

    t1, t2 = solve_quadratic(a_c, b_c, c_c)

    tof = None
    for t in (t1, t2):
        if not math.isnan(t) and t > 0.0:
            if tof is None or t < tof:
                tof = t

    if tof is None or tof <= 0.0:
        dist = math.hypot(dx, dy)
        tof  = dist / B if B > 0 else 1.0

    ix = ax + avx * tof
    iy = ay + avy * tof

    # atan2(screen_dy, screen_dx) gives Kessler heading directly (CW from east).
    heading = math.degrees(math.atan2(iy - sy, ix - sx))
    return heading, tof, ix, iy


def impact_frames(interval: tuple) -> float:
    """Convert predict_collision (t_start, t_end) to frames until first contact."""
    t0, t1 = interval
    if math.isinf(t0):  return 0.0     # permanently overlapping
    if math.isnan(t0):  return 300.0   # no collision on current path
    if t0 <= 0.0 <= t1: return 0.0     # currently colliding
    if t1 <= 0.0:       return 300.0   # collision already passed
    return min(t0 * FPS, 300.0)


# ─── Controller ───────────────────────────────────────────────────────────────

class AimbotController(KesslerController):
    """
    Aimbot controller.

    Targeting pipeline each frame:
      1. Score every non-shot asteroid with fuzzy-logic priority
         (size × impact_time × turn_time → lookup table).
      2. Select highest-priority target; apply hysteresis to avoid thrashing.
      3. Compute precise analytic intercept heading.
      4. Turn toward intercept heading at max rate or proportional fine-tune.
      5. When heading error ≤ FIRE_THRESHOLD (0.5°):
           - Arming frame:  compute intercept with advance=1 (next-frame correction),
                            store aim angle, set delay=1.
           - Firing frame:  use stored aim angle, fire, record shot.
      6. Mine drop if asteroid will collide within 7 frames.
    """

    def __init__(self):
        with open('priorty_lookup_table.json', 'r') as f:
            self.lookup_table: dict = json.load(f)

        # State reset on each scenario start
        self._reset()

    def _reset(self):
        self.delay         = 0       # 0 = idle, 1 = armed (fire next frame)
        self.rest_counter  = 0       # frame we last fired (prevents re-arm same frame)
        self.shots_in_air  = []      # [{velocity, size, sim_frame}, …]
        self.prev_target   = None    # last chosen asteroid dict (with 'priority' key)
        # Stored aim from arming frame — used on firing frame without recompute
        self.stored_aim    = None    # (heading_deg, tof, ix, iy)

    # ── Fuzzy priority lookup ──────────────────────────────────────────────────
    def _priority(self, size: int, imp_frames: float, turn_frames: float) -> float:
        imp  = min(int(round(imp_frames)),  300)
        turn = min(int(round(turn_frames)),  29)
        return self.lookup_table.get(f"{size},{imp},{turn}", 1.0)

    # ── Main action ───────────────────────────────────────────────────────────
    def actions(self, ship_state: Dict, game_state: Dict) -> Tuple[float, float, bool, bool]:

        frame   = game_state["frame"]
        ship_pos = ship_state["position"]
        heading  = ship_state["heading"]

        if game_state["time"] == 0:
            self._reset()

        fire      = False
        drop_mine = False
        turn_rate = 0.0

        # Prune shots that have already reached their target
        self.shots_in_air = [s for s in self.shots_in_air if s["sim_frame"] > frame]

        # ── Score every asteroid ──────────────────────────────────────────────
        best_ast      = None
        best_priority = -math.inf
        best_intercept = None   # (heading, tof, ix, iy) cached from scoring loop

        for ast in game_state["asteroids"]:

            # Skip if a bullet is already on the way to this asteroid
            if any(s["velocity"] == ast["velocity"] and s["size"] == ast["size"]
                   for s in self.shots_in_air):
                continue

            # Impact time (frames until asteroid reaches ship)
            imp_interval = predict_collision(
                ship_pos, (0, 0), SHIP_RADIUS,
                ast["position"], ast["velocity"], ast["radius"]
            )
            imp_t = impact_frames(imp_interval)

            # Mine drop: asteroid on collision path, arriving within 7 frames
            if (not ship_state["is_respawning"]
                    and ship_state["mines_remaining"] > 0
                    and 0 < imp_t <= 7.0
                    and imp_interval[0] > 0 and imp_interval[1] > 0):
                drop_mine = True

            # Intercept heading for turn-time estimate (advance=0, approximate ok)
            aim_h, tof, ix_t, iy_t = intercept_angle(
                ship_pos, ast["position"], ast["velocity"], advance_frames=0
            )
            turn_t = min(abs(angle_diff(aim_h, heading)) / 6.0, 29.0)

            priority = self._priority(ast["size"], imp_t, turn_t)

            if priority > best_priority:
                best_priority  = priority
                best_ast       = ast
                best_intercept = (aim_h, tof, ix_t, iy_t)

        # ── No targets ───────────────────────────────────────────────────────
        if best_ast is None:
            if self.delay == 1:
                # We were armed; fire into the void and clear state
                fire = True
                self.delay = 0
                self.stored_aim = None
            return 0.0, 0.0, fire, False

        # ── Target hysteresis ─────────────────────────────────────────────────
        # If we had a target last frame, try to track it (prevents thrashing).
        if self.prev_target is not None:
            pt = self.prev_target
            # Predict where prev target is NOW (it moved one frame since we stored it)
            pred_x = pt["position"][0] + pt["velocity"][0] / FPS
            pred_y = pt["position"][1] + pt["velocity"][1] / FPS
            for ast in game_state["asteroids"]:
                if (math.isclose(pred_x, ast["position"][0], abs_tol=2.0)
                        and math.isclose(pred_y, ast["position"][1], abs_tol=2.0)
                        and pt["size"] == ast["size"]):
                    # Found the same asteroid; keep it unless new target is
                    # significantly higher priority
                    if best_priority - pt["priority"] <= 1.0:
                        best_ast      = ast
                        best_priority = pt["priority"]
                        # Recompute intercept for this specific asteroid
                        best_intercept = intercept_angle(
                            ship_pos, ast["position"], ast["velocity"], advance_frames=0
                        )
                    break

        # Store chosen target with its priority for next-frame hysteresis
        best_ast_dict = best_ast.dict if hasattr(best_ast, "dict") else dict(best_ast)
        best_ast_dict["priority"] = best_priority
        self.prev_target = best_ast_dict

        # ── Compute aim heading ───────────────────────────────────────────────
        aim_h, tof, ix, iy = best_intercept

        diff     = angle_diff(aim_h, heading)
        abs_diff = abs(diff)

        # ── Turning ───────────────────────────────────────────────────────────
        if abs_diff > FIRE_THRESHOLD:
            if abs_diff > 6.0:
                # Far off — slew at maximum rate
                turn_rate = math.copysign(TURN_FAST, diff)
            else:
                # Close — proportional fine-tune (gain tuned so we reach 0.5° quickly)
                turn_rate = diff * (TURN_FAST / 6.0)

            # Not aligned yet; reset arm state
            self.delay      = 0
            self.stored_aim = None

        else:
            # ── Aligned ──────────────────────────────────────────────────────
            # Fine-tune turn even while aligned
            turn_rate = diff * (TURN_FAST / 6.0)

            if self.delay == 0 and (frame - self.rest_counter) >= 2:
                # ARMING FRAME: bullet will fire NEXT frame.
                # Compute intercept with asteroid advanced 1 frame so the bullet
                # meets the asteroid at its correct future position.
                aim_h1, tof1, ix1, iy1 = intercept_angle(
                    ship_pos, best_ast["position"], best_ast["velocity"],
                    advance_frames=1
                )
                self.stored_aim = (aim_h1, tof1, ix1, iy1)
                self.delay = 1

        # ── Firing ───────────────────────────────────────────────────────────
        if self.delay == 1 and not ship_state["is_respawning"]:
            # FIRING FRAME: use the aim angle stored on the arming frame.
            # Do NOT recompute — asteroid has moved exactly 1 frame since arming,
            # which is exactly what advance_frames=1 accounted for.
            if self.stored_aim is not None:
                aim_h, tof, ix, iy = self.stored_aim

            fire              = True
            self.delay        = 0
            self.rest_counter = frame
            self.stored_aim   = None

            # Record shot so we don't double-target this asteroid
            record = {
                "velocity":  best_ast["velocity"],
                "size":      best_ast["size"],
                "sim_frame": frame + int(tof) + 5,
            }
            self.shots_in_air.append(record)

        return 0.0, turn_rate, fire, drop_mine

    @property
    def name(self) -> str:
        return "Aimbot v1.0"

    @property
    def custom_sprite_path(self) -> str:
        return "akila's turtle fortress spaceship sprite.png"
