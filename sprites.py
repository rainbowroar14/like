"""
High-detail procedural pixel tiles (Stardew-inspired): shading, shadows, texture.
Tile size is larger than 64 so each cell can hold more painted detail.
"""
from __future__ import annotations

import math
import random

import pygame

# Larger tiles = room for shading, roof lines, ground shadows (still one tile per map cell).
TILE = 96


def _surf() -> pygame.Surface:
    return pygame.Surface((TILE, TILE), pygame.SRCALPHA)


def _clamp_rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
    return max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))


def _shade(c: tuple[int, int, int], dr: int, dg: int, db: int) -> tuple[int, int, int]:
    return _clamp_rgb(c[0] + dr, c[1] + dg, c[2] + db)


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _ground_shadow(s: pygame.Surface, cx: int, cy: int, rw: int, rh: int, strength: int = 70) -> None:
    """Soft greenish shadow blob (light from upper-left)."""
    for i in range(4):
        a = max(0, strength - i * 18)
        pygame.draw.ellipse(s, (28, 48, 28, a), (cx - rw // 2 + i, cy - rh // 2 + i, rw - i * 2, rh - i * 2))


def _dither_noise(s: pygame.Surface, palette: list[tuple[int, int, int]], seed: int, amount: float) -> None:
    rng = random.Random(seed)
    for _ in range(int(TILE * TILE * amount)):
        x, y = rng.randint(0, TILE - 1), rng.randint(0, TILE - 1)
        s.set_at((x, y), rng.choice(palette))


def make_grass(seed: int = 0) -> pygame.Surface:
    s = _surf()
    c_tl = (78, 158, 72)
    c_br = (52, 118, 56)
    for y in range(TILE):
        for x in range(TILE):
            t = (x + y) / (TILE * 2 - 2)
            col = _blend(c_tl, c_br, t * 0.55 + random.Random(seed + x * 97 + y).random() * 0.08)
            s.set_at((x, y), col)
    accents = [
        (92, 178, 82),
        (64, 132, 60),
        (110, 192, 96),
        (58, 122, 54),
        (88, 168, 78),
    ]
    _dither_noise(s, accents, seed, 0.12)
    rng = random.Random(seed + 501)
    # tiny flower specks
    for _ in range(28):
        fx = rng.randint(4, TILE - 5)
        fy = rng.randint(4, TILE - 5)
        pet = rng.choice([(235, 120, 150), (240, 210, 90), (200, 200, 240), (255, 255, 255)])
        s.set_at((fx, fy), pet)
        s.set_at((fx + 1, fy), _shade(pet, -20, -20, -20))
    # grass blade clusters
    for _ in range(35):
        bx = rng.randint(0, TILE - 3)
        by = rng.randint(0, TILE - 3)
        c = rng.choice(accents)
        s.set_at((bx, by), c)
        s.set_at((bx + 1, by - 1), _shade(c, 10, 14, 8))
    return s


def make_path(seed: int = 0) -> pygame.Surface:
    s = _surf()
    base = (188, 148, 98)
    s.fill(base)
    dark = (158, 118, 72)
    light = (212, 176, 128)
    mid = (172, 132, 88)
    rng = random.Random(seed)
    for y in range(TILE):
        for x in range(TILE):
            n = rng.random()
            if n < 0.12:
                s.set_at((x, y), dark)
            elif n < 0.22:
                s.set_at((x, y), light)
            elif n < 0.3:
                s.set_at((x, y), mid)
    # worn wheel ruts
    pygame.draw.arc(s, _shade(base, -25, -20, -15), (-20, TILE // 2 - 6, TILE + 40, 40), 0.1, 3.0, 2)
    pygame.draw.arc(s, _shade(base, -30, -25, -18), (-10, TILE // 2 + 2, TILE + 30, 36), 0.05, 3.1, 2)
    # pebbles
    for _ in range(50):
        px, py = rng.randint(0, TILE - 1), rng.randint(0, TILE - 1)
        s.set_at((px, py), rng.choice([light, dark, (145, 108, 68)]))
    return s


def make_water(frame: int, seed: int = 0) -> pygame.Surface:
    s = _surf()
    deep = (42, 98, 168)
    mid = (62, 138, 208)
    bright = (118, 198, 248)
    foam = (200, 232, 255)
    rng = random.Random(seed + frame * 47)
    for y in range(TILE):
        wave = int(4 * math.sin(y / 14.0 + frame * 0.35))
        depth = y / TILE
        for x in range(TILE):
            wx = x + wave
            cell = (wx // 5 + y // 6 + frame) % 6
            base = _blend(mid, deep, depth * 0.45)
            if cell <= 1:
                c = deep
            elif cell >= 4:
                c = bright
            else:
                c = base
            if rng.random() < 0.06:
                c = rng.choice([bright, deep])
            s.set_at((x, y), c)
    # sparkle / foam band along top edge (neighbor land reads as "shore")
    for x in range(0, TILE, 2):
        t = (x + frame * 3) % 9
        if t < 3:
            s.set_at((x, 0), foam)
            s.set_at((x + 1, 1), _shade(foam, -25, -20, -15))
    return s


def make_bridge() -> pygame.Surface:
    s = _surf()
    s.fill((0, 0, 0, 0))
    _ground_shadow(s, TILE // 2, TILE - 10, TILE - 8, 14, 55)
    rail = (110, 78, 48)
    plank_hi = (168, 122, 74)
    plank_lo = (138, 98, 58)
    nail = (60, 48, 40)
    y0 = 10
    for i in range(6):
        y = y0 + i * 13
        pygame.draw.rect(s, plank_lo, (6, y, TILE - 12, 12))
        pygame.draw.rect(s, plank_hi, (6, y, TILE - 12, 4))
        pygame.draw.line(s, _shade(plank_lo, -18, -14, -10), (6, y + 11), (TILE - 7, y + 11), 1)
        for nx in range(14, TILE - 8, 16):
            pygame.draw.circle(s, nail, (nx, y + 6), 1)
    pygame.draw.rect(s, rail, (4, y0 - 4, 4, TILE - 18))
    pygame.draw.rect(s, _shade(rail, 18, 14, 10), (4, y0 - 4, 2, TILE - 18))
    pygame.draw.rect(s, rail, (TILE - 8, y0 - 4, 4, TILE - 18))
    pygame.draw.rect(s, _shade(rail, -14, -12, -10), (TILE - 6, y0 - 4, 2, TILE - 18))
    return s


def make_plaza() -> pygame.Surface:
    s = _surf()
    rng = random.Random(202)
    cell = 12
    for gy in range(0, TILE, cell):
        for gx in range(0, TILE, cell):
            idx = (gx // cell + gy // cell + rng.randint(0, 1)) % 2
            base = (124, 126, 132) if idx == 0 else (138, 140, 146)
            pygame.draw.rect(s, base, (gx, gy, cell, cell))
            # grout
            pygame.draw.rect(s, (88, 90, 96), (gx, gy, cell, cell), 1)
            # chips / wear
            for _ in range(3):
                sx = gx + rng.randint(1, cell - 2)
                sy = gy + rng.randint(1, cell - 2)
                s.set_at((sx, sy), _shade(base, rng.randint(-12, 12), rng.randint(-12, 12), rng.randint(-12, 12)))
    _dither_noise(s, [(108, 110, 116), (152, 154, 158)], 303, 0.04)
    return s


def make_plaza_center() -> pygame.Surface:
    s = make_plaza()
    cx, cy = TILE // 2, TILE // 2
    # brick ring pattern
    for r in (34, 28, 22, 16):
        pygame.draw.circle(s, (150, 62, 62), (cx, cy), r, 2)
        pygame.draw.circle(s, (120, 48, 48), (cx, cy), r, 1)
    pygame.draw.circle(s, (178, 82, 82), (cx, cy), 14)
    pygame.draw.circle(s, (210, 110, 110), (cx, cy), 9)
    pygame.draw.circle(s, (95, 38, 38), (cx, cy), 4)
    # highlight arc (light from NW)
    for i in range(6):
        pygame.draw.arc(s, (230, 150, 150), (cx - 10 - i, cy - 10 - i, 20 + i * 2, 20 + i * 2), 2.2, 4.0, 1)
    return s


def make_tree(cherry: bool = False, seed: int = 0) -> pygame.Surface:
    s = _surf()
    rng = random.Random(seed)
    _ground_shadow(s, TILE // 2 + 4, TILE - 8, TILE - 20, 18, 65)

    trunk_l = (78, 52, 36)
    trunk_r = (110, 78, 52)
    trunk_d = (58, 40, 28)
    tx, tw, th = TILE // 2 - 10, 20, 38
    ty = TILE - th - 6
    for row in range(th):
        t = row / th
        c = _blend(trunk_l, trunk_r, t)
        pygame.draw.line(s, c, (tx, ty + row), (tx + tw - 1, ty + row), 1)
    pygame.draw.line(s, trunk_d, (tx, ty), (tx, ty + th - 1), 2)
    pygame.draw.line(s, _shade(trunk_r, 22, 18, 14), (tx + tw - 1, ty), (tx + tw - 1, ty + th - 1), 2)

    if cherry:
        pal = [(228, 120, 158), (210, 96, 138), (250, 188, 210), (200, 82, 130)]
        dark = (140, 60, 100)
    else:
        pal = [(52, 138, 72), (40, 118, 60), (78, 168, 92), (34, 98, 52)]
        dark = (24, 72, 40)

    blobs = [
        (TILE // 2, 26, 26),
        (TILE // 2 - 22, 38, 22),
        (TILE // 2 + 22, 36, 22),
        (TILE // 2 - 10, 14, 24),
        (TILE // 2 + 14, 16, 20),
    ]
    for bx, by, br in blobs:
        pygame.draw.circle(s, rng.choice(pal), (bx, by), br)
        pygame.draw.circle(s, dark, (bx + 4, by + 5), br - 4)
        pygame.draw.circle(s, rng.choice(pal), (bx - 3, by - 4), max(6, br // 3))
    # rim light
    pygame.draw.arc(s, pal[3], (TILE // 2 - 28, 8, 56, 48), 2.0, 5.0, 2)
    return s


def make_bush(seed: int = 0) -> pygame.Surface:
    s = _surf()
    rng = random.Random(seed)
    _ground_shadow(s, TILE // 2, TILE - 6, 44, 12, 50)
    cols = [(44, 118, 62), (36, 102, 54), (58, 132, 74), (32, 92, 48)]
    for _ in range(14):
        bx = TILE // 2 + rng.randint(-22, 22)
        by = TILE // 2 + 12 + rng.randint(-12, 14)
        r = rng.randint(14, 22)
        pygame.draw.circle(s, rng.choice(cols), (bx, by), r)
        pygame.draw.circle(s, _shade(rng.choice(cols), -18, -22, -14), (bx + 3, by + 4), r - 6)
    return s


def make_fence() -> pygame.Surface:
    s = _surf()
    wood = (168, 124, 76)
    dark = (118, 82, 48)
    hi = _shade(wood, 22, 18, 12)
    posts = [14, TILE // 2, TILE - 14]
    for px in posts:
        pygame.draw.rect(s, wood, (px - 5, 28, 10, TILE - 32))
        pygame.draw.rect(s, dark, (px - 5, 28, 3, TILE - 32))
        pygame.draw.rect(s, hi, (px + 2, 28, 2, TILE - 32))
        pygame.draw.rect(s, hi, (px - 6, 26, 12, 4))
    pygame.draw.rect(s, wood, (8, 40, TILE - 16, 8))
    pygame.draw.rect(s, dark, (8, 44, TILE - 16, 2))
    pygame.draw.rect(s, hi, (8, 40, TILE - 16, 2))
    return s


def make_house(roof_color: tuple[int, int, int], wall_color: tuple[int, int, int]) -> pygame.Surface:
    s = _surf()
    _ground_shadow(s, TILE // 2 + 6, TILE - 6, TILE - 16, 20, 72)

    stone = (120, 118, 122)
    stone_d = (88, 86, 90)
    # foundation
    pygame.draw.rect(s, stone, (16, TILE - 28, TILE - 32, 16))
    for i in range(5):
        pygame.draw.line(s, stone_d, (18 + i * 14, TILE - 28), (18 + i * 14, TILE - 14), 1)

    wx, wy, ww, wh = 18, 46, TILE - 36, 44
    # walls with vertical plank hint
    pygame.draw.rect(s, wall_color, (wx, wy, ww, wh))
    for i in range(1, 5):
        x = wx + i * (ww // 5)
        pygame.draw.line(s, _shade(wall_color, -12, -10, -14), (x, wy), (x, wy + wh - 1), 1)
    pygame.draw.rect(s, _shade(wall_color, -22, -20, -24), (wx, wy, 8, wh))
    pygame.draw.rect(s, _shade(wall_color, 12, 10, 8), (wx + ww - 3, wy, 3, wh))

    # roof
    peak = (TILE // 2, 18)
    left = (wx - 6, wy + 4)
    right = (wx + ww + 6, wy + 4)
    pygame.draw.polygon(s, roof_color, [peak, left, right])
    pygame.draw.polygon(s, _shade(roof_color, -35, -30, -28), [peak, left, (left[0], left[1] + 6), (peak[0] - 2, peak[1] + 8)])
    # shingle rows
    for row in range(5):
        y = 22 + row * 7
        pygame.draw.line(s, _shade(roof_color, -20, -18, -16), (wx - 4 + row, y), (wx + ww + 4 - row, y), 1)
    pygame.draw.polygon(s, _shade(roof_color, -45, -40, -38), [peak, left, right], 2)

    # chimney
    pygame.draw.rect(s, (130, 72, 62), (TILE // 2 + 16, 24, 10, 22))
    pygame.draw.rect(s, _shade((130, 72, 62), 20, 14, 12), (TILE // 2 + 16, 24, 3, 22))

    # window
    pygame.draw.rect(s, (72, 52, 42), (wx + 10, wy + 10, 22, 18))
    pygame.draw.rect(s, (150, 190, 215), (wx + 12, wy + 12, 18, 14))
    pygame.draw.line(s, (92, 118, 138), (wx + 21, wy + 12), (wx + 21, wy + 25), 1)
    pygame.draw.line(s, (92, 118, 138), (wx + 12, wy + 19), (wx + 29, wy + 19), 1)
    pygame.draw.rect(s, (200, 230, 255), (wx + 14, wy + 13, 4, 4))

    # door
    dw, dh = 18, 30
    dx = wx + ww - dw - 12
    pygame.draw.rect(s, (86, 56, 40), (dx, wy + wh - dh, dw, dh))
    pygame.draw.rect(s, _shade((86, 56, 40), 18, 12, 10), (dx, wy + wh - dh, 4, dh))
    pygame.draw.circle(s, (210, 190, 120), (dx + dw - 6, wy + wh - dh // 2), 2)

    # flower box under window
    pygame.draw.rect(s, (92, 62, 44), (wx + 8, wy + 28, 26, 8))
    for fx in range(3):
        pygame.draw.circle(s, (255, 92, 120), (wx + 14 + fx * 8, wy + 26), 3)
    return s


def make_clinic() -> pygame.Surface:
    s = _surf()
    _ground_shadow(s, TILE // 2 + 4, TILE - 4, TILE - 10, 22, 75)
    wall = (78, 118, 168)
    wall_d = _shade(wall, -28, -24, -22)
    trim = (52, 82, 128)
    pygame.draw.rect(s, wall, (8, 36, TILE - 16, TILE - 44))
    pygame.draw.rect(s, wall_d, (8, 36, 12, TILE - 44))
    pygame.draw.rect(s, trim, (8, 32, TILE - 16, 10))
    # columns
    for px in (18, TILE // 2, TILE - 18):
        pygame.draw.rect(s, _shade(wall, 16, 14, 12), (px - 4, 40, 8, TILE - 50))
        pygame.draw.rect(s, wall_d, (px - 4, 40, 3, TILE - 50))
    # windows
    for x0 in (14, 38, 62, TILE - 38):
        pygame.draw.rect(s, (62, 48, 42), (x0, 48, 18, 22))
        pygame.draw.rect(s, (170, 210, 235), (x0 + 2, 50, 14, 18))
        pygame.draw.line(s, (100, 130, 155), (x0 + 9, 50), (x0 + 9, 66), 1)
        pygame.draw.line(s, (100, 130, 155), (x0 + 2, 58), (x0 + 16, 58), 1)
    pygame.draw.rect(s, (58, 42, 34), (TILE // 2 - 12, TILE - 40, 24, 34))
    pygame.draw.rect(s, (92, 62, 48), (TILE // 2 - 10, TILE - 38, 20, 30))
    return s


def make_fountain() -> pygame.Surface:
    s = make_plaza()
    _ground_shadow(s, TILE // 2, TILE - 8, 52, 16, 40)
    cx, cy = TILE // 2, TILE // 2 + 4
    pygame.draw.ellipse(s, (108, 112, 118), (cx - 28, cy - 10, 56, 36))
    pygame.draw.ellipse(s, _shade((108, 112, 118), 16, 16, 16), (cx - 28, cy - 10, 56, 36), 2)
    pygame.draw.ellipse(s, (72, 140, 190), (cx - 22, cy - 4, 44, 26))
    pygame.draw.ellipse(s, (130, 200, 235), (cx - 18, cy, 36, 18))
    pygame.draw.rect(s, (128, 130, 136), (cx - 8, cy - 28, 16, 22))
    pygame.draw.rect(s, (98, 100, 105), (cx - 8, cy - 28, 5, 22))
    pygame.draw.rect(s, (148, 150, 155), (cx - 10, cy - 32, 20, 8))
    # water highlight
    pygame.draw.circle(s, (220, 245, 255), (cx - 8, cy + 4), 3)
    return s


def make_garden() -> pygame.Surface:
    s = make_grass(seed=888)
    soil_t = (132, 88, 54)
    soil_d = (98, 64, 40)
    pygame.draw.rect(s, soil_t, (22, 28, TILE - 44, TILE - 48))
    for row in range(0, TILE - 48, 6):
        pygame.draw.line(s, soil_d, (24, 32 + row), (TILE - 26, 32 + row), 1)
    # crop rows
    rng = random.Random(42)
    for row in range(5):
        for col in range(7):
            sx = 26 + col * 8
            sy = 34 + row * 10
            if rng.random() < 0.85:
                pygame.draw.rect(s, (58, 128, 62), (sx, sy, 4, 8))
                pygame.draw.rect(s, (78, 168, 82), (sx + 1, sy - 2, 2, 4))
    pygame.draw.rect(s, (140, 100, 62), (20, 26, TILE - 40, 4))
    return s


def make_lamp() -> pygame.Surface:
    s = _surf()
    pole_t = (62, 64, 70)
    pole_b = (38, 40, 46)
    px = TILE // 2
    for y in range(28, TILE - 8):
        t = (y - 28) / (TILE - 36)
        c = _blend(pole_t, pole_b, t)
        pygame.draw.line(s, c, (px, y), (px + 3, y), 2)
    pygame.draw.rect(s, (48, 48, 52), (px - 8, TILE - 10, 18, 6))
    # lantern
    pygame.draw.circle(s, (255, 248, 200), (px + 2, 22), 12)
    pygame.draw.circle(s, (240, 220, 140), (px + 2, 22), 8)
    pygame.draw.circle(s, (50, 52, 58), (px + 2, 22), 12, 2)
    pygame.draw.rect(s, (44, 46, 50), (px - 2, 14, 8, 6))
    return s


def make_bench() -> pygame.Surface:
    s = _surf()
    _ground_shadow(s, TILE // 2, TILE - 6, 56, 12, 45)
    w = (142, 102, 64)
    hi = _shade(w, 20, 16, 12)
    lo = _shade(w, -18, -14, -12)
    pygame.draw.rect(s, w, (12, 52, TILE - 24, 10))
    pygame.draw.rect(s, hi, (12, 52, TILE - 24, 3))
    pygame.draw.rect(s, w, (12, 42, TILE - 24, 8))
    pygame.draw.rect(s, hi, (12, 42, TILE - 24, 2))
    pygame.draw.rect(s, lo, (14, 58, 6, 14))
    pygame.draw.rect(s, lo, (TILE - 20, 58, 6, 14))
    return s


DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT = 0, 1, 2, 3


def make_townsperson(
    shirt: tuple[int, int, int],
    pants: tuple[int, int, int],
    hair: tuple[int, int, int],
    skin: tuple[int, int, int] = (235, 198, 168),
) -> list[list[pygame.Surface]]:
    out: list[list[pygame.Surface]] = [[], [], [], []]

    def draw_frame(direction: int, frame: int) -> pygame.Surface:
        surf = _surf()
        bob = 1 if frame == 1 else 0
        y0 = 14 - bob
        leg_w, leg_h = 12, 28
        # shadow
        pygame.draw.ellipse(surf, (0, 0, 0, 55), (TILE // 2 - 22, TILE - 18, 44, 14))

        leg_off = 3 if frame == 1 else 0
        if direction in (DIR_DOWN, DIR_UP):
            pygame.draw.rect(surf, pants, (TILE // 2 - leg_w - leg_off, 58 + y0, leg_w, leg_h))
            pygame.draw.rect(surf, _shade(pants, -16, -14, -18), (TILE // 2 - leg_w - leg_off, 58 + y0, 4, leg_h))
            pygame.draw.rect(surf, pants, (TILE // 2 + leg_off, 58 + y0, leg_w, leg_h))
            pygame.draw.rect(surf, _shade(pants, -16, -14, -18), (TILE // 2 + leg_off, 58 + y0, 4, leg_h))
        else:
            pygame.draw.rect(surf, pants, (TILE // 2 - 8, 58 + y0, 18, leg_h))
            pygame.draw.rect(surf, _shade(pants, -18, -16, -20), (TILE // 2 - 8, 58 + y0, 5, leg_h))
        # shoes
        shoe = (52, 48, 52)
        pygame.draw.rect(surf, shoe, (TILE // 2 - 18, TILE - 14, 14, 6))
        pygame.draw.rect(surf, shoe, (TILE // 2 + 4, TILE - 14, 14, 6))

        bw, bh = 34, 36
        bx = TILE // 2 - bw // 2
        by = 34 + y0
        pygame.draw.rect(surf, shirt, (bx, by, bw, bh))
        pygame.draw.rect(surf, _shade(shirt, -20, -18, -22), (bx, by, 8, bh))
        pygame.draw.line(surf, _shade(shirt, 12, 10, 8), (bx + bw // 2, by + 4), (bx + bw // 2, by + bh - 4), 1)

        hx, hy, hw, hh = TILE // 2 - 14, 12 + y0, 28, 26
        pygame.draw.ellipse(surf, skin, (hx, hy, hw, hh))
        pygame.draw.arc(surf, hair, (hx - 2, hy - 6, hw + 4, hh + 10), 3.25, 6.1, 4)
        pygame.draw.rect(surf, hair, (hx + 2, hy - 4, hw - 4, 12))
        pygame.draw.rect(surf, _shade(hair, -25, -22, -20), (hx + 2, hy - 4, 6, 12))

        eye = (48, 50, 58)
        if direction == DIR_DOWN:
            pygame.draw.rect(surf, eye, (hx + 7, hy + 12, 3, 3))
            pygame.draw.rect(surf, eye, (hx + 18, hy + 12, 3, 3))
            pygame.draw.rect(surf, (200, 140, 150), (hx + 10, hy + 20, 8, 2))
        elif direction == DIR_LEFT:
            pygame.draw.rect(surf, eye, (hx + 6, hy + 11, 3, 3))
        elif direction == DIR_RIGHT:
            pygame.draw.rect(surf, eye, (hx + 19, hy + 11, 3, 3))

        arm_x = -4 if frame == 0 else 4
        aw, ah = 10, 22
        if direction == DIR_LEFT:
            pygame.draw.rect(surf, shirt, (bx - 10 + arm_x, by + 4, aw, ah))
        elif direction == DIR_RIGHT:
            pygame.draw.rect(surf, shirt, (bx + bw - aw + 10 - arm_x, by + 4, aw, ah))
        else:
            pygame.draw.rect(surf, shirt, (bx - 8, by + 8 + arm_x, aw, ah - 4))
            pygame.draw.rect(surf, shirt, (bx + bw - aw + 8, by + 8 - arm_x, aw, ah - 4))
        return surf

    for d in range(4):
        for f in range(2):
            out[d].append(draw_frame(d, f))
    return out


def build_tile_cache() -> dict[str, pygame.Surface]:
    cache: dict[str, pygame.Surface] = {}
    cache["grass"] = make_grass(1)
    cache["path"] = make_path(2)
    cache["water_0"] = make_water(0, 3)
    cache["water_1"] = make_water(1, 3)
    cache["bridge"] = make_bridge()
    cache["plaza"] = make_plaza()
    cache["plaza_c"] = make_plaza_center()
    cache["tree"] = make_tree(False, 10)
    cache["tree_cherry"] = make_tree(True, 11)
    cache["bush"] = make_bush(5)
    cache["fence"] = make_fence()
    cache["house_r"] = make_house((178, 72, 72), (218, 198, 168))
    cache["house_b"] = make_house((78, 102, 188), (210, 205, 188))
    cache["house_p"] = make_house((130, 78, 168), (198, 182, 208))
    cache["clinic"] = make_clinic()
    cache["fountain"] = make_fountain()
    cache["garden"] = make_garden()
    cache["lamp"] = make_lamp()
    cache["bench"] = make_bench()
    return cache
