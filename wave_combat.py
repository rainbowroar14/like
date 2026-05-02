"""Waves, enemies, gun upgrades (inspired by tank upgrade-pick games on Scratch / diep-style)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

import pygame

from hostile_assets import HostileArt

# Imps + big boss share knockdown / finisher rules; boss never freezes from crosshair.
_IMP_FAMILY = frozenset({"imp", "boss"})

# Seconds before a bullet expires (still removed earlier if off-world).
PROJECTILE_LIFETIME_SEC = 30.0

# Technology Zero: only arc between tears within this gap (~5 × 64px arena tiles).
TECH_ZERO_MAX_LINK_DIST = 5.0 * 64.0


class GamePhase(Enum):
    COMBAT = auto()
    INTERMISSION = auto()  # 20s after wave clear
    UPGRADE = auto()


@dataclass
class GunStats:
    base_interval: float = 0.34
    base_speed: float = 640.0
    base_radius: float = 4.0
    interval_mult: float = 1.0
    speed_mult: float = 1.0
    damage_mult: float = 1.0
    radius_mult: float = 1.0
    pierce_bonus: int = 0
    parallel_extra: int = 0
    double_cannon_bonus: int = 0
    laser_visual: bool = False
    minigun: bool = False
    player_speed_mult: float = 1.0
    pierce_grows: bool = False
    fire_trail: bool = False
    sacred_heart_stacks: int = 0
    wiz_stacks: int = 0
    gambling_stacks: int = 0
    lion_ring_count: int = 0
    lava_dps_mult: float = 1.0
    homing_turn_mult: float = 1.0
    rubber_cement_stacks: int = 0
    tech_zero_stacks: int = 0
    chocolate_milk_stacks: int = 0
    spoon_bender_stacks: int = 0
    hive_mind_stacks: int = 0
    big_brain_stacks: int = 0
    thy_nuke_stacks: int = 0

    def interval(self) -> float:
        t = self.base_interval * self.interval_mult
        if self.minigun:
            t *= 0.5
        if self.sacred_heart_stacks > 0:
            t *= 3.0**self.sacred_heart_stacks
        return max(0.04, t)

    def speed(self) -> float:
        return self.base_speed * self.speed_mult

    def radius(self) -> float:
        r = self.base_radius * self.radius_mult
        if self.minigun:
            r *= 0.7
        return max(2.0, r)

    def damage(self) -> float:
        d = self.damage_mult
        if self.minigun:
            d *= 0.25
            # Trash mobs are 1 HP; keep at least 1 so minigun still one-shots them
            return max(1.0, d)
        return max(0.04, d)


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    radius: float
    hits_left: int
    laser: bool
    life: float = PROJECTILE_LIFETIME_SEC
    rot_deg: float = 0.0
    pierce_grows: bool = False
    spawn_fire_trail: bool = False
    trail_emit_cd: float = 0.0
    homing: bool = False
    rubber_bounce: bool = False
    nuke_mother: bool = False

    def update(
        self,
        dt: float,
        bounds: tuple[float, float, float, float],
        inner_bounds: tuple[float, float, float, float] | None = None,
    ) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt  # starts at PROJECTILE_LIFETIME_SEC
        x0, y0, x1, y1 = bounds
        if self.rubber_bounce and inner_bounds is not None:
            ix0, iy0, ix1, iy1 = inner_bounds
            if self.x < ix0:
                self.x = ix0
                self.vx = abs(self.vx)
            elif self.x > ix1:
                self.x = ix1
                self.vx = -abs(self.vx)
            if self.y < iy0:
                self.y = iy0
                self.vy = abs(self.vy)
            elif self.y > iy1:
                self.y = iy1
                self.vy = -abs(self.vy)
        if self.x < x0 or self.x > x1 or self.y < y0 or self.y > y1:
            return False
        return self.life > 0


@dataclass
class FireZone:
    x: float
    y: float
    radius: float
    life: float
    dps: float = 42.0
    phase: float = 0.0


@dataclass
class FireEmber:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    r: int
    g: int
    b: int


# Enemy kinds used by wave_spawn_plan / spawn_enemies.
ENEMY_KINDS_SPAWNED: tuple[str, ...] = (
    "bat",
    "spider",
    "imp",
    "boss",
    "scifi",
    "critter",
    "goblin",
)
ENEMY_KINDS_RESERVED: tuple[str, ...] = ()


@dataclass
class Enemy:
    kind: str
    x: float
    y: float
    hp: float
    max_hp: float
    speed: float
    radius: float
    anim_t: float = 0.0
    player_hit_cd: float = 0.0
    hit_flash: float = 0.0
    hit_vfx_t: float = -1.0
    hit_vfx_id: int = 0
    hit_vfx_len: int = 0
    ai_seed: float = 0.0
    dash_cd: float = 0.0
    imp_down: bool = False
    imp_revive: float = 0.0
    imp_dead: bool = False
    imp_moving: bool = False
    bullet_iframe: float = 0.0


UPGRADE_DEFS: list[dict[str, str]] = [
    {
        "id": "laser",
        "title": "Laser rounds",
        "desc": "Beam sprites (Master484). Slightly punchier shots.",
    },
    {
        "id": "rapid",
        "title": "Rapid fire",
        "desc": "Half delay between shots.",
    },
    {
        "id": "velocity",
        "title": "High velocity",
        "desc": "Bullets travel 2× faster.",
    },
    {
        "id": "pierce",
        "title": "Piercing rounds",
        "desc": "Each bullet hits one extra foe.",
    },
    {
        "id": "double",
        "title": "Double cannon",
        "desc": "Fire two parallel slugs per burst.",
    },
    {
        "id": "minigun",
        "title": "Minigun",
        "desc": "Half fire delay, but −75% damage and −30% bullet size.",
    },
    {
        "id": "big_bullets",
        "title": "Heavy caliber",
        "desc": "Bullets are ~45% wider.",
    },
    {
        "id": "slug",
        "title": "Slug rounds",
        "desc": "Much more damage — great vs imps.",
    },
    {
        "id": "boots",
        "title": "Swift boots",
        "desc": "Move ~22% faster.",
    },
    {
        "id": "extra_pierce",
        "title": "Overpenetration",
        "desc": "Each shot pierces two more targets.",
    },
    {
        "id": "greased",
        "title": "Greased bolt",
        "desc": "Another ~15% less time between shots.",
    },
    {
        "id": "marksman",
        "title": "Marksman kit",
        "desc": "Slight damage and bullet size bump.",
    },
    {
        "id": "siphon",
        "title": "Velocity surge",
        "desc": "Bullets +35% speed (stacks).",
    },
]


def apply_upgrade(uid: str, gun: GunStats, owned: set[str]) -> None:
    if uid in owned:
        return
    owned.add(uid)
    if uid == "laser":
        gun.laser_visual = True
        gun.damage_mult *= 1.12
    elif uid == "rapid":
        gun.interval_mult *= 0.5
    elif uid == "velocity":
        gun.speed_mult *= 2.0
    elif uid == "pierce":
        gun.pierce_bonus += 1
    elif uid == "double":
        gun.double_cannon_bonus = max(gun.double_cannon_bonus, 1)
    elif uid == "minigun":
        gun.minigun = True
    elif uid == "big_bullets":
        gun.radius_mult *= 1.45
    elif uid == "slug":
        gun.damage_mult *= 1.55
    elif uid == "boots":
        gun.player_speed_mult *= 1.22
    elif uid == "extra_pierce":
        gun.pierce_bonus += 2
    elif uid == "greased":
        gun.interval_mult *= 0.85
    elif uid == "marksman":
        gun.damage_mult *= 1.12
        gun.radius_mult *= 1.08
    elif uid == "siphon":
        gun.speed_mult *= 1.35


def pick_offerings(owned: set[str], k: int = 4) -> list[dict[str, str]]:
    pool = [u for u in UPGRADE_DEFS if u["id"] not in owned]
    if not pool:
        return []
    random.shuffle(pool)
    return pool[: min(k, len(pool))]


def _edge_spawn(world_w: float, world_h: float, pad: float) -> tuple[float, float]:
    side = random.randint(0, 3)
    if side == 0:
        return random.uniform(pad, world_w - pad), pad
    if side == 1:
        return world_w - pad, random.uniform(pad, world_h - pad)
    if side == 2:
        return random.uniform(pad, world_w - pad), world_h - pad
    return pad, random.uniform(pad, world_h - pad)


def _scale(wave: int) -> float:
    """Speed scale only — fodder stays 1 HP."""
    return 1.0 + (wave - 1) * 0.024


def wave_spawn_plan(wave: int) -> list[tuple[str, int]]:
    """Waves 1–4 bats; 5 = five imps; 6–9 bats+spiders; every 10th wave = boss;
    11–14 scifi+spiders; 15 = many goblins + five imps; 16+ scifi+critter (non-boss waves)."""
    b = 8 + wave * 4
    if wave >= 10 and wave % 10 == 0:
        return [("boss", 1)]
    if wave <= 3:
        return [("bat", b + wave * 3)]
    if wave == 4:
        return [("bat", b + 4 + 12 + wave * 2)]
    if wave == 5:
        return [("imp", 5)]
    if wave <= 9:
        total = max(36, 18 + wave * 7)
        return [("bat", total // 2), ("spider", total - total // 2)]
    if wave <= 14:
        total = max(34, 16 + wave * 6)
        return [("scifi", total // 2), ("spider", total - total // 2)]
    if wave == 15:
        return [("goblin", 58), ("imp", 5)]
    total = max(40, 20 + wave * 5)
    return [("scifi", total // 2), ("critter", total - total // 2)]


def spawn_enemies(
    wave: int,
    world_w: float,
    world_h: float,
    out: list[Enemy],
    post_boss_hp_mult: float = 1.0,
) -> None:
    sp_m = _scale(wave)
    pad = 48.0
    hp_m = max(0.25, post_boss_hp_mult)
    for kind, count in wave_spawn_plan(wave):
        for _ in range(count):
            x, y = _edge_spawn(world_w, world_h, pad)
            if kind == "boss":
                hp, spd, r = 120.0, 125.0, 44.0
            elif kind == "imp":
                hp, spd, r = 25.0, 68.0, 32.0
            elif kind == "goblin":
                hp, spd, r = 1.0, 96.0, 14.0
            elif kind == "bat":
                hp, spd, r = 1.0, 98.0, 14.0
            elif kind == "scifi":
                hp, spd, r = 1.0, 86.0, 16.0
            elif kind == "spider":
                hp, spd, r = 2.0, 80.0, 18.0
            else:  # critter
                hp, spd, r = 1.0, 102.0, 12.0
            hp *= hp_m
            seed = random.random() * 6.283185307179586
            out.append(
                Enemy(
                    kind=kind,
                    x=x,
                    y=y,
                    hp=hp,
                    max_hp=hp,
                    speed=spd * sp_m,
                    radius=r,
                    ai_seed=seed,
                )
            )


HIT_VFX_FPS = 22.0


def _aiming_at_imp(px: float, py: float, aim_dx: float, aim_dy: float, e: Enemy) -> bool:
    """True if crosshair direction is roughly toward this imp (SCP-style freeze)."""
    tx, ty = e.x - px, e.y - py
    td = math.hypot(tx, ty) or 1.0
    tx, ty = tx / td, ty / td
    dot = tx * aim_dx + ty * aim_dy
    return dot > 0.74


def _resolve_enemy_collisions(
    enemies: list[Enemy],
    world_w: float,
    world_h: float,
    margin: float,
) -> None:
    """Push overlapping enemies apart so they cannot stack on one tile."""
    pad = 2.0
    for _ in range(4):
        for i, a in enumerate(enemies):
            if a.kind in _IMP_FAMILY and a.imp_dead:
                continue
            for j in range(i + 1, len(enemies)):
                b = enemies[j]
                if b.kind in _IMP_FAMILY and b.imp_dead:
                    continue
                dx = b.x - a.x
                dy = b.y - a.y
                dist = math.hypot(dx, dy)
                min_d = a.radius + b.radius + pad
                if dist >= min_d:
                    continue
                if dist < 1e-6:
                    dx, dy = 1.0, 0.0
                    dist = 1.0
                nx, ny = dx / dist, dy / dist
                push = 0.5 * (min_d - dist)
                a.x -= nx * push
                a.y -= ny * push
                b.x += nx * push
                b.y += ny * push
                a.x = max(margin, min(world_w - margin, a.x))
                a.y = max(margin, min(world_h - margin, a.y))
                b.x = max(margin, min(world_w - margin, b.x))
                b.y = max(margin, min(world_h - margin, b.y))


def update_enemies(
    enemies: list[Enemy],
    dt: float,
    px: float,
    py: float,
    world_w: float,
    world_h: float,
    on_player_hit: Callable[[float], None],
    aim_dx: float = 1.0,
    aim_dy: float = 0.0,
) -> None:
    margin = 24.0
    for e in enemies:
        dx, dy = px - e.x, py - e.y
        dist = math.hypot(dx, dy) or 1.0
        nx, ny = dx / dist, dy / dist

        if e.kind in _IMP_FAMILY and e.imp_down:
            e.imp_revive -= dt
            if e.imp_revive <= 0.0:
                e.imp_down = False
                e.hp = e.max_hp
                e.imp_revive = 0.0
            mx, my = 0.0, 0.0
        elif e.kind == "imp" and _aiming_at_imp(px, py, aim_dx, aim_dy, e):
            mx, my = 0.0, 0.0
        elif e.kind in ("bat", "goblin"):
            wx = math.cos(e.anim_t * 11.0 + e.ai_seed) * 62.0
            wy = math.sin(e.anim_t * 9.0 + e.ai_seed * 1.31) * 62.0
            mx = nx * e.speed * dt + wx * dt
            my = ny * e.speed * dt + wy * dt
        elif e.kind == "scifi":
            tx, ty = -ny, nx
            mx = (nx * 0.32 + tx * 0.68) * e.speed * dt
            my = (ny * 0.32 + ty * 0.68) * e.speed * dt
        elif e.kind == "spider":
            e.dash_cd = max(0.0, e.dash_cd - dt)
            sp = e.speed * (1.35 if dist < 200 else 1.0)
            dash = 1.0
            if e.dash_cd > 0:
                dash = 2.35
            elif dist < 260 and random.random() < 0.018:
                e.dash_cd = 0.42
            mx = nx * sp * dash * dt
            my = ny * sp * dash * dt
        elif e.kind == "critter":
            jx = math.sin(e.anim_t * 21.0 + e.ai_seed) * 55.0 * dt
            jy = math.cos(e.anim_t * 16.0 + e.ai_seed * 0.7) * 55.0 * dt
            mx = nx * e.speed * 1.15 * dt + jx
            my = ny * e.speed * 1.15 * dt + jy
        elif e.kind in _IMP_FAMILY:
            sp = e.speed * (0.78 if e.kind == "imp" else 1.0)
            mx = nx * sp * dt
            my = ny * sp * dt
        else:
            mx = nx * e.speed * dt
            my = ny * e.speed * dt

        if e.kind in _IMP_FAMILY and not e.imp_down:
            e.imp_moving = (mx * mx + my * my) > 1e-8
        e.x += mx
        e.y += my
        e.x = max(margin, min(world_w - margin, e.x))
        e.y = max(margin, min(world_h - margin, e.y))
        e.anim_t += dt
        e.player_hit_cd = max(0.0, e.player_hit_cd - dt)
        e.hit_flash = max(0.0, e.hit_flash - dt)
        e.bullet_iframe = max(0.0, e.bullet_iframe - dt)
        if e.hit_vfx_t >= 0.0 and e.hit_vfx_len > 0:
            e.hit_vfx_t += dt
            if int(e.hit_vfx_t * HIT_VFX_FPS) >= e.hit_vfx_len:
                e.hit_vfx_t = -1.0
                e.hit_vfx_len = 0
        elif e.hit_vfx_t >= 0.0:
            e.hit_vfx_t = -1.0
            e.hit_vfx_len = 0
        if dist < e.radius + 14 and e.player_hit_cd <= 0:
            if e.kind in _IMP_FAMILY and e.imp_down:
                pass
            else:
                if e.kind == "boss":
                    dmg = 16.0
                elif e.kind == "imp":
                    dmg = 11.0
                else:
                    dmg = 6.0
                on_player_hit(dmg)
                e.player_hit_cd = 0.55

    _resolve_enemy_collisions(enemies, world_w, world_h, margin)


def _proj_can_hit_enemy(pr: Projectile, e: Enemy) -> bool:
    if e.kind in _IMP_FAMILY and e.imp_dead:
        return False
    if e.kind in _IMP_FAMILY and e.imp_down:
        return True
    if e.bullet_iframe > 0.0:
        return False
    return e.hp > 0.0


def _apply_projectile_hit_vfx(e: Enemy, hit_vfx_sets: list[list[pygame.Surface]]) -> None:
    e.hit_flash = 0.14
    e.hit_vfx_t = 0.0
    if hit_vfx_sets:
        e.hit_vfx_id = random.randrange(len(hit_vfx_sets))
        e.hit_vfx_len = len(hit_vfx_sets[e.hit_vfx_id])
    else:
        e.hit_vfx_len = 0


def _point_segment_dist(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    vx, vy = x2 - x1, y2 - y1
    sq = vx * vx + vy * vy
    if sq < 1e-12:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / sq))
    qx, qy = x1 + t * vx, y1 + t * vy
    return math.hypot(px - qx, py - qy)


def tech_zero_chain_zap(
    projectiles: list[Projectile],
    enemies: list[Enemy],
    gun: GunStats,
    dt: float,
    timer: list[float],
    hit_vfx_sets: list[list[pygame.Surface]],
    pulse_flash: list[float] | None = None,
) -> None:
    """Technology: chain lightning between bullets; pulse damage every 0.2s."""
    if gun.tech_zero_stacks <= 0 or len(projectiles) < 2:
        return
    timer[0] += dt
    if timer[0] < 0.2:
        return
    timer[0] -= 0.2
    dmg = max(0.12, gun.damage() * 0.25 * gun.tech_zero_stacks)
    reach = 14.0
    n = len(projectiles)
    max_d2 = TECH_ZERO_MAX_LINK_DIST * TECH_ZERO_MAX_LINK_DIST
    any_link = False
    for i in range(n):
        ax, ay = projectiles[i].x, projectiles[i].y
        bx, by = projectiles[(i + 1) % n].x, projectiles[(i + 1) % n].y
        dx, dy = bx - ax, by - ay
        if dx * dx + dy * dy > max_d2:
            continue
        any_link = True
        for e in enemies:
            if e.kind in _IMP_FAMILY and e.imp_dead:
                continue
            if e.kind in _IMP_FAMILY and e.imp_down:
                continue
            if e.bullet_iframe > 0.0:
                continue
            if e.hp <= 0.0:
                continue
            d = _point_segment_dist(e.x, e.y, ax, ay, bx, by)
            if d > e.radius + reach:
                continue
            e.hp -= dmg
            e.bullet_iframe = 0.35
            _apply_projectile_hit_vfx(e, hit_vfx_sets)
            if e.kind in _IMP_FAMILY and not e.imp_down and e.hp <= 0.0:
                e.hp = 0.0
                e.imp_down = True
                e.imp_revive = 3.0
    if pulse_flash is not None and any_link:
        pulse_flash[0] = 1.0


def thy_nuke_burst_projectiles(gun: GunStats, pr: Projectile) -> list[Projectile]:
    """25 random-direction child shots when a Thy Nuke mother tear dies."""
    if gun.thy_nuke_stacks <= 0 or not pr.nuke_mother:
        return []
    out: list[Projectile] = []
    spd = gun.speed() * 0.88
    dmg = max(0.12, gun.damage() * 0.30)
    rad = max(2.0, gun.radius() * 0.20)
    laser = gun.laser_visual
    rb = gun.rubber_cement_stacks > 0
    for _ in range(25):
        a = random.random() * math.tau
        dx, dy = math.cos(a), math.sin(a)
        rot_deg = math.degrees(math.atan2(dy, dx))
        out.append(
            Projectile(
                x=pr.x,
                y=pr.y,
                vx=dx * spd,
                vy=dy * spd,
                damage=dmg,
                radius=rad,
                hits_left=1,
                laser=laser,
                rot_deg=rot_deg,
                pierce_grows=False,
                spawn_fire_trail=False,
                trail_emit_cd=0.0,
                homing=False,
                rubber_bounce=rb,
                nuke_mother=False,
            )
        )
    return out


def projectiles_vs_enemies(
    projectiles: list[Projectile],
    enemies: list[Enemy],
    hit_vfx_sets: list[list[pygame.Surface]],
    gun: GunStats,
) -> list[Projectile]:
    """Mutates lists in place. Returns extra projectiles (e.g. Thy Nuke burst)."""
    spawned: list[Projectile] = []
    if not projectiles or not enemies:
        return spawned
    dead_p: set[int] = set()
    for pi, pr in enumerate(projectiles):
        if pi in dead_p:
            continue
        while pr.hits_left > 0:
            best: Enemy | None = None
            best_d = 1e18
            for e in enemies:
                if not _proj_can_hit_enemy(pr, e):
                    continue
                dist = math.hypot(pr.x - e.x, pr.y - e.y)
                if dist > pr.radius + e.radius:
                    continue
                if dist < best_d:
                    best_d = dist
                    best = e
            if best is None:
                break
            e = best
            if e.kind in _IMP_FAMILY and e.imp_down:
                e.imp_dead = True
                _apply_projectile_hit_vfx(e, hit_vfx_sets)
                pr.hits_left -= 1
                if pr.hits_left <= 0:
                    spawned.extend(thy_nuke_burst_projectiles(gun, pr))
                    dead_p.add(pi)
                break
            e.hp -= pr.damage
            e.bullet_iframe = 0.5
            _apply_projectile_hit_vfx(e, hit_vfx_sets)
            if e.kind in _IMP_FAMILY and not e.imp_down and e.hp <= 0.0:
                e.hp = 0.0
                e.imp_down = True
                e.imp_revive = 3.0
            pr.hits_left -= 1
            if pr.pierce_grows and pr.hits_left > 0:
                pr.radius *= 1.5
            if pr.hits_left <= 0:
                spawned.extend(thy_nuke_burst_projectiles(gun, pr))
                dead_p.add(pi)
                break
    for i in sorted(dead_p, reverse=True):
        projectiles.pop(i)
    return spawned


def cull_dead_enemies(
    enemies: list[Enemy],
    last_kill_xy: list[float] | None = None,
    bosses_cleared_count: list[int] | None = None,
) -> None:
    i = 0
    while i < len(enemies):
        e = enemies[i]
        if e.kind in _IMP_FAMILY and e.imp_dead:
            if bosses_cleared_count is not None and e.kind == "boss":
                bosses_cleared_count[0] += 1
            if last_kill_xy is not None and len(last_kill_xy) >= 2:
                last_kill_xy[0] = e.x
                last_kill_xy[1] = e.y
            enemies.pop(i)
        elif e.kind in _IMP_FAMILY and e.imp_down:
            i += 1
        elif e.hp <= 0:
            if last_kill_xy is not None and len(last_kill_xy) >= 2:
                last_kill_xy[0] = e.x
                last_kill_xy[1] = e.y
            enemies.pop(i)
        else:
            i += 1


def update_fire_zones(zones: list[FireZone], enemies: list[Enemy], dt: float) -> None:
    zi = 0
    while zi < len(zones):
        z = zones[zi]
        z.phase += dt * 14.0
        z.life -= dt
        if z.life <= 0.0:
            zones.pop(zi)
            continue
        for e in enemies:
            if e.kind in _IMP_FAMILY and e.imp_dead:
                continue
            if e.kind in _IMP_FAMILY and e.imp_down:
                continue
            dist = math.hypot(e.x - z.x, e.y - z.y)
            if dist >= z.radius + e.radius:
                continue
            e.hp -= z.dps * dt
            if e.kind in _IMP_FAMILY and not e.imp_down and e.hp <= 0.0:
                e.hp = 0.0
                e.imp_down = True
                e.imp_revive = 3.0
        zi += 1


def spawn_fire_embers(zones: list[FireZone], dt: float, out: list[FireEmber]) -> None:
    if not zones:
        return
    for z in zones:
        chance = min(0.9, 10.5 * dt * (0.35 + z.life / 0.5))
        if random.random() < chance:
            out.append(
                FireEmber(
                    z.x + random.uniform(-6, 6),
                    z.y + random.uniform(-6, 6),
                    random.uniform(-42, 42),
                    random.uniform(-100, -38),
                    random.uniform(0.2, 0.52),
                    random.randint(235, 255),
                    random.randint(100, 185),
                    random.randint(28, 75),
                )
            )


def update_fire_embers(embers: list[FireEmber], dt: float) -> None:
    i = 0
    while i < len(embers):
        e = embers[i]
        e.life -= dt
        e.x += e.vx * dt
        e.y += e.vy * dt
        e.vx *= 0.987
        e.vy -= 14.0 * dt
        if e.life <= 0:
            embers.pop(i)
            continue
        i += 1


def draw_fire_puddles(target: pygame.Surface, zones: list[FireZone], cam: tuple[float, float]) -> None:
    cam_x, cam_y = cam
    for z in zones:
        zx, zy = int(z.x - cam_x), int(z.y - cam_y)
        r = int(z.radius)
        pulse = 0.68 + 0.32 * math.sin(z.phase)
        dia = max(14, r * 2 + 12)
        s = pygame.Surface((dia, dia), pygame.SRCALPHA)
        ctr = dia // 2
        pygame.draw.circle(s, (255, 245, 170, int(32 * pulse)), (ctr, ctr), int(r * 1.06))
        pygame.draw.circle(s, (255, 155, 65, int(58 * pulse)), (ctr, ctr), int(r * 0.82))
        pygame.draw.circle(s, (255, 65, 28, int(88 * pulse)), (ctr, ctr), max(4, int(r * 0.52)))
        target.blit(s, (zx - ctr, zy - ctr))
        pygame.draw.circle(target, (85, 38, 14), (zx, zy), r, width=2)


def draw_fire_embers(target: pygame.Surface, embers: list[FireEmber], cam: tuple[float, float]) -> None:
    cam_x, cam_y = cam
    for e in embers:
        t = max(0.0, e.life / 0.45)
        rad = max(1, int(2.2 * t))
        rr = min(255, int(e.r * (0.55 + 0.45 * t)))
        gg = min(255, int(e.g * (0.55 + 0.45 * t)))
        bb = min(255, int(e.b * (0.55 + 0.45 * t)))
        pygame.draw.circle(
            target,
            (rr, gg, bb),
            (int(e.x - cam_x), int(e.y - cam_y)),
            rad,
        )


def draw_enemy(
    target: pygame.Surface,
    art: HostileArt,
    e: Enemy,
    cam: tuple[float, float],
) -> None:
    frames = art.enemy_frames(
        e.kind,
        imp_down=(e.kind in _IMP_FAMILY and e.imp_down),
        imp_moving=(e.kind in _IMP_FAMILY and e.imp_moving),
    )
    f = int(e.anim_t * 10.0) % len(frames)
    img = frames[f]
    if e.kind == "boss":
        h = 124
        w = max(1, int(img.get_width() * (h / max(1, img.get_height()))))
        img = pygame.transform.scale(img, (w, h))
    elif e.kind == "imp":
        h = 96
        w = max(1, int(img.get_width() * (h / max(1, img.get_height()))))
        img = pygame.transform.scale(img, (w, h))
    elif e.kind in ("spider", "scifi"):
        h = 52
        w = max(1, int(img.get_width() * (h / max(1, img.get_height()))))
        img = pygame.transform.scale(img, (w, h))
    elif e.kind == "critter":
        h = 40
        w = max(1, int(img.get_width() * (h / max(1, img.get_height()))))
        img = pygame.transform.scale(img, (w, h))
    else:
        h = 40
        w = max(1, int(img.get_width() * (h / max(1, img.get_height()))))
        img = pygame.transform.scale(img, (w, h))
    if e.hit_flash > 0.0:
        try:
            m = pygame.mask.from_surface(img)
            img = m.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        except (ValueError, pygame.error):
            tmp = img.convert_alpha()
            try:
                m2 = pygame.mask.from_surface(tmp)
                img = m2.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
            except (ValueError, pygame.error):
                img = tmp
                img.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MAX)
    cam_x, cam_y = cam
    rect = img.get_rect(center=(int(e.x - cam_x), int(e.y - cam_y)))
    target.blit(img, rect.topleft)
    if e.hit_vfx_t >= 0.0 and art.hit_vfx_sets and e.hit_vfx_len > 0:
        clip = art.hit_vfx_sets[e.hit_vfx_id % len(art.hit_vfx_sets)]
        idx = min(len(clip) - 1, int(e.hit_vfx_t * HIT_VFX_FPS))
        fx = clip[idx]
        r2 = fx.get_rect(center=(int(e.x - cam_x), int(e.y - cam_y)))
        target.blit(fx, r2.topleft)


def draw_technology_zero_chain(
    target: pygame.Surface,
    projectiles: list[Projectile],
    gun: GunStats,
    cam: tuple[float, float],
    pulse_strength: float,
) -> None:
    """Blue electric-style segments between consecutive bullets (cycle)."""
    if gun.tech_zero_stacks <= 0 or len(projectiles) < 2:
        return
    cam_x, cam_y = cam
    n = len(projectiles)
    a = 0.35 + 0.45 * max(0.0, min(1.0, pulse_strength))
    col_core = (120, 200, 255)
    col_glow = (60, 140, 220)
    w_core = max(2, 1 + gun.tech_zero_stacks)
    w_glow = w_core + 4
    max_d2 = TECH_ZERO_MAX_LINK_DIST * TECH_ZERO_MAX_LINK_DIST
    for i in range(n):
        p0, p1 = projectiles[i], projectiles[(i + 1) % n]
        dx, dy = p1.x - p0.x, p1.y - p0.y
        if dx * dx + dy * dy > max_d2:
            continue
        ax = int(p0.x - cam_x)
        ay = int(p0.y - cam_y)
        bx = int(p1.x - cam_x)
        by = int(p1.y - cam_y)
        pygame.draw.line(target, col_glow, (ax, ay), (bx, by), w_glow)
        pygame.draw.line(target, col_core, (ax, ay), (bx, by), w_core)
        # small jitter nodes for "electric" feel
        mx, my = (ax + bx) // 2, (ay + by) // 2
        pygame.draw.circle(target, (200, 235, 255), (mx, my), max(2, w_core))


def draw_projectile(
    target: pygame.Surface,
    art: HostileArt,
    p: Projectile,
    cam: tuple[float, float],
) -> None:
    cam_x, cam_y = cam
    sx, sy = int(p.x - cam_x), int(p.y - cam_y)
    if p.laser:
        raw = art.bullet_laser
        ang = math.radians(p.rot_deg)
        w = max(int(p.radius * 4), 12)
        h = max(int(p.radius * 2), 6)
        img = pygame.transform.scale(raw, (w, h))
        img = pygame.transform.rotate(img, -p.rot_deg)
        r = img.get_rect(center=(sx, sy))
        target.blit(img, r.topleft)
    else:
        r = int(max(2, p.radius))
        if p.homing:
            pygame.draw.circle(target, (255, 90, 140), (sx, sy), r + 1)
            pygame.draw.circle(target, (255, 210, 235), (sx, sy), r)
        else:
            pygame.draw.circle(target, (255, 230, 120), (sx, sy), r)


def fire_from_player(
    gun: GunStats,
    px: float,
    py: float,
    mwx: float,
    mwy: float,
    _art: HostileArt,
    chocolate_charge: float = 0.0,
) -> list[Projectile]:
    """Aim toward cursor; The Wiz adds diagonal pairs per stack; Gambling adds random-direction shots."""
    adx, ady = mwx - px, mwy - py
    dist = math.hypot(adx, ady) or 1.0
    dx, dy = adx / dist, ady / dist

    def rot(ax: float, ay: float, rad: float) -> tuple[float, float]:
        c, s = math.cos(rad), math.sin(rad)
        return ax * c - ay * s, ax * s + ay * c

    # The Wiz (Repentance+): two diagonal tears at ±38°; each *extra* copy adds
    # one straight shot (wiki.gg — "one extra tear...forwards").
    unit_dirs: list[tuple[float, float]] = []
    if gun.wiz_stacks <= 0:
        unit_dirs.append((dx, dy))
    else:
        ang = math.radians(38)
        unit_dirs.append(rot(dx, dy, ang))
        unit_dirs.append(rot(dx, dy, -ang))
        for _ in range(max(0, gun.wiz_stacks - 1)):
            unit_dirs.append((dx, dy))

    for _ in range(5 * gun.gambling_stacks):
        a = random.random() * math.tau
        unit_dirs.append((math.cos(a), math.sin(a)))
    for _ in range(3 * gun.hive_mind_stacks):
        a = random.random() * math.tau
        unit_dirs.append((math.cos(a), math.sin(a)))

    spd = gun.speed()
    dmg = gun.damage()
    rad = gun.radius()
    if gun.chocolate_milk_stacks > 0 and chocolate_charge > 0.0:
        cc = chocolate_charge**0.62
        dmg *= 0.38 + 0.62 * cc
        rad *= 0.45 + 0.58 * cc
    hl = 1 + gun.pierce_bonus
    laser = gun.laser_visual
    pgrow = gun.pierce_grows
    trail = gun.fire_trail
    hom = (
        gun.sacred_heart_stacks > 0
        or gun.spoon_bender_stacks > 0
        or gun.big_brain_stacks > 0
    )
    rb = gun.rubber_cement_stacks > 0

    n_par = max(1, 1 + gun.parallel_extra + gun.double_cannon_bonus)

    nuke_m = gun.thy_nuke_stacks > 0

    def make_one(ox: float, oy: float, vx: float, vy: float) -> Projectile:
        vlen = math.hypot(vx, vy) or 1.0
        nx, ny = vx / vlen, vy / vlen
        rot_deg = math.degrees(math.atan2(ny, nx))
        return Projectile(
            x=px + ox,
            y=py + oy,
            vx=nx * spd,
            vy=ny * spd,
            damage=dmg,
            radius=rad,
            hits_left=hl,
            laser=laser,
            rot_deg=rot_deg,
            pierce_grows=pgrow,
            spawn_fire_trail=trail,
            trail_emit_cd=0.0,
            homing=hom,
            rubber_bounce=rb,
            nuke_mother=nuke_m,
        )

    out: list[Projectile] = []
    for bdx, bdy in unit_dirs:
        if n_par == 1:
            out.append(make_one(0.0, 0.0, bdx, bdy))
        else:
            for i in range(n_par):
                t = (i - (n_par - 1) / 2.0) * 2.0 / (n_par - 1)
                ox, oy = -bdy * 7.0 * t, bdx * 7.0 * t
                out.append(make_one(ox, oy, bdx, bdy))
    return out


def fire_radial_retaliation(
    gun: GunStats,
    px: float,
    py: float,
    _art: HostileArt,
) -> list[Projectile]:
    """Ring shots (lion shield); stacks raise lion_ring_count (5+ per stack)."""
    if gun.lion_ring_count < 5:
        return []
    n = gun.lion_ring_count
    spd = gun.speed()
    dmg = gun.damage()
    rad = gun.radius()
    laser = gun.laser_visual
    hom = (
        gun.sacred_heart_stacks > 0
        or gun.spoon_bender_stacks > 0
        or gun.big_brain_stacks > 0
    )
    rb = gun.rubber_cement_stacks > 0
    out: list[Projectile] = []
    for i in range(n):
        ang = i * (2.0 * math.pi / n)
        dx, dy = math.cos(ang), math.sin(ang)
        rot = math.degrees(math.atan2(dy, dx))
        out.append(
            Projectile(
                x=px,
                y=py,
                vx=dx * spd,
                vy=dy * spd,
                damage=dmg,
                radius=rad,
                hits_left=1,
                laser=laser,
                rot_deg=rot,
                pierce_grows=False,
                spawn_fire_trail=False,
                trail_emit_cd=0.0,
                homing=hom,
                rubber_bounce=rb,
            )
        )
    return out


def steer_homing_projectiles(
    projectiles: list[Projectile],
    enemies: list[Enemy],
    dt: float,
    turn_rate: float = 5.8,
) -> None:
    """Curve bullets toward the nearest valid target."""
    for pr in projectiles:
        if not pr.homing:
            continue
        best: Enemy | None = None
        best_d = 1e18
        for e in enemies:
            if e.kind in _IMP_FAMILY and e.imp_dead:
                continue
            if e.hp <= 0.0 and not (e.kind in _IMP_FAMILY and e.imp_down):
                continue
            d = math.hypot(e.x - pr.x, e.y - pr.y)
            if d < best_d:
                best_d = d
                best = e
        if best is None:
            continue
        tx, ty = best.x - pr.x, best.y - pr.y
        td = math.hypot(tx, ty) or 1.0
        tx, ty = tx / td, ty / td
        spd = math.hypot(pr.vx, pr.vy)
        if spd < 8.0:
            spd = 420.0
        vx, vy = pr.vx / spd, pr.vy / spd
        cross = vx * ty - vy * tx
        dot = max(-1.0, min(1.0, vx * tx + vy * ty))
        ang = math.atan2(cross, dot)
        step = turn_rate * dt
        if ang > step:
            ang = step
        elif ang < -step:
            ang = -step
        ca, sa = math.cos(ang), math.sin(ang)
        nx = vx * ca - vy * sa
        ny = vx * sa + vy * ca
        pr.vx = nx * spd
        pr.vy = ny * spd
        pr.rot_deg = math.degrees(math.atan2(pr.vy, pr.vx))
