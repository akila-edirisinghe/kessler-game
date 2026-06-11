'''
═══════════════════════════════════════════════════════════════════════════════
WHAT CHANGED FROM v2.0 (SIMPLIFIED)
═══════════════════════════════════════════════════════════════════════════════

1) STRONGER TARGET SEPARATION
─────────────────────────────
Raw fuzzy scores (1–10) were too close together, making targets feel similar.

We apply a power curve:
    scaled_priority = raw_priority ** PRIORITY_EXPONENT

This preserves ordering but increases separation between strong and weak targets.
Switching behavior was adjusted so the agent commits more strongly and only
changes targets when there is a clearly better option.

2) SIMPLE RECOVERY FROM MISSED SHOTS
─────────────────────────────────────
Previously, fired shots stayed reserved for a fixed time, which sometimes blocked
retargeting even after a miss.

Fix: every RESCAN_INTERVAL frames, we clear `shots_in_air`.

This immediately makes all still-alive asteroids eligible again.


3) REMOVED LESS EFFECTIVE MINE STRATEGIES
─────────────────────────────────────────
Removed:
  - Cluster kill mines
  - Large incoming asteroid intercept mines

Kept:
  - Emergency kamikaze mine (only when a hit is unavoidable)



4) REMOVED WRAP-AWARE LOOKAHEAD (FOR NOW)
────────────────────────────────────────
Wrap-aware prediction was removed.

Issues:
  - It caused over-prediction and early aiming, reducing accuracy
  - Bullets do not wrap, so wrap-based intercepts often produced wasted shots



5) INDECISION BREAKER 
───────────────────────────
Problem: agent sometimes switches between similar targets and fails to fire.

Fix:
If frames_since_fire > INDECISION_FRAMES:
  - Ignore normal priority scoring
  - Pick asteroid requiring least rotation to shoot
  - Force a temporary lock so it commits and fires


OTHER IMPROVEMENTS (FROM v2.0)
──────────────────────────────
- Spray fire respects can_fire
- Arm gating uses can_fire directly
- Turn scoring uses intercept-based heading
'''

from src.kesslergame import KesslerController
from typing import Dict, Tuple, Optional
from impact_time_cal import predict_collision, solve_quadratic
import math
import json


BULLET_SPEED     = 800.0
FPS              = 30.0
BULLET_SPF       = BULLET_SPEED / FPS       # px/frame ~26.67

FIRE_THRESHOLD   = 1.0                      # degrees to consider "aligned"

TURN_FAST        = 180.0                    # max slew (deg/s)
TURN_SWITCH_DEG  = 10.0                     # proportional below this
PROP_GAIN        = TURN_FAST / TURN_SWITCH_DEG

SHIP_RADIUS      = 20                       # px


# Raw fuzzy scores (1-10) are raised to PRIORITY_EXPONENT to stretch apart
# high-value targets from mediocre ones, increasing decisiveness.
PRIORITY_EXPONENT  = 1.6
TARGET_LOCK_FRAMES = 25                     # ~0.83 s before reconsidering
SWITCH_MARGIN      = 1.0                    # challenger must beat frozen (scaled) score by this

# Asteroid identity tracker
ID_MAX_MOVE_PX    = 20.0
ID_MAX_MOVE_PX2   = ID_MAX_MOVE_PX ** 2

# Stale-shot recovery: periodically forget all in-flight shots so any asteroid
# that's still alive (missed shot, wrong-target hit, etc.) becomes eligible
# for targeting again.
RESCAN_INTERVAL   = 30                      # 1 second @ 30 FPS

# Indecision breaker:
# If the ship goes this many frames without firing a shot (while asteroids
# are present), the normal priority/lock logic is overridden and the ship
#  commits to the asteroid requiring the LEAST turning aka the fastest
# possible path to an aligned shot  and locks onto it for FORCE_LOCK_FRAMES,
# ignoring SWITCH_MARGIN entirely. This breaks cycles where the fuzzy score
# keeps flip-flopping between near-tied targets and the ship never settles
# long enough to actually fire.
INDECISION_FRAMES = 45                      # ~1.5 s without a shot
FORCE_LOCK_FRAMES = 40                      # > TARGET_LOCK_FRAMES, hard commit

# Spray fire (infinite ammo only)
SPRAY_EVERY_N     = 3                       # fire 1-in-3 frames while turning

# Mine thresholds (strategy A only — see header notes)
MINE_SAVE_FRAMES      = 10
MINE_COOLDOWN_FRAMES  = 90



def angle_diff(target: float, current: float) -> float:
    """Signed shortest arc current→target, result in (-180, 180].
    Positive = CCW = positive turn_rate in Kessler."""
    return (target - current + 180.0) % 360.0 - 180.0


def intercept_angle(ship_pos, ast_pos, ast_vel, advance_frames=0):
    """
    Analytically solve bullet heading to intercept a moving asteroid.

    advance_frames: shift asteroid forward N frames before solving.
                    Use 1 on the arming frame (bullet fires next frame).

    Returns (heading_deg, tof_frames, intercept_x, intercept_y).
    """
    sx, sy = ship_pos
    ax = ast_pos[0] + ast_vel[0] / FPS * advance_frames
    ay = ast_pos[1] + ast_vel[1] / FPS * advance_frames

    avx = ast_vel[0] / FPS
    avy = ast_vel[1] / FPS
    B   = BULLET_SPF

    dx, dy = ax - sx, ay - sy

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
    return math.degrees(math.atan2(iy - sy, ix - sx)), tof, ix, iy


def impact_frames(interval):
    """predict_collision interval → frames until first contact."""
    t0, t1 = interval
    if math.isinf(t0):  return 0.0
    if math.isnan(t0):  return 300.0
    if t0 <= 0.0 <= t1: return 0.0
    if t1 <= 0.0:       return 300.0
    return min(t0 * FPS, 300.0)


def dist2(p1, p2):
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return dx*dx + dy*dy


# ─── Asteroid identity tracker ────────────────────────────────────────────────

class AsteroidTracker:
    """
    Assigns stable integer IDs to asteroids across frames.

    Each frame: greedy nearest-neighbour match between predicted old positions
    and new actual positions (within ID_MAX_MOVE_PX, same size).
    Unmatched new asteroids get fresh IDs.  Destroyed asteroids are retired.

    This is essential for:
      - shots_in_air keyed on stable ID (no float-equality fragility)
      - target lock tracking without position-prediction hacks
    """

    def __init__(self):
        self._next_id = 0
        # id -> {"pred": (px,py), "size": int}
        self._known: dict = {}

    def reset(self):
        self._next_id = 0
        self._known   = {}

    def update(self, asteroids: list) -> dict:
        """
        Match this frame's asteroids to known IDs.
        Returns {list_index: stable_int_id}.
        """
        assigned: dict = {}
        used_ids: set  = set()

        for idx, ast in enumerate(asteroids):
            pos  = ast["position"]
            size = ast["size"]
            best_id = None
            best_d2 = ID_MAX_MOVE_PX2

            for aid, info in self._known.items():
                if aid in used_ids:
                    continue
                if info["size"] != size:
                    continue
                d2 = dist2(pos, info["pred"])
                if d2 < best_d2:
                    best_d2 = d2
                    best_id = aid

            if best_id is not None:
                assigned[idx] = best_id
                used_ids.add(best_id)
            else:
                assigned[idx] = self._next_id
                self._next_id += 1

        # Rebuild known from this frame
        new_known = {}
        for idx, ast in enumerate(asteroids):
            aid  = assigned[idx]
            vx, vy = ast["velocity"]
            px = ast["position"][0] + vx / FPS
            py = ast["position"][1] + vy / FPS
            new_known[aid] = {"pred": (px, py), "size": ast["size"]}
        self._known = new_known

        return assigned



class AkilaController(KesslerController):
    """

    Targeting pipeline each frame:
      1. AsteroidTracker assigns stable IDs to all asteroids.
      2. Score every un-shot asteroid: fuzzy(size, imp_t, turn_t)**PRIORITY_EXPONENT,
         using each asteroid's current (unwrapped) position/velocity. The
         intercept heading stays stable as the ship turns since it's based on
         the solved intercept, not the raw bearing.
      3. Target selection one of:
           - Indecision breaker: if frames_since_fire >= INDECISION_FRAMES,
             force-pick the asteroid needing the LEAST turning and hard-lock
             onto it (locked_score = inf) until it fires.
           - Otherwise, two-layer target lock:
               - Active lock: keep target unless challenger beats frozen
                 score by SWITCH_MARGIN, or lock timer expires, or target
                 is destroyed.
               - Expired/no lock: pick highest scorer, start new lock.
      4. Turn toward intercept (shortest direction, proportional near target).
      5. Fire when aligned (arm+fire two-frame pattern with advance=1 correction).
         Spray fire while turning if infinite ammo. frames_since_fire resets
         to 0 on every shot fired.
      6. Mine drops: kamikaze save only (strategy A).
      7. Every RESCAN_INTERVAL frames, forget all in-flight shots so missed /
         wrong-target asteroids become eligible for targeting again.
    """

    def __init__(self):
        with open('priorty_lookup_table.json', 'r') as f:
            self.lookup_table: dict = json.load(f)
        self.tracker = AsteroidTracker()
        self._reset()


    def _reset(self):
        self.tracker.reset()

        self.delay            = 0       # 0=idle  1=armed (fires next frame)
        self.rest_counter     = 0
        self.stored_aim       = None    # (heading, tof, ix, iy)
        self.infinite_bullets = False

        self.shots_in_air: dict = {}    # stable_id -> expiry_frame

        # Target lock
        self.locked_id:        Optional[int]  = None
        self.lock_frames_left: int            = 0
        self.locked_score:     float          = 0.0

        self.last_mine_frame = -MINE_COOLDOWN_FRAMES

        # Indecision breaker: frames elapsed since the last bullet was fired
        self.frames_since_fire: int = 0

    # ── Fuzzy lookup ──────────────────────────────────────────────────────────

    def _priority(self, size: int, imp_t: float, turn_t: float) -> float:
        imp  = min(int(round(imp_t)),  300)
        turn = min(int(round(turn_t)),  29)
        raw = float(self.lookup_table.get(f"{size},{imp},{turn}", 1.0))
        # Stretch the score distribution so strong targets stand out much more
        # decisively from mediocre ones (raw is always >= 1, so this preserves
        # ordering while amplifying the gaps between high scores).
        return raw ** PRIORITY_EXPONENT

    # ── Mine decision ─────────────────────────────────────────────────────────

    def _decide_mine(self, ship_state: Dict, game_state: Dict, frame: int) -> bool:
        if ship_state["mines_remaining"] <= 0:          return False
        if not ship_state["can_deploy_mine"]:           return False
        if ship_state["is_respawning"]:                 return False
        if frame - self.last_mine_frame < MINE_COOLDOWN_FRAMES: return False

        ship_pos  = ship_state["position"]
        lives     = ship_state["lives_remaining"]
        asteroids = game_state["asteroids"]

        # Strategy A: Kamikaze save — imminent unavoidable hit.

        for ast in asteroids:
            interval = predict_collision(
                ship_pos, (0, 0), SHIP_RADIUS,
                ast["position"], ast["velocity"], ast["radius"]
            )
            imp_t = impact_frames(interval)
            if 0 < imp_t <= MINE_SAVE_FRAMES:
                if lives > 1 or ast["size"] >= 2:
                    return True

        return False

    # ── Target lock state machine ─────────────────────────────────────────────

    def _select_target(self, scored: list, id_map: dict) -> Optional[tuple]:
        """
        scored: [(priority, idx, ast, intercept), …] sorted highest-first.
        id_map: {list_idx: stable_id}
        Returns chosen (priority, idx, ast, intercept) or None.
        """
        if not scored:
            self.locked_id        = None
            self.lock_frames_left = 0
            return None

        # Tick lock timer
        if self.lock_frames_left > 0:
            self.lock_frames_left -= 1

        # Check if locked target survived this frame
        if self.locked_id is not None:
            alive = any(id_map.get(e[1]) == self.locked_id for e in scored)
            if not alive:
                # Destroyed — unlock immediately
                self.locked_id        = None
                self.lock_frames_left = 0

        # ── Active lock ───────────────────────────────────────────────────────
        if self.locked_id is not None and self.lock_frames_left > 0:
            # Find the locked asteroid in this frame's scored list
            for entry in scored:
                if id_map.get(entry[1]) == self.locked_id:
                    # Check if the best challenger earns an early switch
                    best = scored[0]
                    if (id_map.get(best[1]) != self.locked_id
                            and best[0] > self.locked_score + SWITCH_MARGIN):
                        # Challenger is decisively better — switch
                        self._lock_onto(best, id_map)
                        return best
                    # Stay on locked target
                    return entry
            # Locked target filtered out (e.g. shot already in air) — fall through

        # ── No active lock — pick best and start new lock ─────────────────────
        best = scored[0]
        self._lock_onto(best, id_map)
        return best

    def _lock_onto(self, entry: tuple, id_map: dict):
        """Commit to a target: record its stable ID, start timer, freeze score."""
        prio, idx, ast, intercept = entry
        self.locked_id        = id_map.get(idx)
        self.lock_frames_left = TARGET_LOCK_FRAMES
        self.locked_score     = prio

    # ── Main action ───────────────────────────────────────────────────────────

    def actions(self, ship_state: Dict, game_state: Dict) -> Tuple[float, float, bool, bool]:

        frame    = game_state["frame"]
        ship_pos = ship_state["position"]
        heading  = ship_state["heading"]

        if game_state["time"] == 0:
            self._reset()

        self.infinite_bullets = (ship_state["bullets_remaining"] == -1)

        fire      = False
        drop_mine = False
        turn_rate = 0.0

        # Assign stable IDs to this frame's asteroids
        asteroids = game_state["asteroids"]
        id_map    = self.tracker.update(asteroids)

        # Prune expired shots
        self.shots_in_air = {aid: exp for aid, exp in self.shots_in_air.items()
                             if exp > frame}

        # Stale-shot recovery: periodically forget ALL in-flight shots so any
        # asteroid that survived a missed/wrong-target shot becomes eligible
        # for targeting again, without per-asteroid hit verification.
        if frame % RESCAN_INTERVAL == 0:
            self.shots_in_air.clear()

        # Mine decision
        drop_mine = self._decide_mine(ship_state, game_state, frame)
        if drop_mine:
            self.last_mine_frame = frame

        # ── Score all asteroids ───────────────────────────────────────────────
        scored = []
        for idx, ast in enumerate(asteroids):
            stable_id = id_map.get(idx)

            # Skip if a bullet is already heading for this asteroid
            if stable_id in self.shots_in_air:
                continue

            aim_h, tof, ix_t, iy_t = intercept_angle(
                ship_pos, ast["position"], ast["velocity"], advance_frames=0
            )

            interval = predict_collision(
                ship_pos, (0, 0), SHIP_RADIUS,
                ast["position"], ast["velocity"], ast["radius"]
            )
            imp_t = impact_frames(interval)

            # turn_t: frames needed to reach intercept heading
            # Using intercept heading (not raw bearing) keeps this stable while
            # the ship is rotating — prevents score drift that causes oscillation.
            turn_t = min(abs(angle_diff(aim_h, heading)) / 6.0, 29.0)

            priority = self._priority(ast["size"], imp_t, turn_t)
            scored.append((priority, idx, ast, (aim_h, tof, ix_t, iy_t)))

        scored.sort(key=lambda e: e[0], reverse=True)

        # ── Target selection ──────────────────────────────────────────────────
        if scored and self.frames_since_fire >= INDECISION_FRAMES:
            # Indecision breaker: it's been too long since we last fired,
            # almost certainly because the locked target keeps getting
            # outscored by near-tied challengers (or the lock keeps expiring
            # right as we're about to align). Stop deliberating: forcibly
            # commit to whichever asteroid needs the LEAST turning right now
            # — the fastest possible route to an aligned shot — and lock
            # onto it hard so nothing can pre-empt it before we fire.
            chosen = min(scored, key=lambda e: abs(angle_diff(e[3][0], heading)))
            self.locked_id        = id_map.get(chosen[1])
            self.lock_frames_left = FORCE_LOCK_FRAMES
            self.locked_score     = math.inf  # nothing can out-prioritize this lock
            self.delay            = 0
            self.stored_aim       = None
        else:
            chosen = self._select_target(scored, id_map)

        if chosen is None:
            if self.delay == 1:
                fire = True
                self.delay      = 0
                self.stored_aim = None
            self.frames_since_fire = 0 if fire else self.frames_since_fire + 1
            return 0.0, 0.0, fire, drop_mine

        _, chosen_idx, chosen_ast, chosen_intercept = chosen
        aim_h, tof, ix, iy = chosen_intercept

        # ── Heading error (signed shortest arc) ───────────────────────────────
        diff     = angle_diff(aim_h, heading)
        abs_diff = abs(diff)

        # ── Turning ───────────────────────────────────────────────────────────
        if abs_diff > FIRE_THRESHOLD:
            # Full slew or proportional depending on distance from target heading
            if abs_diff > TURN_SWITCH_DEG:
                turn_rate = math.copysign(TURN_FAST, diff)
            else:
                turn_rate = diff * PROP_GAIN
            turn_rate = max(-TURN_FAST, min(TURN_FAST, turn_rate))

            # Break arm state while turning
            self.delay      = 0
            self.stored_aim = None

            # Spray fire: unlimited ammo only, every SPRAY_EVERY_N frames
            if (self.infinite_bullets
                    and not ship_state["is_respawning"]
                    and ship_state["can_fire"]
                    and frame % SPRAY_EVERY_N == 0):
                fire = True

        else:
            # ── Aligned ───────────────────────────────────────────────────────
            # Proportional fine-tune to hold heading
            turn_rate = diff * PROP_GAIN
            turn_rate = max(-TURN_FAST, min(TURN_FAST, turn_rate))

            # Arm if idle and the gun is ready
            if (self.delay == 0
                    and not ship_state["is_respawning"]
                    and ship_state["can_fire"]):
                # advance=1: bullet physically leaves next frame
                aim_h1, tof1, ix1, iy1 = intercept_angle(
                    ship_pos, chosen_ast["position"], chosen_ast["velocity"],
                    advance_frames=1
                )
                self.stored_aim = (aim_h1, tof1, ix1, iy1)
                self.delay = 1

        # ── Fire ──────────────────────────────────────────────────────────────
        if self.delay == 1 and not ship_state["is_respawning"]:
            if self.stored_aim is not None:
                aim_h, tof, ix, iy = self.stored_aim

            fire              = True
            self.delay        = 0
            self.stored_aim   = None
            self.rest_counter = frame

            # Record bullet so we don't fire a second shot at the same asteroid
            chosen_stable_id = id_map.get(chosen_idx)
            if chosen_stable_id is not None:
                self.shots_in_air[chosen_stable_id] = frame + int(tof) + 5

        # Track how long it's been since we last actually fired, used by the
        # indecision breaker at the top of the next call.
        self.frames_since_fire = 0 if fire else self.frames_since_fire + 1

        return 0.0, turn_rate, fire, drop_mine

    @property
    def name(self) -> str:
        return "hit or miss 3.0v"

    @property
    def custom_sprite_path(self) -> str:
        return "akila's turtle fortress spaceship sprite.png"