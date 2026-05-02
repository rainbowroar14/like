"""Riley Gombart — Animated Top Down Survivor (handgun). CC-BY 3.0.
https://opengameart.org/content/animated-top-down-survivor-player
"""
from __future__ import annotations

import math
import os
import re
from typing import Literal

import pygame

Mode = Literal["idle", "move", "shoot"]


def _load_sequence(folder: str, prefix: str) -> list[pygame.Surface]:
    pat = re.compile(rf"{re.escape(prefix)}_(\d+)\.png$")
    files: list[tuple[int, str]] = []
    for name in os.listdir(folder):
        m = pat.match(name)
        if m:
            files.append((int(m.group(1)), os.path.join(folder, name)))
    files.sort(key=lambda t: t[0])
    if not files:
        raise FileNotFoundError(f"No frames matching {prefix}_*.png in {folder}")
    return [pygame.image.load(p).convert_alpha() for _, p in files]


class SurvivorPlayer:
    def __init__(self, survivor_root: str, on_screen_height: int) -> None:
        hg = os.path.join(survivor_root, "handgun")
        self.idle = _load_sequence(os.path.join(hg, "idle"), "survivor-idle_handgun")
        self.move = _load_sequence(os.path.join(hg, "move"), "survivor-move_handgun")
        self.shoot = _load_sequence(os.path.join(hg, "shoot"), "survivor-shoot_handgun")

        base = self.idle[0]
        self.scale = on_screen_height / max(1, base.get_height())
        self.anim_index = 0.0
        self.shoot_time = 0.0
        self.x = 0.0
        self.y = 0.0
        self.speed = 220.0

    def update(
        self,
        dt: float,
        keys: pygame.key.ScancodeWrapper,
        mouse_world: tuple[float, float],
    ) -> None:
        vx = vy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            vy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            vy += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            vx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            vx += 1.0
        ln = math.hypot(vx, vy)
        moving = ln > 0
        if moving:
            vx /= ln
            vy /= ln
            self.x += vx * self.speed * dt
            self.y += vy * self.speed * dt
            self.anim_index += dt * 14.0
        else:
            self.anim_index += dt * 6.0

        if self.shoot_time > 0:
            self.shoot_time = max(0.0, self.shoot_time - dt)

    def trigger_shoot(self) -> None:
        self.shoot_time = 0.22

    def aim_rotation_deg(self, mouse_world: tuple[float, float]) -> float:
        """Aim gun at cursor. Sprite forward is toward top of image (screen −y). pygame.rotate is CCW."""
        mx, my = mouse_world
        dx, dy = mx - self.x, my - self.y
        if dx * dx + dy * dy < 1.0:
            dx, dy = 1.0, 0.0
        # Screen: atan2(dy,dx) → 0° east, 90° south, −90° north. Forward in art = north (−90°).
        theta = math.degrees(math.atan2(dy, dx))
        # −θ−90 plus 90° CCW (left) → −θ
        return -theta

    def is_moving(self, keys: pygame.key.ScancodeWrapper) -> bool:
        return bool(
            keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]
            or keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]
        )

    def current_mode(self, moving: bool) -> Mode:
        if self.shoot_time > 0:
            return "shoot"
        if moving:
            return "move"
        return "idle"

    def draw(
        self,
        target: pygame.Surface,
        camera: tuple[float, float],
        mouse_world: tuple[float, float],
        keys: pygame.key.ScancodeWrapper,
        invuln_blink: bool = False,
    ) -> None:
        if invuln_blink and (pygame.time.get_ticks() // 75) % 2 == 0:
            return
        moving = self.is_moving(keys)
        mode = self.current_mode(moving)
        if mode == "shoot":
            seq = self.shoot
            t = 1.0 - (self.shoot_time / 0.22)
            f = min(len(seq) - 1, int(t * len(seq)))
        elif mode == "move":
            seq = self.move
            f = int(self.anim_index) % len(seq)
        else:
            seq = self.idle
            f = int(self.anim_index) % len(seq)

        raw = seq[f]
        rot = pygame.transform.rotate(raw, self.aim_rotation_deg(mouse_world))
        w = max(1, int(rot.get_width() * self.scale))
        h = max(1, int(rot.get_height() * self.scale))
        img = pygame.transform.scale(rot, (w, h))

        cam_x, cam_y = camera
        rect = img.get_rect(center=(int(self.x - cam_x), int(self.y - cam_y)))
        target.blit(img, rect.topleft)
