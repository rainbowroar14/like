"""LPC Plant Repack — CC-BY-SA 3.0 / GPL 3.0. https://opengameart.org/content/lpc-plant-repack"""
from __future__ import annotations

import os

import pygame

SHEET = os.path.join(os.path.dirname(__file__), "assets", "lpc-plant-repack.png")

# Loose crops on the 416× sheet; each is trimmed to non-transparent pixels after load.
TREE_RECTS = [
    (0, 0, 130, 170),
    (130, 0, 130, 170),
    (260, 0, 130, 170),
    (0, 180, 130, 170),
    (130, 180, 140, 180),
]


def _trim_alpha(surf: pygame.Surface, alpha_min: int = 10) -> pygame.Surface:
    w, h = surf.get_size()
    min_x, min_y = w, h
    max_x, max_y = 0, 0
    for y in range(h):
        for x in range(w):
            if surf.get_at((x, y)).a > alpha_min:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < min_x:
        return surf
    r = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    return surf.subsurface(r).copy()


def load_trees(max_height: int) -> list[pygame.Surface]:
    sheet = pygame.image.load(SHEET)
    out: list[pygame.Surface] = []
    for r in TREE_RECTS:
        sub = sheet.subsurface(pygame.Rect(r)).copy()
        sub = _trim_alpha(sub)
        h = sub.get_height()
        scale = max_height / max(1, h)
        nw = max(1, int(sub.get_width() * scale))
        nh = max(1, int(h * scale))
        out.append(pygame.transform.scale(sub, (nw, nh)))
    return out
