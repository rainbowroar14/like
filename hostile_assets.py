"""Load OpenGameArt enemy and bullet sheets (colorkey black where needed)."""
from __future__ import annotations

import os
import zipfile

import pygame

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")


def _ck(s: pygame.Surface) -> pygame.Surface:
    s = s.convert()
    s.set_colorkey((0, 0, 0))
    return s


def _load(path: str) -> pygame.Surface:
    return pygame.image.load(path).convert_alpha()


def ensure_spiders_extracted() -> str:
    out = os.path.join(_ASSETS, "spider_packed", "LPC_Spiders")
    marker = os.path.join(out, "spider01.png")
    if os.path.isfile(marker):
        return out
    zpath = os.path.join(_ASSETS, "LPC_Spiders.zip")
    if not os.path.isfile(zpath):
        raise FileNotFoundError("Missing assets/LPC_Spiders.zip")
    with zipfile.ZipFile(zpath, "r") as z:
        z.extractall(os.path.join(_ASSETS, "spider_packed"))
    return out


def load_bat_frames() -> list[pygame.Surface]:
    path = os.path.join(_ASSETS, "bat-sprite.png")
    sheet = _load(path)
    w, h = sheet.get_size()
    if w % 32 or h % 32:
        return [_ck(sheet)]
    frames: list[pygame.Surface] = []
    # Second row, columns 1–3: front-facing flap cycle
    for c in (1, 2, 3):
        fr = sheet.subsurface(pygame.Rect(c * 32, 32, 32, 32)).copy()
        frames.append(_ck(fr))
    return frames


def _strip_cell_black_fill(surf: pygame.Surface, rgb_max: int = 32) -> pygame.Surface:
    """goblinsword cells use opaque black as padding — make it transparent."""
    s = surf.copy().convert_alpha()
    w, h = s.get_size()
    for yy in range(h):
        for xx in range(w):
            c = s.get_at((xx, yy))
            if c.a == 0:
                continue
            if c.r <= rgb_max and c.g <= rgb_max and c.b <= rgb_max:
                s.set_at((xx, yy), (0, 0, 0, 0))
    return s


def _load_goblinsword_row(row: int, ncols: int = 9) -> list[pygame.Surface]:
    path = os.path.join(_ASSETS, "goblinsword.png")
    sheet = pygame.image.load(path).convert_alpha()
    cell = 64
    frames: list[pygame.Surface] = []
    for col in range(min(ncols, sheet.get_width() // cell)):
        if (row + 1) * cell > sheet.get_height():
            break
        fr = sheet.subsurface(pygame.Rect(col * cell, row * cell, cell, cell)).copy()
        frames.append(_strip_cell_black_fill(fr.convert_alpha()))
    return frames or [sheet]


def load_imp_alive_frames() -> list[pygame.Surface]:
    """Walking imp — LPC goblin+sword row 2."""
    return _load_goblinsword_row(2, 9)


def load_imp_idle_frames() -> list[pygame.Surface]:
    """Sword-up idle — first cell of row 0 (static while frozen or not walking)."""
    row0 = _load_goblinsword_row(0, 9)
    return [row0[0]] if row0 else row0


def load_imp_down_frames() -> list[pygame.Surface]:
    """Knocked-down pose — different row so it reads as a second state."""
    return _load_goblinsword_row(4, 3)


def load_critter_frames() -> list[pygame.Surface]:
    path = os.path.join(_ASSETS, "rpgcritters.png")
    sheet = pygame.image.load(path).convert_alpha()
    # 16×16 grid, small slime-ish tile
    frames: list[pygame.Surface] = []
    for i in range(3):
        fr = sheet.subsurface(pygame.Rect(48 + i * 16, 64, 16, 16)).copy()
        frames.append(pygame.transform.scale(fr.convert_alpha(), (32, 32)))
    return frames or [sheet]


def load_scifi_frames() -> list[pygame.Surface]:
    path = os.path.join(_ASSETS, "scifi-creatures.png")
    sheet = pygame.image.load(path)
    frames: list[pygame.Surface] = []
    for r in (4, 5, 6):
        fr = sheet.subsurface(pygame.Rect(32, r * 32, 32, 32)).copy()
        frames.append(_ck(fr))
    return frames or [_ck(sheet)]


def load_spider_walk() -> list[pygame.Surface]:
    root = ensure_spiders_extracted()
    path = os.path.join(root, "spider03.png")
    sheet = pygame.image.load(path)
    cw, ch = 64, 64
    cols = sheet.get_width() // cw
    row = 2
    frames: list[pygame.Surface] = []
    for c in range(min(6, cols)):
        fr = sheet.subsurface(pygame.Rect(c * cw, row * ch, cw, ch)).copy()
        # LPC cells use solid black padding; same as bats — colorkey, not raw alpha
        frames.append(_ck(fr))
    return frames or [_ck(sheet)]


def load_bullet_default() -> pygame.Surface:
    s = pygame.Surface((8, 8), pygame.SRCALPHA)
    pygame.draw.circle(s, (255, 230, 120), (4, 4), 4)
    return s


def load_bullet_laser() -> pygame.Surface:
    path = os.path.join(_ASSETS, "M484BulletCollection1.png")
    sheet = pygame.image.load(path).convert_alpha()
    # Small cyan beam from Master484’s collection (approx crop; tune if needed)
    fr = sheet.subsurface(pygame.Rect(12, 44, 28, 10)).copy()
    return fr.convert_alpha()


def load_hit_yellow_frames(out_size: int = 96) -> list[pygame.Surface]:
    """Sinestesia — Hit Animation 2 (4×4 grid on 4096² sheet). CC0."""
    path = os.path.join(_ASSETS, "Hit-Yellow.png")
    if not os.path.isfile(path):
        return []
    sheet = pygame.image.load(path).convert_alpha()
    sw, sh = sheet.get_size()
    cols, rows = 4, 4
    cw, ch = sw // cols, sh // rows
    frames: list[pygame.Surface] = []
    for r in range(rows):
        for c in range(cols):
            fr = sheet.subsurface(pygame.Rect(c * cw, r * ch, cw, ch)).copy().convert_alpha()
            frames.append(pygame.transform.smoothscale(fr, (out_size, out_size)))
    return frames


def _pil_rgba_to_pygame(pil_img, out_max: int) -> pygame.Surface:
    from PIL import Image

    pil_img = pil_img.convert("RGBA")
    w, h = pil_img.size
    m = max(w, h)
    if m > out_max and m > 0:
        s = out_max / float(m)
        pil_img = pil_img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.Resampling.LANCZOS)
    raw = pil_img.tobytes()
    surf = pygame.image.frombuffer(raw, pil_img.size, "RGBA")
    return surf.convert_alpha()


def _pixel_layer_useful(layer, min_area: int = 220, min_long: int = 14) -> bool:
    from psd_tools.api.layers import PixelLayer

    if not isinstance(layer, PixelLayer):
        return False
    w, h = layer.width, layer.height
    if w < 4 or h < 4:
        return False
    if w * h < min_area and max(w, h) < min_long:
        return False
    n = layer.name.lower()
    if "layer 5" in n or n.startswith("layer 4"):
        return False
    if n in ("color a ", "color b", "layer 0 copy"):
        return False
    return True


def load_pixel_fxs_clips(out_max: int = 96) -> list[list[pygame.Surface]]:
    """zonked — Pixel Animated vFXs (PSD layer groups). CC0."""
    try:
        from psd_tools import PSDImage
        from psd_tools.api.layers import Group, PixelLayer
    except ImportError:
        return []
    path = os.path.join(_ASSETS, "pixel-fxs.psd")
    if not os.path.isfile(path):
        return []

    def walk_frames(container: Group) -> list[pygame.Surface]:
        from psd_tools.api.layers import Group as G, PixelLayer as PL

        frames: list[pygame.Surface] = []
        for c in container:
            if isinstance(c, G):
                frames.extend(walk_frames(c))
            elif isinstance(c, PL) and _pixel_layer_useful(c):
                try:
                    pil = c.topil()
                except Exception:
                    continue
                if pil is None or not pil.getbbox():
                    continue
                try:
                    frames.append(_pil_rgba_to_pygame(pil, out_max))
                except Exception:
                    continue
        return frames

    clips: list[list[pygame.Surface]] = []
    try:
        psd = PSDImage.open(path)
    except Exception:
        return []
    for layer in psd:
        if not isinstance(layer, Group):
            continue
        lname = layer.name.lower()
        if not (lname.endswith("fx") or lname in ("blood", "block")):
            continue
        seq = walk_frames(layer)
        if len(seq) >= 2:
            clips.append(seq)
    return clips


def build_hit_vfx_sets(out_max: int = 96) -> list[list[pygame.Surface]]:
    """Ordered: zonked PSD clips first, then Sinestesia Hit-Yellow strip."""
    sets = load_pixel_fxs_clips(out_max)
    hy = load_hit_yellow_frames(out_max)
    if hy:
        sets.append(hy)
    return sets


class HostileArt:
    def __init__(self) -> None:
        self.bat = load_bat_frames()
        self.imp_alive = load_imp_alive_frames()
        self.imp_idle = load_imp_idle_frames()
        self.imp_down = load_imp_down_frames()
        self.critter = load_critter_frames()
        self.scifi = load_scifi_frames()
        self.spider = load_spider_walk()
        self.bullet_normal = load_bullet_default()
        self.bullet_laser = load_bullet_laser()
        self.hit_vfx_sets = build_hit_vfx_sets()
        # Legacy single list for max length / empty guard
        self.hit_vfx_frames = self.hit_vfx_sets[0] if self.hit_vfx_sets else []

    def enemy_frames(
        self,
        kind: str,
        imp_down: bool = False,
        imp_moving: bool = False,
    ) -> list[pygame.Surface]:
        if kind in ("bat", "goblin"):
            return self.bat
        if kind == "imp":
            if imp_down:
                return self.imp_down
            return self.imp_alive if imp_moving else self.imp_idle
        if kind == "boss":
            if imp_down:
                return self.imp_down
            return self.imp_alive
        if kind == "critter":
            return self.critter
        if kind == "scifi":
            return self.scifi
        if kind == "spider":
            return self.spider
        return self.bat