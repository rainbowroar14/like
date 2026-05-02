"""Michele 'Buch' Bucelli — Outdoor tiles (16×16). https://opengameart.org/content/outdoor-tiles-again — CC-BY 3.0

Terrain pools only use homogeneous cells. We also filter by mean brightness so near-black
water / near-white junk tiles do not read as void squares, and we composite onto a solid
base so accidental transparency does not punch holes.
"""
from __future__ import annotations

import os

import pygame

SUB = 16
SHEET_PATH = os.path.join(os.path.dirname(__file__), "assets", "buch-outdoor-sheet.png")

_BG_GRASS = (66, 118, 62)
_BG_DIRT = (118, 72, 58)
_BG_WATER = (52, 108, 158)

# Full-dirt maps: clear color behind scaled path tiles
DIRT_FILL = _BG_DIRT

# Bigger number = larger uniform patches (less checkerboard noise at tile seams).
GRASS_CLUMP = 8
DIRT_CLUMP = 1  # dirt arena: varied / pseudo-random per tile (no big muddy clumps)
WATER_CLUMP = 5


def _mean_lum(sheet: pygame.Surface, i: int, j: int) -> float:
    s = 0
    for yy in range(SUB):
        for xx in range(SUB):
            c = sheet.get_at((i * SUB + xx, j * SUB + yy))
            s += (c.r + c.g + c.b) // 3
    return s / float(SUB * SUB)


def _homog(sheet: pygame.Surface, i: int, j: int, pred) -> float:
    ok = 0
    for yy in range(SUB):
        for xx in range(SUB):
            if pred(sheet.get_at((i * SUB + xx, j * SUB + yy))):
                ok += 1
    return ok / float(SUB * SUB)


def _grass_pred(c: pygame.Color) -> bool:
    return c.g > 95 and c.g >= c.r - 15 and c.b < c.g + 25 and (c.r + c.g + c.b) > 120


def _water_pred(c: pygame.Color) -> bool:
    lum = (c.r + c.g + c.b) // 3
    return c.b > c.g + 12 and lum < 210


def _path_pred(c: pygame.Color) -> bool:
    return (
        c.r > 70
        and c.g < 100
        and c.b < 100
        and (c.r + c.g + c.b) < 290
        and not (c.b > c.g + 8 and c.b > c.r - 20)
    )


def _tile_waterish_fraction(sheet: pygame.Surface, i: int, j: int) -> float:
    """How much of the cell reads as blue / water (exclude from dirt pool)."""
    return _homog(sheet, i, j, _water_pred)


def _scrub_dirt_pool(sheet: pygame.Surface, dirt: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Drop path tiles that still contain noticeable water pixels (fixes blue patches on dirt maps)."""
    cleaned: list[tuple[int, int]] = []
    for ij in dirt:
        i, j = ij
        if _tile_waterish_fraction(sheet, i, j) > 0.045:
            continue
        ml = _mean_lum(sheet, i, j)
        # Reject unusually cool / bright cells that skew blue
        corner = sheet.get_at((i * SUB + SUB // 2, j * SUB + SUB // 2))
        if corner.b > corner.r + 25 and corner.b > corner.g + 10:
            continue
        if ml > 198 and corner.b > corner.g:
            continue
        cleaned.append(ij)
    if len(cleaned) >= 4:
        return cleaned
    # Looser cutoff if the sheet yields few “clean” path cells
    loose = [ij for ij in dirt if _tile_waterish_fraction(sheet, ij[0], ij[1]) < 0.12]
    return loose if len(loose) >= 4 else dirt


def _pools(sheet: pygame.Surface) -> tuple[list[tuple[int, int]], list[tuple[int, int]], list[tuple[int, int]]]:
    w, h = sheet.get_size()
    cols, rows = w // SUB, h // SUB
    grass: list[tuple[int, int]] = []
    water: list[tuple[int, int]] = []
    dirt: list[tuple[int, int]] = []

    for j in range(rows):
        for i in range(cols):
            hg = _homog(sheet, i, j, _grass_pred)
            hw = _homog(sheet, i, j, _water_pred)
            hp = _homog(sheet, i, j, _path_pred)
            ml = _mean_lum(sheet, i, j)

            if hg >= 0.88 and hw < 0.10 and 52 <= ml <= 215:
                grass.append((i, j))
            elif hw >= 0.88 and 62 <= ml <= 185:
                water.append((i, j))
            elif hp >= 0.82 and hw < 0.18 and hg < 0.35 and 48 <= ml <= 200:
                dirt.append((i, j))

    dirt = _scrub_dirt_pool(sheet, dirt)

    if len(grass) < 6:
        grass = [(6, 6), (6, 7), (6, 8), (6, 9), (6, 10), (6, 11)]
    if len(water) < 4:
        water = [(10, 7), (11, 7), (10, 8), (11, 8), (20, 1), (21, 1)]
    if len(dirt) < 4:
        # path-only (avoid indices that are water on this sheet)
        dirt = [(3, 1), (4, 1), (3, 2), (4, 2), (7, 0), (12, 0)]

    return grass, dirt, water


def _scale_backed(src: pygame.Surface, tile_px: int, bg: tuple[int, int, int]) -> pygame.Surface:
    base = pygame.Surface((SUB, SUB))
    base.fill(bg)
    base.blit(src, (0, 0))
    return pygame.transform.scale(base, (tile_px, tile_px))


def _clump_index(mx: int, my: int, clump: int, pool_len: int, salt: int) -> int:
    cx, cy = mx // max(1, clump), my // max(1, clump)
    # Mix bits so clumps look organic, not stripes
    h = (cx * 374761393 + cy * 668265263 + salt * 1442695041) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h ^= h >> 16
    return h % pool_len


def _dirt_tile_index(mx: int, my: int, pool_len: int, salt: int) -> int:
    """High-frequency noise: different tile per map cell, still deterministic."""
    h = (mx * 195225786 + my * 86094599 + salt * 977505629) & 0xFFFFFFFF
    h ^= h >> 13
    h *= 2246822519 & 0xFFFFFFFF
    h ^= h >> 16
    return h % pool_len


class BuchTiles:
    def __init__(self, tile_px: int, path: str = SHEET_PATH) -> None:
        self.tile_px = tile_px
        self.sheet = pygame.image.load(path)
        self.grass_pool, self.dirt_pool, self.water_pool = _pools(self.sheet)

    def _cell(self, i: int, j: int) -> pygame.Surface:
        return self.sheet.subsurface(pygame.Rect(i * SUB, j * SUB, SUB, SUB)).copy()

    def grass_at(self, mx: int, my: int) -> pygame.Surface:
        n = len(self.grass_pool)
        idx = _clump_index(mx, my, GRASS_CLUMP, n, salt=1)
        i, j = self.grass_pool[idx]
        return _scale_backed(self._cell(i, j), self.tile_px, _BG_GRASS)

    def dirt_at(self, mx: int, my: int, variant: int = 0) -> pygame.Surface:
        """variant shifts the noise seed so map letters a–d still get distinct mixes."""
        n = len(self.dirt_pool)
        salt = 11 + (variant % 8) * 47
        idx = _dirt_tile_index(mx, my, n, salt=salt)
        i, j = self.dirt_pool[idx]
        return _scale_backed(self._cell(i, j), self.tile_px, _BG_DIRT)

    def water_at(self, mx: int, my: int, tick: int) -> pygame.Surface:
        n = len(self.water_pool)
        cx, cy = mx // WATER_CLUMP, my // WATER_CLUMP
        h = (cx * 2246822519 + cy * 3266489917 + (tick // 6) * 1442695041) & 0xFFFFFFFF
        h ^= h >> 13
        idx = h % n
        i, j = self.water_pool[idx]
        return _scale_backed(self._cell(i, j), self.tile_px, _BG_WATER)
