"""Music-stand pedestals + procedural 64×64 loot icons (shaded pixel style)."""
from __future__ import annotations

import colorsys
import math
import os
import secrets
from collections.abc import Callable
from dataclasses import dataclass

import pygame

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")
ICON = 64

# Rarity weights (must sum to 100): common 40, rare 30, epic 20, legendary 9, mythical 1.
COMMON_POOL: list[str] = [
    "lion_shield",
    "green_shield",
    "tread_plating",
    "reinforced_hull",
    "machined_barrel",
    "neural_magnet",
    "contact_lens",
    "iron_skin",
]
RARE_POOL: list[str] = [
    "lava_sword",
    "overclock_chip",
    "glass_cannon",
    "chocolate_milk",
    "battery_cell",
    "spoon_bender",
    "big_brain",
]
EPIC_POOL: list[str] = [
    "twenty_twenty",
    "thump_rounds",
    "the_wiz",
    "soy_milk",
    "rubber_cement",
    "brimstone",
    "mutant_spider",
    "thy_nuke",
]
LEGENDARY_POOL: list[str] = [
    "skeleton_staff",
    "sacred_heart",
    "gambling",
    "technology_zero",
    "polyphemus",
    "hive_mind",
]
MYTHICAL_POOL: list[str] = [
    "growth",
]

PEDESTAL_ITEM_IDS: list[str] = (
    COMMON_POOL + RARE_POOL + EPIC_POOL + LEGENDARY_POOL + MYTHICAL_POOL
)  # grid order: common → rare → epic → legendary → mythical

ITEM_RARITY: dict[str, str] = {}
for _p in COMMON_POOL:
    ITEM_RARITY[_p] = "common"
for _p in RARE_POOL:
    ITEM_RARITY[_p] = "rare"
for _p in EPIC_POOL:
    ITEM_RARITY[_p] = "epic"
for _p in LEGENDARY_POOL:
    ITEM_RARITY[_p] = "legendary"
for _p in MYTHICAL_POOL:
    ITEM_RARITY[_p] = "mythical"

RARITY_BORDER_RGB: dict[str, tuple[int, int, int]] = {
    "common": (120, 130, 145),
    "rare": (70, 130, 235),
    "epic": (175, 85, 220),
    "legendary": (235, 175, 55),
    "mythical": (255, 105, 180),
}

# Soft halo drawn behind item icons (world + spawn menu).
RARITY_GLOW_RGB: dict[str, tuple[int, int, int]] = {
    "common": (255, 255, 255),
    "rare": (96, 168, 255),
    "epic": (188, 96, 255),
    "legendary": (255, 224, 96),
    "mythical": (255, 160, 220),
}


def mythical_rgb(anim_t: float, salt: float = 0.0) -> tuple[int, int, int]:
    h = (anim_t * 0.38 + salt) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.72, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def rarity_border_rgb(item_id: str, anim_t: float = 0.0) -> tuple[int, int, int]:
    tier = ITEM_RARITY.get(item_id, "common")
    if tier == "mythical":
        return mythical_rgb(anim_t, 0.0)
    return RARITY_BORDER_RGB.get(tier, (130, 140, 175))


def draw_mythical_rainbow_rect(
    target: pygame.Surface, rect: pygame.Rect, anim_t: float, width: int = 2
) -> None:
    """Animated rainbow outline (mythical tier)."""
    x0, y0, x1, y1 = rect.left, rect.top, rect.right - 1, rect.bottom - 1
    segs = (
        ((x0, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    )
    for si, ((ax, ay), (bx, by)) in enumerate(segs):
        n = 10
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            sx = int(ax + (bx - ax) * t0)
            sy = int(ay + (by - ay) * t0)
            ex = int(ax + (bx - ax) * t1)
            ey = int(ay + (by - ay) * t1)
            col = mythical_rgb(anim_t, (si * 0.17 + i * 0.03 + t0 * 0.1) % 1.0)
            pygame.draw.line(target, col, (sx, sy), (ex, ey), width)


def draw_rarity_glow(
    target: pygame.Surface,
    icon_x: int,
    icon_y: int,
    iw: int,
    ih: int,
    item_id: str,
    anim_t: float = 0.0,
) -> None:
    """Draw a multi-layer bloom behind a loot icon; call before blitting the icon."""
    tier = ITEM_RARITY.get(item_id, "common")
    cx = icon_x + iw // 2
    cy = icon_y + ih // 2
    half = max(iw, ih) // 2
    layers: tuple[tuple[int, int], ...] = (
        (half + 22, 24),
        (half + 14, 38),
        (half + 6, 52),
        (half, 64),
    )
    for li, (rad, alpha) in enumerate(layers):
        if rad < 4:
            continue
        if tier == "mythical":
            rgb = mythical_rgb(anim_t, li * 0.11)
        else:
            rgb = RARITY_GLOW_RGB.get(tier, (255, 255, 255))
        surf = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*rgb, alpha), (rad + 1, rad + 1), rad)
        target.blit(surf, (cx - rad - 1, cy - rad - 1))


def roll_pedestal_item_id(exclude: str | None = None) -> str:
    r = secrets.randbelow(100)
    if r < 40:
        pool = list(COMMON_POOL)
    elif r < 70:
        pool = list(RARE_POOL)
    elif r < 90:
        pool = list(EPIC_POOL)
    elif r < 99:
        pool = list(LEGENDARY_POOL)
    else:
        pool = list(MYTHICAL_POOL)
    if exclude is not None:
        pool = [p for p in pool if p != exclude]
    if not pool:
        pool = [p for p in PEDESTAL_ITEM_IDS if p != exclude]
    if not pool:
        pool = list(PEDESTAL_ITEM_IDS)
    return secrets.choice(pool)


def _icon_lion_shield() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    # heater shield body
    pts = [(32, 6), (50, 14), (54, 38), (32, 58), (10, 38), (14, 14)]
    pygame.draw.polygon(s, (92, 28, 32), pts)
    pygame.draw.polygon(s, (140, 52, 48), [(32, 10), (46, 16), (50, 36), (32, 52), (14, 36), (18, 16)])
    pygame.draw.polygon(s, (178, 142, 58), [(32, 14), (42, 20), (44, 34), (32, 46), (20, 34), (22, 20)])
    pygame.draw.lines(s, (210, 175, 90), False, [(32, 18), (32, 42)], 2)
    pygame.draw.circle(s, (200, 40, 55), (32, 30), 7)
    pygame.draw.circle(s, (255, 120, 130), (30, 28), 3)
    pygame.draw.arc(s, (40, 20, 22), (18, 16, 28, 30), 0.3, 2.8, 2)
    return s


def _icon_green_shield() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pts = [(32, 8), (48, 16), (52, 36), (32, 56), (12, 36), (16, 16)]
    pygame.draw.polygon(s, (28, 92, 58), pts)
    pygame.draw.polygon(s, (48, 140, 88), [(32, 12), (44, 18), (48, 34), (32, 50), (16, 34), (20, 18)])
    pygame.draw.polygon(s, (22, 72, 48), [(32, 18), (40, 24), (42, 32), (32, 44), (22, 32), (24, 24)])
    pygame.draw.lines(s, (190, 205, 210), False, [(24, 22), (40, 22), (40, 38), (24, 38)], 2)
    pygame.draw.circle(s, (255, 255, 255, 90), (26, 24), 4)
    return s


def _icon_lava_sword() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    # hilt
    pygame.draw.rect(s, (38, 32, 28), (26, 40, 12, 18), border_radius=2)
    pygame.draw.rect(s, (62, 52, 44), (28, 42, 8, 6))
    # blade (warm gradient bands)
    blade = [(32, 8), (38, 10), (40, 38), (32, 42), (24, 38), (26, 10)]
    pygame.draw.polygon(s, (255, 92, 28), blade)
    pygame.draw.polygon(s, (255, 200, 60), [(32, 12), (36, 14), (37, 32), (32, 36), (27, 32), (28, 14)])
    pygame.draw.line(s, (255, 255, 220), (32, 12), (32, 34), 2)
    pygame.draw.polygon(s, (180, 40, 12), [(32, 8), (34, 12), (32, 16), (30, 12)])
    # ember sparks
    for ox, oy in ((18, 18), (46, 22), (14, 34)):
        pygame.draw.circle(s, (255, 220, 80, 200), (ox, oy), 2)
    return s


def _icon_skeleton_staff() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    # shaft
    pygame.draw.rect(s, (58, 48, 42), (29, 22, 6, 38))
    pygame.draw.line(s, (88, 76, 64), (30, 24), (30, 56), 1)
    pygame.draw.line(s, (72, 62, 55), (34, 30), (34, 54), 1)
    # skull knob
    pygame.draw.circle(s, (220, 210, 198), (32, 16), 11)
    pygame.draw.circle(s, (180, 168, 155), (32, 17), 9)
    pygame.draw.circle(s, (40, 38, 38), (28, 14), 2)
    pygame.draw.circle(s, (40, 38, 38), (36, 14), 2)
    pygame.draw.arc(s, (60, 52, 52), (26, 18, 12, 10), 3.3, 6.1, 1)
    pygame.draw.rect(s, (140, 130, 118), (27, 20, 10, 4))
    return s


def _icon_twenty_twenty() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    # thick frames — Isaac-style specs, 64×64 detail
    frame = (28, 28, 28, 255)
    hi = (55, 55, 62, 255)
    lens_fill = (120, 175, 225, 235)
    lens_hi = (220, 235, 255, 200)
    # left lens rim
    pygame.draw.ellipse(s, frame, (6, 22, 26, 28), 0)
    pygame.draw.ellipse(s, hi, (8, 24, 22, 24), 3)
    pygame.draw.ellipse(s, lens_fill, (11, 27, 16, 18))
    pygame.draw.arc(s, lens_hi[:3], (12, 28, 14, 16), 1.1, 2.5, 2)
    # right lens
    pygame.draw.ellipse(s, frame, (32, 22, 26, 28), 0)
    pygame.draw.ellipse(s, hi, (34, 24, 22, 24), 3)
    pygame.draw.ellipse(s, lens_fill, (37, 27, 16, 18))
    pygame.draw.arc(s, lens_hi[:3], (38, 28, 14, 16), 1.0, 2.4, 2)
    # bridge
    pygame.draw.rect(s, frame, (28, 32, 8, 6), border_radius=1)
    pygame.draw.line(s, hi[:3], (30, 34), (34, 34), 1)
    # temples
    pygame.draw.rect(s, frame, (2, 34, 8, 5), border_radius=1)
    pygame.draw.rect(s, frame, (54, 34, 8, 5), border_radius=1)
    # nose pad hints
    pygame.draw.line(s, (70, 70, 78), (30, 38), (28, 42), 1)
    pygame.draw.line(s, (70, 70, 78), (34, 38), (36, 42), 1)
    return s


def _icon_sacred_heart() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    # golden halo
    for i, alp in enumerate((40, 70, 110, 150)):
        pygame.draw.arc(
            s,
            (255, 215, 120, alp),
            (8 - i, 2 - i, 48 + i * 2, 28 + i * 2),
            0.15,
            math.pi - 0.15,
            2,
        )
    # heart body (two lobes + point)
    pygame.draw.circle(s, (168, 28, 48), (24, 30), 12)
    pygame.draw.circle(s, (168, 28, 48), (40, 30), 12)
    pygame.draw.polygon(s, (148, 22, 42), [(32, 38), (14, 28), (50, 28)])
    pygame.draw.polygon(s, (210, 55, 72), [(32, 42), (20, 32), (44, 32)])
    pygame.draw.line(s, (90, 20, 38), (32, 36), (32, 50), 2)
    # specular
    pygame.draw.ellipse(s, (255, 200, 210, 220), (20, 26, 10, 8))
    # center gem (Isaac-style)
    pygame.draw.polygon(s, (240, 248, 255), [(32, 34), (36, 40), (32, 46), (28, 40)])
    pygame.draw.polygon(s, (200, 220, 255), [(32, 36), (34, 40), (32, 44), (30, 40)])
    return s


def _icon_tread_plating() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (44, 48, 52), (8, 18, 48, 32), border_radius=4)
    for i in range(4):
        x0 = 12 + i * 12
        pygame.draw.rect(s, (70, 74, 80), (x0, 22, 8, 10), border_radius=1)
        pygame.draw.line(s, (110, 118, 128), (x0 + 1, 24), (x0 + 6, 24), 1)
        pygame.draw.line(s, (28, 30, 34), (x0 + 1, 30), (x0 + 6, 30), 1)
    pygame.draw.rect(s, (90, 95, 102), (10, 36, 44, 8), border_radius=2)
    pygame.draw.circle(s, (130, 135, 140), (16, 44), 2)
    pygame.draw.circle(s, (130, 135, 140), (48, 44), 2)
    return s


def _icon_overclock_chip() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (35, 40, 48), (14, 14, 36, 36), border_radius=3)
    pygame.draw.rect(s, (55, 62, 72), (18, 18, 28, 28), border_radius=2)
    # hex core glow
    hx = [(32, 16), (44, 22), (44, 34), (32, 40), (20, 34), (20, 22)]
    pygame.draw.polygon(s, (0, 200, 255, 60), hx)
    pygame.draw.polygon(s, (80, 240, 255, 220), [(32, 22), (38, 26), (38, 32), (32, 36), (26, 32), (26, 26)])
    pygame.draw.circle(s, (220, 250, 255), (32, 29), 5)
    pygame.draw.circle(s, (255, 255, 255), (30, 27), 2)
    # pins
    for px, py in ((32, 10), (50, 28), (32, 50), (14, 28)):
        pygame.draw.rect(s, (160, 165, 170), (px - 2, py - 2, 4, 4))
    return s


def _icon_thump_rounds() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    # fat cartridge
    pygame.draw.ellipse(s, (160, 130, 58), (18, 20, 28, 26))
    pygame.draw.ellipse(s, (200, 170, 90), (21, 23, 22, 20))
    pygame.draw.rect(s, (90, 82, 70), (24, 36, 16, 14), border_radius=2)
    pygame.draw.rect(s, (120, 110, 95), (26, 38, 12, 6))
    # copper tip
    pygame.draw.polygon(s, (185, 150, 70), [(32, 14), (40, 22), (24, 22)])
    pygame.draw.line(s, (240, 230, 200), (30, 18), (34, 20), 1)
    pygame.draw.line(s, (70, 60, 50), (22, 32), (42, 34), 1)
    return s


def _icon_the_wiz() -> pygame.Surface:
    """Conical hat nod to Isaac's The Wiz (wizard / dunce cone)."""
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.polygon(s, (108, 62, 178), [(32, 6), (54, 42), (10, 42)])
    pygame.draw.polygon(s, (150, 110, 220), [(32, 12), (48, 38), (16, 38)])
    pygame.draw.polygon(s, (230, 220, 250, 200), [(32, 16), (40, 32), (24, 32)])
    pygame.draw.rect(s, (55, 48, 68), (12, 40, 40, 12), border_radius=3)
    pygame.draw.rect(s, (85, 78, 105), (16, 43, 32, 6))
    pygame.draw.arc(s, (200, 200, 220), (20, 44, 24, 14), 0.2, 2.9, 2)
    return s


def _icon_gambling() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (32, 128, 78), (8, 12, 48, 48), border_radius=8)
    pygame.draw.rect(s, (22, 92, 58), (12, 16, 40, 40), border_radius=6)
    for ox, oy in ((20, 22), (32, 32), (44, 42)):
        pygame.draw.circle(s, (248, 248, 255), (ox, oy), 5)
    pygame.draw.rect(s, (190, 50, 52), (36, 6, 24, 24), border_radius=4)
    pygame.draw.rect(s, (240, 228, 210), (40, 10, 16, 16), border_radius=2)
    pygame.draw.circle(s, (40, 40, 48), (48, 18), 3)
    pygame.draw.circle(s, (40, 40, 48), (52, 26), 3)
    return s


def _icon_reinforced_hull() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (72, 78, 92), (10, 18, 44, 36), border_radius=4)
    for y in (22, 30, 38):
        pygame.draw.line(s, (130, 138, 155), (14, y), (50, y), 2)
    pygame.draw.rect(s, (95, 102, 118), (14, 22, 36, 28), width=2, border_radius=3)
    pygame.draw.polygon(s, (160, 170, 188), [(32, 10), (44, 20), (20, 20)])
    return s


def _icon_machined_barrel() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (88, 90, 98), (12, 20, 40, 28), border_radius=3)
    for y in (24, 30, 36):
        pygame.draw.line(s, (48, 50, 58), (16, y), (48, y), 2)
    pygame.draw.rect(s, (60, 62, 70), (8, 26, 10, 16), border_radius=2)
    pygame.draw.rect(s, (200, 200, 210), (44, 24, 14, 8), border_radius=2)
    return s


def _icon_glass_cannon() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.polygon(s, (180, 210, 235, 200), [(32, 8), (48, 36), (16, 36)])
    pygame.draw.polygon(s, (120, 175, 220, 160), [(32, 14), (42, 34), (22, 34)])
    pygame.draw.circle(s, (255, 90, 70, 220), (32, 28), 8)
    pygame.draw.rect(s, (55, 50, 62), (26, 36, 12, 18), border_radius=2)
    return s


def _icon_neural_magnet() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (200, 120, 200), (14, 16, 36, 40))
    pygame.draw.ellipse(s, (160, 80, 170), (18, 22, 28, 28))
    pygame.draw.line(s, (255, 230, 255), (8, 32), (22, 28), 2)
    pygame.draw.line(s, (255, 230, 255), (56, 32), (42, 28), 2)
    pygame.draw.circle(s, (255, 250, 255), (32, 36), 5)
    return s


def _icon_soy_milk() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (245, 248, 252), (14, 10, 36, 48), border_radius=6)
    pygame.draw.rect(s, (40, 120, 200), (18, 14, 28, 14), border_radius=3)
    pygame.draw.line(s, (180, 190, 205), (20, 32), (44, 32), 2)
    pygame.draw.line(s, (180, 190, 205), (20, 40), (44, 40), 2)
    pygame.draw.circle(s, (90, 160, 230), (32, 21), 5)
    return s


def _icon_rubber_cement() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (55, 55, 62), (10, 24, 44, 28), border_radius=4)
    pygame.draw.rect(s, (35, 35, 42), (14, 28, 36, 20), border_radius=2)
    for x in (18, 28, 38, 48):
        pygame.draw.circle(s, (90, 90, 98), (x, 38), 3)
    pygame.draw.arc(s, (240, 200, 80), (8, 8, 48, 36), 3.5, 5.8, 3)
    return s


def _icon_technology_zero() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.circle(s, (20, 60, 120), (20, 22), 8)
    pygame.draw.circle(s, (20, 60, 120), (44, 40), 8)
    pygame.draw.circle(s, (20, 60, 120), (26, 48), 8)
    pygame.draw.line(s, (120, 210, 255), (20, 22), (44, 40), 2)
    pygame.draw.line(s, (120, 210, 255), (44, 40), (26, 48), 2)
    pygame.draw.line(s, (180, 235, 255), (20, 22), (26, 48), 2)
    pygame.draw.circle(s, (200, 240, 255), (32, 36), 10, width=2)
    return s


def _icon_chocolate_milk() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (245, 248, 252), (14, 10, 36, 48), border_radius=6)
    pygame.draw.rect(s, (92, 52, 32), (18, 14, 28, 36), border_radius=4)
    pygame.draw.rect(s, (140, 85, 55), (22, 20, 20, 12), border_radius=2)
    pygame.draw.line(s, (255, 250, 240), (24, 36), (40, 44), 2)
    return s


def _icon_contact_lens() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.circle(s, (60, 70, 88), (32, 32), 22, width=4)
    pygame.draw.circle(s, (130, 185, 235), (32, 32), 16)
    pygame.draw.circle(s, (220, 240, 255), (28, 28), 5)
    pygame.draw.line(s, (255, 200, 120), (10, 32), (22, 32), 2)
    pygame.draw.line(s, (255, 200, 120), (42, 32), (54, 32), 2)
    return s


def _icon_iron_skin() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (88, 92, 102), (12, 14, 40, 40), border_radius=6)
    for i in range(5):
        pygame.draw.line(s, (130, 135, 145), (16, 18 + i * 8), (48, 18 + i * 8), 2)
    pygame.draw.rect(s, (55, 58, 65), (16, 18, 32, 32), width=2, border_radius=4)
    pygame.draw.polygon(s, (160, 165, 175), [(32, 8), (44, 16), (20, 16)])
    return s


def _icon_battery_cell() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (55, 58, 65), (18, 16, 28, 40), border_radius=4)
    pygame.draw.rect(s, (28, 120, 85), (22, 20, 20, 30), border_radius=2)
    pygame.draw.rect(s, (90, 95, 100), (26, 10, 12, 8), border_radius=2)
    pygame.draw.polygon(s, (255, 230, 80), [(32, 28), (38, 36), (32, 44), (26, 36)])
    return s


def _icon_spoon_bender() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.arc(s, (190, 195, 210), (8, 8, 48, 48), 0.9, 2.8, 6)
    pygame.draw.circle(s, (255, 240, 200), (44, 22), 8)
    pygame.draw.circle(s, (120, 200, 255, 180), (44, 22), 5)
    pygame.draw.line(s, (200, 200, 210), (18, 40), (40, 24), 3)
    return s


def _icon_brimstone() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (42, 38, 48), (10, 18, 44, 34), border_radius=4)
    pygame.draw.rect(s, (255, 55, 40), (14, 22, 36, 8), border_radius=2)
    pygame.draw.rect(s, (255, 140, 60), (18, 32, 28, 14), border_radius=2)
    pygame.draw.rect(s, (255, 230, 120), (20, 36, 24, 6), border_radius=1)
    return s


def _icon_mutant_spider() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (48, 42, 52), (20, 20, 24, 20))
    pygame.draw.circle(s, (38, 34, 48), (26, 28), 7)
    pygame.draw.circle(s, (38, 34, 48), (38, 28), 7)
    for i, (lx, ly) in enumerate(((12, 26), (8, 34), (52, 26), (56, 34))):
        pygame.draw.line(s, (35, 30, 40), (24 + (i % 2) * 8, 32), (lx, ly), 2)
    pygame.draw.circle(s, (255, 60, 60), (26, 28), 2)
    pygame.draw.circle(s, (255, 60, 60), (38, 28), 2)
    return s


def _icon_thy_nuke() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.circle(s, (55, 58, 62), (32, 30), 22)
    pygame.draw.circle(s, (255, 215, 60), (32, 30), 16, width=3)
    pygame.draw.circle(s, (255, 100, 40), (32, 30), 8)
    pygame.draw.polygon(s, (240, 240, 245), [(32, 6), (38, 18), (26, 18)])
    for a in (0, 0.9, 1.8, 2.7, 3.6):
        x = 32 + int(26 * math.cos(a - 1.57))
        y = 30 + int(26 * math.sin(a - 1.57))
        pygame.draw.line(s, (255, 240, 200), (32, 30), (x, y), 2)
    return s


def _icon_polyphemus() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.circle(s, (120, 75, 55), (32, 34), 20)
    pygame.draw.circle(s, (255, 240, 200), (32, 32), 8)
    pygame.draw.circle(s, (40, 30, 25), (32, 32), 4)
    pygame.draw.arc(s, (90, 55, 45), (18, 40, 28, 16), 0.1, 3.0, 3)
    return s


def _icon_hive_mind() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.polygon(s, (210, 175, 65), [(32, 8), (52, 22), (46, 46), (18, 46), (12, 22)])
    pygame.draw.polygon(s, (240, 210, 100), [(32, 14), (46, 24), (42, 42), (22, 42), (18, 24)])
    for ox, oy in ((32, 26), (24, 34), (40, 34)):
        pygame.draw.circle(s, (48, 42, 38), (ox, oy), 4)
    return s


def _icon_big_brain() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (200, 100, 160), (14, 12, 36, 40))
    pygame.draw.ellipse(s, (170, 75, 130), (18, 16, 28, 30))
    pygame.draw.line(s, (240, 230, 250), (22, 22), (28, 20), 2)
    pygame.draw.line(s, (240, 230, 250), (36, 22), (42, 20), 2)
    pygame.draw.line(s, (220, 200, 235), (26, 32), (38, 32), 2)
    pygame.draw.circle(s, (255, 250, 255), (24, 26), 3)
    pygame.draw.circle(s, (255, 250, 255), (40, 26), 3)
    return s


def _icon_growth() -> pygame.Surface:
    s = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    pygame.draw.rect(s, (38, 92, 58), (8, 40, 48, 18), border_radius=3)
    for i in range(5):
        h = 28 - i * 5
        pygame.draw.rect(
            s,
            (80 + i * 28, 200 - i * 15, 90 + i * 12),
            (14 + i * 4, 40 - h, 6, h),
            border_radius=2,
        )
    pygame.draw.circle(s, (255, 230, 120), (48, 14), 8)
    pygame.draw.circle(s, (255, 250, 200), (46, 12), 3)
    return s


_ICON_BUILDERS: dict[str, Callable[[], pygame.Surface]] = {
    "lion_shield": _icon_lion_shield,
    "green_shield": _icon_green_shield,
    "lava_sword": _icon_lava_sword,
    "skeleton_staff": _icon_skeleton_staff,
    "twenty_twenty": _icon_twenty_twenty,
    "sacred_heart": _icon_sacred_heart,
    "tread_plating": _icon_tread_plating,
    "overclock_chip": _icon_overclock_chip,
    "thump_rounds": _icon_thump_rounds,
    "the_wiz": _icon_the_wiz,
    "gambling": _icon_gambling,
    "reinforced_hull": _icon_reinforced_hull,
    "machined_barrel": _icon_machined_barrel,
    "glass_cannon": _icon_glass_cannon,
    "neural_magnet": _icon_neural_magnet,
    "soy_milk": _icon_soy_milk,
    "rubber_cement": _icon_rubber_cement,
    "technology_zero": _icon_technology_zero,
    "chocolate_milk": _icon_chocolate_milk,
    "contact_lens": _icon_contact_lens,
    "iron_skin": _icon_iron_skin,
    "battery_cell": _icon_battery_cell,
    "spoon_bender": _icon_spoon_bender,
    "brimstone": _icon_brimstone,
    "mutant_spider": _icon_mutant_spider,
    "thy_nuke": _icon_thy_nuke,
    "polyphemus": _icon_polyphemus,
    "hive_mind": _icon_hive_mind,
    "big_brain": _icon_big_brain,
    "growth": _icon_growth,
}


def _load_optional_png(stem: str, fallback: pygame.Surface) -> pygame.Surface:
    for fname in (f"{stem}.png", f"boi_{stem}.png"):
        p = os.path.join(_ASSETS, fname)
        if os.path.isfile(p):
            img = pygame.image.load(p).convert_alpha()
            w, h = img.get_size()
            m = max(w, h, 1)
            sc = ICON / m
            return pygame.transform.scale(
                img, (max(1, int(w * sc)), max(1, int(h * sc)))
            )
    return fallback


def load_weapon_icon(item_id: str) -> pygame.Surface:
    builder = _ICON_BUILDERS.get(item_id)
    base = builder() if builder else pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    return _load_optional_png(item_id, base)


ITEM_INFO: dict[str, dict[str, str]] = {
    "skeleton_staff": {
        "title": "Skeleton staff",
        "desc": "Legendary: pierce +3 per stack; bullets grow 50% wider after each hit.",
    },
    "lion_shield": {
        "title": "Lion shield",
        "desc": "Common: on damage, ring volley — 4 + stacks shots (5 with one copy, stacks forever).",
    },
    "lava_sword": {
        "title": "Lava sword",
        "desc": "Rare: fire puddles from bullets; +12% puddle DPS per stack.",
    },
    "green_shield": {
        "title": "Green shield",
        "desc": "Common: ×1.5 max HP per stack (multiplicative); heal to full when picked up.",
    },
    "twenty_twenty": {
        "title": "20/20",
        "desc": "Epic: +1 parallel shot per stack (Isaac glasses).",
    },
    "sacred_heart": {
        "title": "Sacred heart",
        "desc": "Legendary: homing, +1 pierce per stack, +48% damage per stack (multiplicative); fire delay ×3 per stack.",
    },
    "tread_plating": {
        "title": "Tread plating",
        "desc": "Common: +12% move speed per stack (tank treads).",
    },
    "overclock_chip": {
        "title": "Overclock chip",
        "desc": "Rare: ~12% faster firing per stack (overdrive CPU).",
    },
    "thump_rounds": {
        "title": "Thump rounds",
        "desc": "Epic: +10% bullet size and +10% fire delay per stack (chunky tradeoff).",
    },
    "the_wiz": {
        "title": "The Wiz",
        "desc": "Epic (Isaac Repentance+ style): two shots at ±38°; each extra stack adds one straight shot forward (wiki.gg).",
    },
    "gambling": {
        "title": "Gambling",
        "desc": "Legendary: +5 random-direction shots per stack; Sacred Heart homing applies to them too.",
    },
    "reinforced_hull": {
        "title": "Reinforced hull",
        "desc": "Common: take 6% less damage per stack (tank / diep armor).",
    },
    "machined_barrel": {
        "title": "Machined barrel",
        "desc": "Common: +8% bullet speed per stack.",
    },
    "glass_cannon": {
        "title": "Glass cannon",
        "desc": "Rare: +18% bullet damage per stack (Isaac glass cannon vibe).",
    },
    "neural_magnet": {
        "title": "Neural magnet",
        "desc": "Common: +10% Sacred Heart homing turn speed per stack (curves harder).",
    },
    "soy_milk": {
        "title": "Soy milk",
        "desc": "Epic: 50% smaller shots, 80% less damage, 5× faster fire per stack — chip DPS; pair with damage items.",
    },
    "rubber_cement": {
        "title": "Rubber cement",
        "desc": "Epic: bullets bounce off the arena edges instead of dying at the border.",
    },
    "technology_zero": {
        "title": "Technology Zero",
        "desc": "Legendary: with 2+ bullets, blue arcs only between tears within ~5 tiles; every 0.2s pulses for ¼ bullet damage (× stacks) along each segment.",
    },
    "chocolate_milk": {
        "title": "Chocolate milk",
        "desc": "Rare: hold fire to charge — bigger, harder shots and longer cooldown after firing; stacks improve charge speed.",
    },
    "contact_lens": {
        "title": "Contact lens",
        "desc": "Common: +1 pierce per stack (extra enemies cleared per shot).",
    },
    "iron_skin": {
        "title": "Iron skin",
        "desc": "Common: −3% damage taken per stack (multiplicative, stacks with Reinforced hull).",
    },
    "battery_cell": {
        "title": "Battery cell",
        "desc": "Rare: ~7% faster firing per stack (multiplicative).",
    },
    "spoon_bender": {
        "title": "Spoon bender",
        "desc": "Rare: shots curve toward foes; weaker than Sacred Heart homing unless you have both.",
    },
    "brimstone": {
        "title": "Brimstone",
        "desc": "Epic: laser beam shots; +10% damage, +8% size, +12% fire delay per stack.",
    },
    "mutant_spider": {
        "title": "Mutant spider",
        "desc": "Epic: +1 parallel tear per stack (stacks with 20/20).",
    },
    "thy_nuke": {
        "title": "Thy nuke",
        "desc": "Epic: −90% attack speed & shot speed, +10 pierce, 5× tear size per stack; mother tears spawn 25 random shots when they expire, leave the map, or use up pierce.",
    },
    "polyphemus": {
        "title": "Polyphemus",
        "desc": "Legendary: huge tears — +42% damage, +38% fire delay, +28% size per stack.",
    },
    "hive_mind": {
        "title": "Hive mind",
        "desc": "Legendary: +3 random-direction extra shots per stack (like a mini Gambling).",
    },
    "big_brain": {
        "title": "Big brain",
        "desc": "Rare: homing tears like Sacred Heart, but turn rate is only 20% as strong (stacks don't multiply turn).",
    },
    "growth": {
        "title": "Growth",
        "desc": "Mythical: each wave you clear adds +1% compounding to damage, size, bullet speed, fire rate, move speed, homing, and lava DPS (× stacks per wave: 1% each stack).",
    },
}


@dataclass
class Pedestal:
    x: float
    y: float
    item_id: str
    active: bool = False
    stand_surf: pygame.Surface | None = None
    icon_surfs: dict[str, pygame.Surface] | None = None

    def ensure_surfaces(self) -> None:
        if self.stand_surf is None:
            self.stand_surf = load_music_stand()
        if self.icon_surfs is None:
            self.icon_surfs = {i: load_weapon_icon(i) for i in PEDESTAL_ITEM_IDS}

    def spawn(self, wx: float, wy: float) -> None:
        self.ensure_surfaces()
        self.x = wx
        self.y = wy
        self.item_id = roll_pedestal_item_id()
        self.active = True

    def spawn_at(self, wx: float, wy: float, item_id: str) -> None:
        """Debug / scripted pedestal with a specific item."""
        self.ensure_surfaces()
        if item_id not in PEDESTAL_ITEM_IDS:
            raise ValueError(item_id)
        self.x = wx
        self.y = wy
        self.item_id = item_id
        self.active = True

    def reroll_item(self) -> None:
        if not self.active:
            return
        self.item_id = roll_pedestal_item_id(exclude=self.item_id)

    def draw(self, target: pygame.Surface, cam: tuple[float, float], anim_t: float = 0.0) -> None:
        if not self.active or self.stand_surf is None or self.icon_surfs is None:
            return
        cx, cy = cam
        stand = self.stand_surf
        sx = int(self.x - cx - stand.get_width() // 2)
        sy = int(self.y - cy - stand.get_height() // 2)
        target.blit(stand, (sx, sy))
        icon = self.icon_surfs.get(self.item_id) if self.icon_surfs else None
        if icon and icon.get_width() > 0:
            bob = math.sin(anim_t * 3.2) * 3.0
            ix = int(self.x - cx - icon.get_width() // 2)
            iy = int(
                self.y
                - cy
                - stand.get_height() // 2
                - icon.get_height()
                - 6
                + bob
            )
            foot_cx = ix + icon.get_width() // 2
            foot_y = iy + icon.get_height() - 1
            pygame.draw.ellipse(
                target,
                (35, 18, 8, 110),
                pygame.Rect(foot_cx - 20, foot_y - 7, 40, 14),
            )
            draw_rarity_glow(
                target,
                ix,
                iy,
                icon.get_width(),
                icon.get_height(),
                self.item_id,
                anim_t,
            )
            target.blit(icon, (ix, iy))


def load_music_stand() -> pygame.Surface:
    path = os.path.join(_ASSETS, "music_stand.png")
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
