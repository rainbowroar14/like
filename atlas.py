"""
Load CC0 Puny World 16×16 tiles and scale to game TILE size.
Grass picks a different source tile per map cell (hash of x,y).
"""
from __future__ import annotations

import os
import pygame

SUB = 16

_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
_SHEET = os.path.join(_ASSET_DIR, "punyworld-overworld-tileset.png")

# Sheet sprites use transparency for unused pixels — composite onto a solid color before scaling.
_BG_GRASS = (72, 138, 64)
_BG_STONE = (118, 120, 126)
_BG_WATER = (48, 108, 168)
_BG_DIRT = (150, 118, 78)


def _scale(src: pygame.Surface, out: int) -> pygame.Surface:
    if src.get_width() == out and src.get_height() == out:
        return src
    return pygame.transform.scale(src, (out, out))


def _scale_backed(src: pygame.Surface, out: int, bg: tuple[int, int, int]) -> pygame.Surface:
    w, h = src.get_width(), src.get_height()
    base = pygame.Surface((w, h))
    base.fill(bg)
    base.blit(src, (0, 0))
    return pygame.transform.scale(base, (out, out))


def _scan_pools(sheet: pygame.Surface) -> tuple[list[tuple[int, int]], list[tuple[int, int]], list[tuple[int, int]]]:
    """Return (grass_tiles, dirt_tiles, water_tiles) as 16px grid indices."""
    grass: list[tuple[int, int]] = []
    dirt: list[tuple[int, int]] = []
    water: list[tuple[int, int]] = []
    w, h = sheet.get_size()
    cols, rows = w // SUB, h // SUB
    for j in range(rows):
        for i in range(cols):
            c = sheet.get_at((i * SUB + SUB // 2, j * SUB + SUB // 2))
            lum = (c.r + c.g + c.b) // 3
            if c.a < 128:
                continue
            if c.b > c.g + 16 and lum < 210:
                water.append((i, j))
            elif j >= 11 and j <= 17 and c.g > 82 and c.g >= c.r - 10 and c.b < c.g + 22:
                grass.append((i, j))
            elif j <= 6 and c.r > 110 and c.g > 80 and lum < 190 and not (c.g > c.r + 15):
                # Brown path dirt (skip teal grass and semi-transparent cliff edges)
                if c.r > c.g - 5 and c.b < c.r - 5:
                    dirt.append((i, j))
    if len(grass) < 8:
        grass = [(i, 14) for i in range(27)]
    if len(dirt) < 4:
        dirt = [(10, 1), (11, 1), (12, 1), (13, 1)]
    if len(water) < 4:
        water = [(3, 10), (9, 10), (23, 10), (24, 10)]
    return grass, dirt, water


class TileAtlas:
    def __init__(self, tile_px: int, sheet_path: str = _SHEET) -> None:
        self.tile_px = tile_px
        # convert_alpha needs a display surface on some platforms; raw load is fine for subsurface/scale
        self.sheet = pygame.image.load(sheet_path)
        self.grass_pool, self.dirt_pool, self.water_pool = _scan_pools(self.sheet)
        self._static: dict[str, pygame.Surface] = {}
        self._build_static()

    def _grab(self, ix: int, iy: int, iw: int = 1, ih: int = 1) -> pygame.Surface:
        r = pygame.Rect(ix * SUB, iy * SUB, iw * SUB, ih * SUB)
        return self.sheet.subsurface(r).copy()

    def _put(
        self,
        key: str,
        ix: int,
        iy: int,
        iw: int = 1,
        ih: int = 1,
        *,
        bg: tuple[int, int, int] = _BG_GRASS,
    ) -> None:
        raw = self._grab(ix, iy, iw, ih)
        self._static[key] = _scale_backed(raw, self.tile_px, bg)

    def _build_static(self) -> None:
        # Water animation frames
        for idx, name in enumerate(("water_0", "water_1", "water_2")):
            t = self.water_pool[idx % len(self.water_pool)]
            self._put(name, t[0], t[1], 1, 1, bg=_BG_WATER)
        # Wood bridge (planks) — water under gaps
        self._put("bridge", 4, 26, 2, 2, bg=_BG_WATER)
        # Town square: use opaque tan cobble (old 10,3 was mostly transparent cliff art)
        self._put("plaza", 10, 0, 2, 2, bg=_BG_STONE)
        self._put("plaza_c", 10, 32, 2, 2, bg=_BG_STONE)
        # Trees (2×2 foliage clumps)
        self._put("tree", 0, 7, 2, 2)
        self._put("tree_cherry", 6, 7, 2, 2)
        self._put("bush", 14, 15, 1, 1)
        self._put("fence", 8, 4, 1, 1)
        self._put("house_r", 14, 33, 2, 2)
        self._put("house_b", 4, 32, 2, 2)
        self._put("house_p", 8, 34, 2, 2)
        # 3×3 clinic slice was ~60% transparent; use a dense 2×2 civic chunk instead
        self._put("clinic", 5, 33, 2, 2)
        self._put("fountain", 1, 12, 2, 2, bg=_BG_DIRT)
        self._put("garden", 9, 1, 2, 2, bg=_BG_GRASS)
        self._put("bench", 6, 26, 2, 1)
        self._put("lamp", 10, 26, 1, 2)

    def grass_at(self, mx: int, my: int) -> pygame.Surface:
        n = len(self.grass_pool)
        idx = (mx * 73 + my * 37 + (mx * my % 5)) % n
        i, j = self.grass_pool[idx]
        raw = self._grab(i, j, 1, 1)
        return _scale_backed(raw, self.tile_px, _BG_GRASS)

    def dirt_at(self, mx: int, my: int) -> pygame.Surface:
        n = len(self.dirt_pool)
        idx = (mx * 41 + my * 19) % n
        i, j = self.dirt_pool[idx]
        raw = self._grab(i, j, 1, 1)
        return _scale_backed(raw, self.tile_px, _BG_DIRT)

    def get(self, name: str) -> pygame.Surface:
        return self._static[name]

    def build_cache_dict(self) -> dict[str, pygame.Surface]:
        """Same keys as procedural cache for objects + water; grass/path handled in main."""
        out = dict(self._static)
        return out


def try_load_atlas(tile_px: int) -> TileAtlas | None:
    if not os.path.isfile(_SHEET):
        return None
    return TileAtlas(tile_px, _SHEET)
