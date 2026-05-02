"""
Top-down survival: dirt arena, waves, Buch tiles + OGA enemies.
Pedestal loot every 2 waves (Music Stand + Epic Weapons icons).
"""
from __future__ import annotations

import math
import os
import sys
from collections import Counter

import pygame

from buch_tiles import BuchTiles, DIRT_FILL, SHEET_PATH as BUCH_PATH
from hostile_assets import HostileArt
from pedestal_items import (
    ITEM_INFO,
    ITEM_RARITY,
    PEDESTAL_ITEM_IDS,
    Pedestal,
    draw_mythical_rainbow_rect,
    draw_rarity_glow,
    rarity_border_rgb,
)
from survivor_extract import ensure_survivor
from survivor_player import SurvivorPlayer
from wave_combat import (
    Enemy,
    FireEmber,
    FireZone,
    GamePhase,
    GunStats,
    Projectile,
    cull_dead_enemies,
    draw_enemy,
    draw_fire_embers,
    draw_fire_puddles,
    draw_projectile,
    draw_technology_zero_chain,
    fire_from_player,
    fire_radial_retaliation,
    projectiles_vs_enemies,
    spawn_enemies,
    spawn_fire_embers,
    steer_homing_projectiles,
    tech_zero_chain_zap,
    thy_nuke_burst_projectiles,
    update_enemies,
    update_fire_embers,
    update_fire_zones,
)
from world import MAP_H, MAP_W, blocks_movement, dirt_variant, parse_world

TITLE = "Towny Town"
TILE = 64
FPS = 60
BASE_MAX_HP = 100.0
PICKUP_RADIUS = 56.0
TOOLTIP_RADIUS = 112.0


class _NoMovementKeys:
    """While spawn or inventory UI is open, WASD must not move the player."""

    __slots__ = ()

    def __getitem__(self, _k: int) -> bool:
        return False


_NO_MOVE_KEYS = _NoMovementKeys()


def _build_spawn_menu_layout(
    sw: int,
    sh: int,
    scroll_y: float,
) -> tuple[list[tuple[pygame.Rect, str]], pygame.Rect, pygame.Rect, float, float]:
    """Spawn menu geometry. Item rows scroll inside viewport; waves row stays fixed."""
    pw = min(780, sw - 24)
    ph = min(520, sh - 28)
    px = (sw - pw) // 2
    py = (sh - ph) // 2
    outer = pygame.Rect(px, py, pw, ph)
    bx = px + 14
    by = py + 44
    waves_rect = pygame.Rect(bx, by, pw - 28, 38)
    item_top = by + 50
    pad_b = 12
    viewport_h = max(80, outer.bottom - pad_b - item_top)
    viewport = pygame.Rect(bx, item_top, pw - 28, viewport_h)
    cols = 3
    gap = 10
    cw = (pw - 28 - (cols - 1) * gap) // cols
    ch = 112
    n = len(PEDESTAL_ITEM_IDS)
    n_rows = (n + cols - 1) // cols if n else 0
    content_h = n_rows * (ch + gap) - gap if n_rows > 0 else 0
    max_scroll = max(0.0, float(content_h - viewport_h))
    sy = max(0.0, min(max_scroll, scroll_y))
    hits: list[tuple[pygame.Rect, str]] = [(waves_rect, "__waves__")]
    for i, pid in enumerate(PEDESTAL_ITEM_IDS):
        r, c = divmod(i, cols)
        rx = bx + c * (cw + gap)
        ry = item_top + r * (ch + gap) - sy
        hits.append((pygame.Rect(rx, ry, cw, ch), pid))
    return hits, outer, viewport, max_scroll, sy


def _feet_box_blocked(cx: float, cy: float) -> bool:
    margin = 12
    foot = 22
    low = TILE - 8
    for ox, oy in (
        (margin, margin + foot),
        (TILE - margin, margin + foot),
        (margin, low),
        (TILE - margin, low),
    ):
        gx = int((cx + ox) // TILE)
        gy = int((cy + oy) // TILE)
        if blocks_movement(gx, gy):
            return True
    return False


def main() -> None:
    pygame.init()
    pygame.display.set_caption(TITLE)

    if not pygame.font.get_init():
        pygame.font.init()

    if not pygame.image.get_extended():
        print("PNG support required.")
        sys.exit(1)

    if not os.path.isfile(BUCH_PATH):
        print("Missing Buch tileset:", BUCH_PATH)
        sys.exit(1)

    world_w, world_h = MAP_W * TILE, MAP_H * TILE
    screen = pygame.display.set_mode((min(1280, world_w), min(720, world_h)))
    sw, sh = screen.get_size()
    clock = pygame.time.Clock()

    root = ensure_survivor()
    base = parse_world()
    buch = BuchTiles(TILE)
    art = HostileArt()

    player = SurvivorPlayer(root, int(TILE * 1.15))
    player.x = world_w * 0.45
    player.y = world_h * 0.42

    projectiles: list[Projectile] = []
    fire_zones: list[FireZone] = []
    fire_embers: list[FireEmber] = []
    enemies: list[Enemy] = []
    gun = GunStats()
    gun_cd = 0.0
    choc_charge = 0.0
    tech_zero_timer = [0.0]
    tech_zero_flash = [0.0]
    wave = 1
    bosses_cleared = [0]
    growth_wave_clears = [0]
    phase = GamePhase.COMBAT
    inter_timer = 0.0
    player_hp = BASE_MAX_HP
    player_max_hp = BASE_MAX_HP
    game_over = False
    last_kill_xy = [player.x, player.y]
    pedestal = Pedestal(0.0, 0.0, "skeleton_staff", active=False)
    equipped_passives: list[str] = []
    damage_taken_mult = 1.0
    lion_shield = False
    game_started = False
    reroll_used = False
    bob_t = 0.0
    player_iframe = 0.0
    spawn_menu_open = False
    spawn_menu_scroll = 0.0
    inventory_open = False
    debug_waves_stopped = False

    font = pygame.font.SysFont("segoe ui", 16)
    font_big = pygame.font.SysFont("segoe ui", 22)

    def spawn_wave_enemies() -> None:
        if not debug_waves_stopped:
            hp_mult = 1.5 ** bosses_cleared[0]
            spawn_enemies(
                wave, world_w, world_h, enemies, post_boss_hp_mult=hp_mult
            )

    def toggle_debug_waves() -> None:
        nonlocal debug_waves_stopped, phase, inter_timer
        debug_waves_stopped = not debug_waves_stopped
        if debug_waves_stopped:
            enemies.clear()
            phase = GamePhase.COMBAT
            inter_timer = 0.0
            projectiles.clear()
            fire_zones.clear()
            fire_embers.clear()

    def sync_equipment_stats() -> None:
        nonlocal player_max_hp, player_hp
        n_green = equipped_passives.count("green_shield")
        if n_green:
            player_max_hp = BASE_MAX_HP * (1.5**n_green)
        else:
            player_max_hp = BASE_MAX_HP
        player_hp = min(player_hp, player_max_hp)

    def apply_all_passives() -> None:
        """Recompute gun stats from every pedestal pickup (unlimited stacking)."""
        nonlocal lion_shield, damage_taken_mult
        gun.pierce_bonus = 0
        gun.pierce_grows = False
        gun.fire_trail = False
        gun.parallel_extra = 0
        gun.sacred_heart_stacks = 0
        gun.wiz_stacks = 0
        gun.gambling_stacks = 0
        gun.lion_ring_count = 0
        gun.lava_dps_mult = 1.0
        gun.homing_turn_mult = 1.0
        gun.speed_mult = 1.0
        lion_shield = False
        damage_taken_mult = (0.94 ** equipped_passives.count("reinforced_hull")) * (
            0.97 ** equipped_passives.count("iron_skin")
        )
        n_staff = equipped_passives.count("skeleton_staff")
        if n_staff:
            gun.pierce_bonus += 3 * n_staff
            gun.pierce_grows = True
        n_heart = equipped_passives.count("sacred_heart")
        gun.sacred_heart_stacks = n_heart
        if n_heart:
            gun.pierce_bonus += n_heart
        gun.pierce_bonus += equipped_passives.count("contact_lens")
        gun.pierce_bonus += 10 * equipped_passives.count("thy_nuke")
        gun.parallel_extra = equipped_passives.count("twenty_twenty") + equipped_passives.count(
            "mutant_spider"
        )
        n_lava = equipped_passives.count("lava_sword")
        if n_lava:
            gun.fire_trail = True
            gun.lava_dps_mult = 1.12**n_lava
        n_lion = equipped_passives.count("lion_shield")
        if n_lion:
            lion_shield = True
            gun.lion_ring_count = 4 + n_lion
        gun.wiz_stacks = equipped_passives.count("the_wiz")
        gun.gambling_stacks = equipped_passives.count("gambling")
        gun.player_speed_mult = 1.12 ** equipped_passives.count("tread_plating")
        n_oc = equipped_passives.count("overclock_chip")
        n_bat = equipped_passives.count("battery_cell")
        n_thump = equipped_passives.count("thump_rounds")
        n_soy = equipped_passives.count("soy_milk")
        n_glass = equipped_passives.count("glass_cannon")
        n_brim = equipped_passives.count("brimstone")
        n_poly = equipped_passives.count("polyphemus")
        n_nuke = equipped_passives.count("thy_nuke")
        gun.thy_nuke_stacks = n_nuke
        gun.laser_visual = n_brim > 0
        gun.interval_mult = (
            (0.88**n_oc)
            * (0.93**n_bat)
            * (1.10**n_thump)
            * (0.2**n_soy)
            * (1.12**n_brim)
            * (1.38**n_poly)
            * (10**n_nuke)
        )
        gun.radius_mult = (
            (1.10**n_thump)
            * (0.5**n_soy)
            * (1.08**n_brim)
            * (1.28**n_poly)
            * (5**n_nuke)
        )
        gun.damage_mult = (
            (1.18**n_glass)
            * (1.48**n_heart)
            * (0.2**n_soy)
            * (1.1**n_brim)
            * (1.42**n_poly)
        )
        gun.speed_mult = (1.08 ** equipped_passives.count("machined_barrel")) * (
            0.1**n_nuke
        )
        gun.homing_turn_mult = 1.1 ** equipped_passives.count("neural_magnet")
        gun.rubber_cement_stacks = equipped_passives.count("rubber_cement")
        gun.tech_zero_stacks = equipped_passives.count("technology_zero")
        gun.chocolate_milk_stacks = equipped_passives.count("chocolate_milk")
        gun.spoon_bender_stacks = equipped_passives.count("spoon_bender")
        gun.hive_mind_stacks = equipped_passives.count("hive_mind")
        gun.big_brain_stacks = equipped_passives.count("big_brain")
        n_growth = equipped_passives.count("growth")
        growth_mult = (
            (1.0 + 0.01 * n_growth) ** growth_wave_clears[0]
            if n_growth > 0
            else 1.0
        )
        if growth_mult != 1.0:
            gun.damage_mult *= growth_mult
            gun.radius_mult *= growth_mult
            gun.speed_mult *= growth_mult
            gun.interval_mult /= growth_mult
            gun.homing_turn_mult *= growth_mult
            gun.lava_dps_mult *= growth_mult
            gun.player_speed_mult *= growth_mult
        sync_equipment_stats()

    def take_pedestal_item() -> None:
        nonlocal player_hp
        if not pedestal.active:
            return
        pid = pedestal.item_id
        equipped_passives.append(pid)
        apply_all_passives()
        if pid == "green_shield":
            player_hp = player_max_hp
        pedestal.active = False

    def end_intermission() -> None:
        nonlocal phase, wave, inter_timer
        inter_timer = 0.0
        wave += 1
        spawn_wave_enemies()
        phase = GamePhase.COMBAT

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        bob_t += dt

        cam_x = max(0, min(player.x - sw / 2, world_w - sw))
        cam_y = max(0, min(player.y - sh / 2, world_h - sh))

        mx, my = pygame.mouse.get_pos()
        mwx, mwy = mx + cam_x, my + cam_y

        near_pedestal = (
            pedestal.active
            and math.hypot(player.x - pedestal.x, player.y - pedestal.y) < TOOLTIP_RADIUS
        )
        can_pickup = (
            pedestal.active
            and math.hypot(player.x - pedestal.x, player.y - pedestal.y) < PICKUP_RADIUS
        )

        spawn_hits: list[tuple[pygame.Rect, str]] = []
        spawn_outer: pygame.Rect | None = None
        spawn_viewport = pygame.Rect(0, 0, 0, 0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if not game_started:
                    if event.key == pygame.K_SPACE:
                        game_started = True
                        spawn_wave_enemies()
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    continue
                backtick = event.key == pygame.K_BACKQUOTE or event.unicode == "`"
                if backtick and not game_over:
                    spawn_menu_open = not spawn_menu_open
                    if spawn_menu_open:
                        spawn_menu_scroll = 0.0
                        inventory_open = False
                        pedestal.ensure_surfaces()
                    continue
                if event.key == pygame.K_ESCAPE:
                    if spawn_menu_open:
                        spawn_menu_open = False
                    elif inventory_open:
                        inventory_open = False
                    else:
                        running = False
                    continue
                elif (
                    phase == GamePhase.INTERMISSION
                    and not game_over
                    and event.key == pygame.K_SPACE
                    and not spawn_menu_open
                    and not inventory_open
                ):
                    end_intermission()
                elif (
                    not game_over
                    and event.key == pygame.K_e
                    and phase in (GamePhase.COMBAT, GamePhase.INTERMISSION)
                ):
                    if can_pickup:
                        take_pedestal_item()
                    else:
                        inventory_open = not inventory_open
                        if inventory_open:
                            spawn_menu_open = False
                elif (
                    not game_over
                    and phase == GamePhase.COMBAT
                    and event.key == pygame.K_r
                    and can_pickup
                    and not reroll_used
                ):
                    pedestal.reroll_item()
                    reroll_used = True
                elif game_over and event.key == pygame.K_r:
                    game_over = False
                    player_hp = BASE_MAX_HP
                    player_max_hp = BASE_MAX_HP
                    wave = 1
                    gun = GunStats()
                    gun_cd = 0.0
                    choc_charge = 0.0
                    tech_zero_timer[0] = 0.0
                    tech_zero_flash[0] = 0.0
                    bosses_cleared[0] = 0
                    growth_wave_clears[0] = 0
                    enemies.clear()
                    projectiles.clear()
                    fire_zones.clear()
                    fire_embers.clear()
                    phase = GamePhase.COMBAT
                    inter_timer = 0.0
                    pedestal.active = False
                    equipped_passives.clear()
                    gun = GunStats()
                    lion_shield = False
                    reroll_used = False
                    player_iframe = 0.0
                    last_kill_xy[0] = player.x
                    last_kill_xy[1] = player.y
                    apply_all_passives()
                    spawn_wave_enemies()
                    player.x = world_w * 0.45
                    player.y = world_h * 0.42
                    spawn_menu_open = False
                    inventory_open = False
            elif event.type == pygame.MOUSEWHEEL and spawn_menu_open:
                spawn_menu_scroll -= event.y * 44.0
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and spawn_menu_open:
                click_hits, _, click_vp, _, spawn_menu_scroll = _build_spawn_menu_layout(
                    sw, sh, spawn_menu_scroll
                )
                for rect, tag in click_hits:
                    if not rect.collidepoint(event.pos):
                        continue
                    if tag != "__waves__" and not click_vp.collidepoint(event.pos):
                        continue
                    if tag == "__waves__":
                        toggle_debug_waves()
                    else:
                        pedestal.spawn_at(player.x, player.y - 24.0, tag)
                        reroll_used = False
                    break

        ui_blocks_world = spawn_menu_open or inventory_open

        if spawn_menu_open:
            spawn_hits, spawn_outer, spawn_viewport, _, spawn_menu_scroll = (
                _build_spawn_menu_layout(sw, sh, spawn_menu_scroll)
            )

        if not game_started:
            cam_x = max(0, min(player.x - sw / 2, world_w - sw))
            cam_y = max(0, min(player.y - sh / 2, world_h - sh))
            screen.fill(DIRT_FILL)
            vx0 = int(cam_x // TILE)
            vy0 = int(cam_y // TILE)
            vx1 = int((cam_x + sw) // TILE) + 2
            vy1 = int((cam_y + sh) // TILE) + 2
            for ty in range(max(0, vy0), min(MAP_H, vy1)):
                for tx in range(max(0, vx0), min(MAP_W, vx1)):
                    ch = base[ty][tx]
                    surf = buch.dirt_at(tx, ty, dirt_variant(ch))
                    screen.blit(surf, (tx * TILE - cam_x, ty * TILE - cam_y))
            cam = (cam_x, cam_y)
            player.update(dt, _NO_MOVE_KEYS, (player.x + 120.0, player.y))
            player.draw(screen, cam, (player.x + 120.0, player.y), _NO_MOVE_KEYS)
            t1 = font_big.render(TITLE, True, (255, 248, 235))
            t2 = font_big.render("Press SPACE to start", True, (255, 230, 190))
            t3 = font.render("Esc quit", True, (200, 200, 210))
            screen.blit(t1, (sw // 2 - t1.get_width() // 2, sh // 2 - 72))
            screen.blit(t2, (sw // 2 - t2.get_width() // 2, sh // 2 - 24))
            screen.blit(t3, (sw // 2 - t3.get_width() // 2, sh // 2 + 20))
            pygame.display.flip()
            continue

        keys = pygame.key.get_pressed()
        if not game_over and phase in (GamePhase.COMBAT, GamePhase.INTERMISSION):
            player.speed = 220.0 * gun.player_speed_mult
            ox, oy = player.x, player.y
            pl_keys = _NO_MOVE_KEYS if ui_blocks_world else keys
            player.update(dt, pl_keys, (mwx, mwy))
            box_x = player.x - TILE / 2
            if _feet_box_blocked(box_x, oy - TILE / 2):
                player.x = ox
            box_x = player.x - TILE / 2
            if _feet_box_blocked(box_x, player.y - TILE / 2):
                player.y = oy
            player.x = max(TILE / 2, min(world_w - TILE / 2, player.x))
            player.y = max(TILE / 2, min(world_h - TILE / 2, player.y))
            player_iframe = max(0.0, player_iframe - dt)

            if phase == GamePhase.COMBAT:

                def _hit(dmg: float) -> None:
                    nonlocal player_hp, game_over, player_iframe
                    if dmg <= 0.0:
                        return
                    if player_iframe > 0.0:
                        return
                    player_hp -= dmg * damage_taken_mult
                    player_iframe = 1.75
                    if player_hp <= 0:
                        player_hp = 0.0
                        game_over = True
                        return
                    if lion_shield and dmg > 0:
                        projectiles.extend(
                            fire_radial_retaliation(gun, player.x, player.y, art)
                        )

                adx, ady = mwx - player.x, mwy - player.y
                aln = math.hypot(adx, ady) or 1.0
                update_enemies(
                    enemies,
                    dt,
                    player.x,
                    player.y,
                    world_w,
                    world_h,
                    _hit,
                    aim_dx=adx / aln,
                    aim_dy=ady / aln,
                )
                gun_cd = max(0.0, gun_cd - dt)
                if gun.chocolate_milk_stacks > 0 and not ui_blocks_world:
                    if pygame.mouse.get_pressed()[0]:
                        choc_charge = min(
                            1.0,
                            choc_charge
                            + dt * (1.05 + 0.4 * gun.chocolate_milk_stacks),
                        )
                    else:
                        choc_charge = max(0.0, choc_charge - dt * 2.0)
                elif choc_charge > 0.0:
                    choc_charge = max(0.0, choc_charge - dt * 3.0)

                if (
                    pygame.mouse.get_pressed()[0]
                    and gun_cd <= 0
                    and not ui_blocks_world
                ):
                    projectiles.extend(
                        fire_from_player(
                            gun,
                            player.x,
                            player.y,
                            mwx,
                            mwy,
                            art,
                            chocolate_charge=choc_charge,
                        )
                    )
                    gun_cd = gun.interval() * (
                        1.0
                        + 0.42
                        * choc_charge
                        * max(1, gun.chocolate_milk_stacks)
                    )
                    if gun.chocolate_milk_stacks > 0:
                        choc_charge = 0.0
                    player.trigger_shoot()

                bnd = (-80.0, -80.0, world_w + 80.0, world_h + 80.0)
                inner_b = (12.0, 12.0, world_w - 12.0, world_h - 12.0)
                proj_next: list[Projectile] = []
                for p in projectiles:
                    if p.update(
                        dt,
                        bnd,
                        inner_b if p.rubber_bounce else None,
                    ):
                        proj_next.append(p)
                    elif p.nuke_mother and gun.thy_nuke_stacks > 0:
                        proj_next.extend(thy_nuke_burst_projectiles(gun, p))
                projectiles = proj_next
                hom_turn = 5.8 * gun.homing_turn_mult
                if gun.sacred_heart_stacks > 0:
                    pass
                elif gun.big_brain_stacks > 0:
                    hom_turn *= 0.2
                elif gun.spoon_bender_stacks > 0:
                    hom_turn *= min(
                        0.92,
                        0.48 + 0.12 * gun.spoon_bender_stacks,
                    )
                steer_homing_projectiles(
                    projectiles, enemies, dt, turn_rate=hom_turn
                )
                for p in projectiles:
                    p.trail_emit_cd -= dt
                    if p.spawn_fire_trail and p.trail_emit_cd <= 0.0:
                        p.trail_emit_cd = 0.055
                        fire_zones.append(
                            FireZone(
                                p.x,
                                p.y,
                                max(18.0, p.radius * 2.4),
                                0.5,
                                dps=42.0 * gun.lava_dps_mult,
                            )
                        )
                tech_zero_chain_zap(
                    projectiles,
                    enemies,
                    gun,
                    dt,
                    tech_zero_timer,
                    art.hit_vfx_sets,
                    pulse_flash=tech_zero_flash,
                )
                projectiles.extend(
                    projectiles_vs_enemies(
                        projectiles, enemies, art.hit_vfx_sets, gun
                    )
                )
                update_fire_zones(fire_zones, enemies, dt)
                spawn_fire_embers(fire_zones, dt, fire_embers)
                update_fire_embers(fire_embers, dt)
                cull_dead_enemies(enemies, last_kill_xy, bosses_cleared)

                if not enemies and not game_over:
                    if equipped_passives.count("growth") > 0:
                        growth_wave_clears[0] += 1
                        apply_all_passives()
                    projectiles.clear()
                    fire_zones.clear()
                    fire_embers.clear()
                    phase = GamePhase.INTERMISSION
                    inter_timer = 20.0
                    if wave % 2 == 0:
                        pedestal.spawn(last_kill_xy[0], last_kill_xy[1])
                        reroll_used = False

            elif phase == GamePhase.INTERMISSION:
                inter_timer -= dt
                if inter_timer <= 0:
                    end_intermission()

        screen.fill(DIRT_FILL)

        vx0 = int(cam_x // TILE)
        vy0 = int(cam_y // TILE)
        vx1 = int((cam_x + sw) // TILE) + 2
        vy1 = int((cam_y + sh) // TILE) + 2

        for ty in range(max(0, vy0), min(MAP_H, vy1)):
            for tx in range(max(0, vx0), min(MAP_W, vx1)):
                ch = base[ty][tx]
                surf = buch.dirt_at(tx, ty, dirt_variant(ch))
                screen.blit(surf, (tx * TILE - cam_x, ty * TILE - cam_y))

        cam = (cam_x, cam_y)
        pedestal.draw(screen, cam, bob_t)
        draw_fire_puddles(screen, fire_zones, cam)

        py_sort = player.y + 8.0
        enemies_sorted = sorted(enemies, key=lambda e: e.y)
        for e in enemies_sorted:
            if e.y <= py_sort:
                draw_enemy(screen, art, e, cam)
        player.draw(
            screen,
            cam,
            (mwx, mwy),
            _NO_MOVE_KEYS if ui_blocks_world else keys,
            invuln_blink=player_iframe > 0.0 and not game_over,
        )
        for e in enemies_sorted:
            if e.y > py_sort:
                draw_enemy(screen, art, e, cam)
        draw_fire_embers(screen, fire_embers, cam)
        draw_technology_zero_chain(
            screen, projectiles, gun, cam, tech_zero_flash[0]
        )
        tech_zero_flash[0] = max(0.0, tech_zero_flash[0] - dt * 4.5)
        for p in projectiles:
            draw_projectile(screen, art, p, cam)

        imps = [e for e in enemies if e.kind in ("imp", "boss")]
        if imps:
            bw = sw - 48
            bx = 24
            by = 52
            tot_hp = sum(e.hp for e in imps)
            tot_mx = sum(e.max_hp for e in imps)
            pygame.draw.rect(screen, (28, 24, 22), (bx, by, bw, 18))
            frac = max(0.0, min(1.0, tot_hp / tot_mx))
            pygame.draw.rect(screen, (210, 50, 80), (bx + 2, by + 2, int((bw - 4) * frac), 14))
            lbl = font.render(f"Elites ({len(imps)})", True, (250, 245, 240))
            screen.blit(lbl, (bx + bw // 2 - lbl.get_width() // 2, by - 20))

        hb_w = 180
        pygame.draw.rect(screen, (30, 28, 26), (10, sh - 28, hb_w, 16))
        hf = max(0.0, min(1.0, player_hp / player_max_hp))
        pygame.draw.rect(screen, (70, 180, 95), (12, sh - 26, int((hb_w - 4) * hf), 12))

        hud = font.render(
            "` spawn menu — E inventory / take loot — R reroll — hold shoot — Esc",
            True,
            (230, 230, 235),
        )
        screen.blit(hud, (8, 6))
        wave_lbl = font.render(f"Wave {wave}", True, (240, 235, 230))
        screen.blit(wave_lbl, (8, 26))

        if near_pedestal and pedestal.active:
            info = ITEM_INFO.get(pedestal.item_id, {})
            title = font_big.render(info.get("title", "?"), True, (255, 248, 220))
            desc = font.render(info.get("desc", ""), True, (220, 215, 205))
            screen.blit(title, (16, sh - 92))
            screen.blit(desc, (16, sh - 64))
            if can_pickup:
                hint = font.render(
                    "E take item" + ("" if reroll_used else " — R reroll once"),
                    True,
                    (190, 255, 190),
                )
                screen.blit(hint, (16, sh - 40))

        if phase == GamePhase.INTERMISSION and not game_over:
            msg = font_big.render(
                f"Next wave in {max(0, int(math.ceil(inter_timer)))}s — Space skip",
                True,
                (255, 240, 200),
            )
            screen.blit(msg, (sw // 2 - msg.get_width() // 2, sh // 2 - 40))

        if game_over:
            spawn_menu_open = False
            inventory_open = False
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((8, 6, 4, 210))
            screen.blit(overlay, (0, 0))
            go = font_big.render("Destroyed — press R to restart", True, (255, 220, 200))
            screen.blit(go, (sw // 2 - go.get_width() // 2, sh // 2 - 20))

        if spawn_menu_open and spawn_outer is not None and not game_over:
            dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 140))
            screen.blit(dim, (0, 0))
            pygame.draw.rect(screen, (24, 28, 38), spawn_outer)
            pygame.draw.rect(screen, (120, 130, 165), spawn_outer, 2)
            title = font_big.render(
                "Spawn menu — scroll wheel — click item (` or Esc)",
                True,
                (235, 240, 255),
            )
            screen.blit(title, (spawn_outer.x + 12, spawn_outer.y + 10))
            prev_clip = screen.get_clip()
            for rect, tag in spawn_hits:
                if tag != "__waves__":
                    continue
                pygame.draw.rect(screen, (48, 54, 68), rect)
                pygame.draw.rect(screen, (130, 140, 175), rect, 1)
                wtxt = "Stop waves" if not debug_waves_stopped else "Resume waves"
                wsub = "ON — no spawns" if debug_waves_stopped else "OFF — normal"
                t1 = font.render(wtxt, True, (255, 230, 200))
                t2 = font.render(wsub, True, (200, 205, 220))
                screen.blit(t1, (rect.x + 8, rect.y + 6))
                screen.blit(t2, (rect.x + 8, rect.y + 26))
            screen.set_clip(spawn_viewport)
            for rect, tag in spawn_hits:
                if tag == "__waves__":
                    continue
                pygame.draw.rect(screen, (48, 54, 68), rect)
                rid = ITEM_RARITY.get(tag, "common")
                if rid == "mythical":
                    draw_mythical_rainbow_rect(screen, rect, bob_t, 2)
                else:
                    pygame.draw.rect(screen, rarity_border_rgb(tag, bob_t), rect, 2)
                info = ITEM_INFO.get(tag, {})
                ic = None
                if pedestal.icon_surfs:
                    ic = pedestal.icon_surfs.get(tag)
                if ic:
                    iy_ic = rect.y + 6
                    ix = rect.centerx - ic.get_width() // 2
                    draw_rarity_glow(
                        screen,
                        ix,
                        iy_ic,
                        ic.get_width(),
                        ic.get_height(),
                        tag,
                        bob_t,
                    )
                    screen.blit(ic, (ix, iy_ic))
                t = font.render(info.get("title", tag)[:20], True, (250, 245, 235))
                screen.blit(t, (rect.x + 4, rect.bottom - 20))
            screen.set_clip(prev_clip)
            pygame.draw.rect(screen, (80, 90, 110), spawn_viewport, 1)

        if inventory_open and not game_over:
            dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 120))
            screen.blit(dim, (0, 0))
            ix0, iy0 = 40, 48
            iw = min(520, sw - 80)
            ih = min(sh - 96, 420)
            inv_r = pygame.Rect(ix0, iy0, iw, ih)
            pygame.draw.rect(screen, (26, 30, 38), inv_r)
            pygame.draw.rect(screen, (100, 115, 145), inv_r, 2)
            hdr = font_big.render("Inventory (E or Esc to close)", True, (240, 238, 255))
            screen.blit(hdr, (ix0 + 14, iy0 + 10))
            iy = iy0 + 46
            if not equipped_passives:
                empty = font.render("Nothing yet — pick up pedestal items with E.", True, (190, 195, 205))
                screen.blit(empty, (ix0 + 14, iy))
            else:
                for pid, cnt in sorted(Counter(equipped_passives).items()):
                    inf = ITEM_INFO.get(pid, {})
                    title = inf.get("title", pid)
                    if cnt > 1:
                        title = f"{title} ×{cnt}"
                    line = font_big.render(title, True, (255, 250, 240))
                    screen.blit(line, (ix0 + 14, iy))
                    iy += 24
                    desc = inf.get("desc", "")
                    while desc:
                        chunk = desc[:72]
                        desc = desc[72:]
                        row = font.render(chunk, True, (205, 210, 220))
                        screen.blit(row, (ix0 + 22, iy))
                        iy += 18
                        if iy > iy0 + ih - 28:
                            break
                    iy += 10
                    if iy > iy0 + ih - 28:
                        break

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
