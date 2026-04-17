from __future__ import annotations

import os
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game import config
from game.balance import enemy_scaling
from game.entities import Enemy
from game.content import CHARACTERS, WEAPONS, Upgrade
from game.game import Game, RoomState
from game.map_system import Chamber, RoomLayout, RoomObstacle, build_maze_room_layout


def make_room_layout(arena: pygame.Rect, obstacles: list[RoomObstacle]) -> RoomLayout:
    chamber_rect = arena.inflate(-48, -48)
    chamber = Chamber((0, 0), chamber_rect, pygame.Vector2(chamber_rect.center))
    return RoomLayout(
        name="smoke",
        theme="????",
        family="single",
        grid_size=(1, 1),
        obstacles=list(obstacles),
        doorways=[],
        chambers={(0, 0): chamber},
        links={(0, 0): ()},
        door_centers={},
        player_spawn=pygame.Vector2(chamber.center),
        enemy_cells=((0, 0),),
        pickup_cells=((0, 0),),
        screen_doors={},
        door_entries={},
    )


def install_room(game: Game, layout: RoomLayout, enemies: list[Enemy], player_pos: pygame.Vector2) -> None:
    room_state = RoomState(
        room_id=9001,
        coord=(0, 0),
        room_type="combat",
        difficulty=1,
        neighbors={},
        layout=layout,
    )
    room_state.enemies = enemies
    room_state.pickups = []
    game.current_room_id = room_state.room_id
    game.current_room_state = room_state
    game.room_layout = layout
    game.obstacles = list(layout.obstacles)
    game.enemies = room_state.enemies
    game.pickups = []
    game.bullets.clear()
    game.laser_traces.clear()
    game.explosion_waves.clear()
    game.gas_clouds.clear()
    game.floaters.clear()
    game.clear_navigation_fields()
    game.refresh_obstacle_state()
    game.refresh_enemy_spatial_index()
    game.player_pos = player_pos.copy()
    game.player_hp = 10000.0
    game.iframes = 9999.0


def install_shop_room(game: Game, layout: RoomLayout, offers) -> RoomState:
    install_room(game, layout, [], layout.player_spawn.copy())
    room_state = game.current_room_state
    assert room_state is not None
    room_state.room_type = "shop"
    room_state.resolved = True
    room_state.shop_offers = list(offers)
    room_state.shop_purchases = 0
    game.current_room_state = room_state
    game.mode = "playing"
    return room_state


def make_enemy(x: float, y: float, *, kind: str = "grunt", boss: bool = False, variant: str = "") -> Enemy:
    speed = config.BOSS_SPEED if boss else config.ENEMY_SPEED
    radius = config.BOSS_RADIUS if boss else config.ENEMY_RADIUS
    color = config.BOSS_COLOR if boss else config.ENEMY_COLOR
    cooldown = 0.55 if kind in {"shooter", "laser", "shotgunner", "elite"} or boss else 0.0
    return Enemy(
        pos=pygame.Vector2(x, y),
        hp=1200.0 if boss else 180.0,
        max_hp=1200.0 if boss else 180.0,
        speed=float(speed),
        radius=radius,
        damage=8.0,
        xp_reward=1,
        color=color,
        is_boss=boss,
        kind="boss" if boss else kind,
        variant=variant,
        shoot_cooldown=cooldown,
        shoot_timer=0.0,
    )


def simulate(game: Game, seconds: float, *, track: Enemy | None = None):
    dt = 1.0 / config.FPS
    history = []
    for _ in range(int(seconds * config.FPS)):
        game.update_enemies(dt)
        if track is not None:
            history.append(track.pos.copy())
    return history


def max_stall_frames(history: list[pygame.Vector2], center: pygame.Vector2, radius: float) -> int:
    best = 0
    current = 0
    prev = history[0] if history else None
    for pos in history[1:]:
        moved = 0.0 if prev is None else pos.distance_to(prev)
        if pos.distance_to(center) <= radius and moved < 1.25:
            current += 1
            best = max(best, current)
        else:
            current = 0
        prev = pos
    return best


def wall_gap_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    cx, cy = arena.center
    gap = 24
    thickness = 16
    span = 180
    obstacles = [
        RoomObstacle(pygame.Rect(cx - span, cy - thickness // 2, span - gap // 2, thickness), tag="wall"),
        RoomObstacle(pygame.Rect(cx + gap // 2, cy - thickness // 2, span - gap // 2, thickness), tag="wall"),
        RoomObstacle(pygame.Rect(cx - thickness // 2, cy - span, thickness, span - gap // 2), tag="wall"),
        RoomObstacle(pygame.Rect(cx - thickness // 2, cy + gap // 2, thickness, span - gap // 2), tag="wall"),
    ]
    layout = make_room_layout(arena, obstacles)
    enemy = make_enemy(arena.left + 150, cy - 8)
    player = pygame.Vector2(arena.right - 150, cy + 8)
    install_room(game, layout, [enemy], player)
    start_distance = enemy.pos.distance_to(player)
    history = simulate(game, 4.0, track=enemy)
    final_distance = enemy.pos.distance_to(player)
    progress = start_distance - final_distance
    stalled = max_stall_frames(history, pygame.Vector2(cx, cy), 42.0)
    success = progress > 200.0 and stalled < 20
    return success, f"progress={progress:.1f}, max_stall_frames={stalled}, final=({enemy.pos.x:.1f},{enemy.pos.y:.1f})"


def obstacle_detour_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    box = RoomObstacle(pygame.Rect(arena.centerx - 44, arena.centery - 52, 88, 104), destructible=True, max_hp=100.0, hp=100.0, tag="crate")
    layout = make_room_layout(arena, [box])
    enemy = make_enemy(arena.left + 140, arena.centery)
    player = pygame.Vector2(arena.right - 160, arena.centery + 6)
    install_room(game, layout, [enemy], player)
    start_distance = enemy.pos.distance_to(player)
    simulate(game, 4.0, track=enemy)
    final_distance = enemy.pos.distance_to(player)
    progress = start_distance - final_distance
    clear_los = game.find_line_of_sight_blocker(enemy.pos, player, max(6, enemy.radius // 2)) is None
    success = progress > 220.0 and clear_los
    return success, f"progress={progress:.1f}, clear_los={clear_los}, final=({enemy.pos.x:.1f},{enemy.pos.y:.1f})"


def multi_enemy_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    obstacles = [
        RoomObstacle(pygame.Rect(arena.centerx - 54, arena.centery - 110, 108, 36), tag="wall"),
        RoomObstacle(pygame.Rect(arena.centerx - 54, arena.centery + 74, 108, 36), tag="wall"),
        RoomObstacle(pygame.Rect(arena.centerx - 20, arena.centery - 44, 40, 88), destructible=True, max_hp=120.0, hp=120.0, tag="crate"),
    ]
    layout = make_room_layout(arena, obstacles)
    player = pygame.Vector2(arena.right - 140, arena.centery)
    enemies = []
    starts = []
    for idx in range(8):
        pos = pygame.Vector2(arena.left + 120 + (idx % 4) * 24, arena.centery - 110 + (idx // 4) * 220)
        enemy = make_enemy(pos.x, pos.y, kind="grunt" if idx % 2 == 0 else "charger")
        enemies.append(enemy)
        starts.append(pos)
    install_room(game, layout, enemies, player)
    simulate(game, 4.5)
    progresses = [start.distance_to(player) - enemy.pos.distance_to(player) for start, enemy in zip(starts, enemies)]
    moved = sum(1 for value in progresses if value > 140.0)
    min_pair_distance = min(
        enemies[i].pos.distance_to(enemies[j].pos)
        for i in range(len(enemies))
        for j in range(i + 1, len(enemies))
    )
    success = moved >= 6 and min_pair_distance > 8.0
    return success, f"moved={moved}/8, min_pair_distance={min_pair_distance:.1f}, progress_avg={sum(progresses)/len(progresses):.1f}"


def edge_corridor_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    obstacles = [
        RoomObstacle(
            pygame.Rect(arena.centerx - 72, arena.top + 114, 144, arena.height - 170),
            tag="wall",
        )
    ]
    layout = make_room_layout(arena, obstacles)
    enemy = make_enemy(arena.left + 126, arena.centery + 8)
    player = pygame.Vector2(arena.right - 126, arena.centery - 8)
    install_room(game, layout, [enemy], player)
    start_distance = enemy.pos.distance_to(player)
    history = simulate(game, 5.0, track=enemy)
    final_distance = enemy.pos.distance_to(player)
    progress = start_distance - final_distance
    used_edge = min(pos.y for pos in history) < arena.top + 150
    success = progress > 260.0 and used_edge
    return success, f"progress={progress:.1f}, used_edge={used_edge}, final=({enemy.pos.x:.1f},{enemy.pos.y:.1f})"


def boss_recovery_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    obstacles = [
        RoomObstacle(
            pygame.Rect(arena.centerx - 110, arena.centery - 54, 220, 108),
            tag="wall",
        ),
        RoomObstacle(
            pygame.Rect(arena.centerx - 18, arena.top + 130, 36, 120),
            tag="wall",
        ),
    ]
    layout = make_room_layout(arena, obstacles)
    enemy = make_enemy(
        arena.left + 220,
        arena.centery + 36,
        boss=True,
        variant="challenge",
    )
    player = pygame.Vector2(arena.right - 180, arena.centery - 48)
    install_room(game, layout, [enemy], player)
    start_distance = enemy.pos.distance_to(player)
    history = simulate(game, 6.0, track=enemy)
    final_distance = enemy.pos.distance_to(player)
    progress = start_distance - final_distance
    stalled = max_stall_frames(history, enemy.pos.copy(), 18.0)
    recovered = enemy.navigation.force_repath or enemy.navigation.route_mode in {
        "field",
        "anchor",
        "direct",
    }
    success = progress > 180.0 and recovered and enemy.action_state == ""
    return success, f"progress={progress:.1f}, route_mode={enemy.navigation.route_mode}, action={enemy.action_state!r}, final=({enemy.pos.x:.1f},{enemy.pos.y:.1f})"


def charger_dash_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    enemy = make_enemy(arena.centerx - 110, arena.centery, kind="charger")
    player = pygame.Vector2(arena.centerx + 12, arena.centery)
    install_room(game, layout, [enemy], player)
    game.floor_index = max(game.floor_index, config.CHARGER_TRUE_DASH_FLOOR)
    baseline = enemy.speed / config.FPS
    history = simulate(game, 0.45, track=enemy)
    step_distances = [
        history[idx].distance_to(history[idx - 1])
        for idx in range(1, len(history))
    ]
    peak_step = max(step_distances) if step_distances else 0.0
    dash_started = enemy.special_timer > 0
    success = dash_started and peak_step > baseline * 1.8
    return success, f"dash_started={dash_started}, peak_step={peak_step:.2f}, baseline={baseline:.2f}"


def standard_boss_phase_two_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    boss = make_enemy(arena.centerx - 170, arena.centery, boss=True)
    boss.hp = boss.max_hp * 0.45
    boss.shoot_timer = 0.0
    install_room(game, layout, [boss], pygame.Vector2(arena.centerx + 170, arena.centery))
    before_speed = boss.speed
    game.rng.seed(7)
    simulate(game, 4.0, track=boss)
    rocket_count = sum(1 for bullet in game.bullets if getattr(bullet, 'style', '') == 'rocket')
    speed_gain = boss.speed > before_speed
    success = boss.phase == 2 and speed_gain and rocket_count > 0
    return success, f"phase={boss.phase}, speed_gain={speed_gain}, rockets={rocket_count}"


def challenge_boss_phase_two_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    boss = make_enemy(arena.centerx - 150, arena.centery, boss=True, variant="challenge")
    boss.hp = boss.max_hp * 0.45
    boss.summon_timer = 0.0
    boss.alt_special_timer = 0.0
    install_room(game, layout, [boss], pygame.Vector2(arena.centerx + 180, arena.centery))
    before_speed = boss.speed
    simulate(game, 1.4, track=boss)
    minion_count = sum(1 for enemy in game.enemies if enemy is not boss and not enemy.is_boss)
    distance_ratio = game.current_challenge_boss_dash_distance(boss) / (config.CHALLENGE_BOSS_DASH_SPEED * config.CHALLENGE_BOSS_DASH_DURATION)
    speed_gain = boss.speed > before_speed
    success = boss.phase == 2 and speed_gain and minion_count > 0 and distance_ratio > 1.0
    return success, f"phase={boss.phase}, speed_gain={speed_gain}, minions={minion_count}, dash_ratio={distance_ratio:.2f}"


def shop_upgrade_logic_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    game.player_hp = game.player_max_hp * 0.28
    game.player_shield = 0.0
    game.floor_index = 6
    offers = game.build_shop_offers(layout, difficulty=2)
    offer_keys = [offer.key for offer in offers]
    upgrades = game.roll_upgrade_choices()
    upgrade_keys = [upgrade.key for upgrade in upgrades]
    unique_offers = len(set(offer_keys)) == len(offer_keys)
    unique_upgrades = len(set(upgrade_keys)) == len(upgrade_keys)
    has_sustain = any(key in {"repair", "shield_charge", "shield_core", "heal", "max_hp"} for key in offer_keys)
    success = len(offers) == min(5, len(offer_keys)) and unique_offers and unique_upgrades and has_sustain and 1 <= len(upgrades) <= 3
    return success, f"offers={offer_keys}, upgrades={upgrade_keys}"


def shop_purchase_limit_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    game.floor_index = 6
    offers = game.build_shop_offers(layout, difficulty=2)
    room_state = install_shop_room(game, layout, offers)
    game.credits = 999
    picks = room_state.shop_offers[:3]
    spent = 0
    for idx, offer in enumerate(picks):
        game.player_pos = offer.pos.copy()
        before = game.credits
        game.handle_interaction()
        if idx < config.SHOP_PURCHASE_LIMIT:
            spent += offer.cost
        elif game.credits != before:
            return False, f"third_purchase_spent={before - game.credits}"
    sold = sum(1 for offer in picks if offer.sold)
    success = (
        room_state.shop_purchases == config.SHOP_PURCHASE_LIMIT
        and sold == config.SHOP_PURCHASE_LIMIT
        and not picks[2].sold
        and game.credits == 999 - spent
    )
    return success, f"shop_purchases={room_state.shop_purchases}, sold={sold}, credits={game.credits}"


def engineer_shield_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    engineer = game.make_theme_enemy(arena, "engineer", min_distance=0.0)
    engineer.pos = pygame.Vector2(arena.centerx - 6, arena.centery)
    player = pygame.Vector2(arena.centerx + 4, arena.centery)
    install_room(game, layout, [engineer], player)
    game.player_shield = 40.0
    game.player_max_shield = 40.0
    game.player_hp = 100.0
    game.iframes = 0.0
    simulate(game, 0.1)
    shield_loss = 40.0 - game.player_shield
    success = shield_loss >= engineer.damage * 1.5
    return success, f"shield_loss={shield_loss:.1f}, engineer_damage={engineer.damage:.1f}, hp={game.player_hp:.1f}"


def turret_stationary_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    turret = game.make_theme_enemy(arena, "turret", min_distance=0.0)
    turret.pos = pygame.Vector2(arena.left + 180, arena.centery)
    start = turret.pos.copy()
    install_room(game, layout, [turret], pygame.Vector2(arena.right - 180, arena.centery))
    simulate(game, 2.0, track=turret)
    bullets = len(game.bullets)
    moved = turret.pos.distance_to(start)
    success = bullets > 0 and moved < 1.0
    return success, f"bullets={bullets}, moved={moved:.2f}"


def auto_aim_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    enemy_a = make_enemy(arena.centerx + 100, arena.centery - 10, kind="grunt")
    enemy_b = make_enemy(arena.centerx + 220, arena.centery + 120, kind="grunt")
    install_room(game, layout, [enemy_a, enemy_b], pygame.Vector2(arena.centerx - 120, arena.centery))
    game.selected_weapon = next(weapon for weapon in WEAPONS if weapon.key == "rocket")
    cursor = enemy_a.pos + pygame.Vector2(10, 4)
    target = game.find_auto_aim_enemy(cursor)
    success = target is enemy_a
    return success, f"target={(target.kind if target else None)}, target_pos=({target.pos.x:.1f},{target.pos.y:.1f})" if target else 'target=None'


def vanguard_shockwave_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    enemies = [
        make_enemy(arena.centerx + 120, arena.centery - 60, kind="grunt"),
        make_enemy(arena.centerx + 150, arena.centery + 70, kind="shooter"),
    ]
    install_room(game, layout, enemies, pygame.Vector2(arena.centerx - 120, arena.centery))
    game.selected_character = next(char for char in CHARACTERS if char.key == "vanguard")
    game.configure_character_skill("pulse")
    game.credits = config.VANGUARD_SHOCKWAVE_COST + 20
    game.skill_timer = 0.0
    game.vanguard_shockwave_used = False
    for direction in (pygame.Vector2(1, 0), pygame.Vector2(0, 1), pygame.Vector2(-1, 0)):
        game.spawn_projectile(
            game.player_pos + direction * 40,
            direction,
            8.0,
            speed=180.0,
            ttl=1.0,
            radius=6,
            friendly=False,
            color=config.BULLET_ENEMY_COLOR,
        )
    before_credits = game.credits
    ok = game.try_vanguard_shockwave()
    stunned = sum(1 for enemy in game.enemies if enemy.stun_timer >= config.VANGUARD_SHOCKWAVE_STUN - 0.05)
    enemy_bullets = sum(1 for bullet in game.bullets if not bullet.friendly)
    success = ok and game.vanguard_shockwave_used and game.credits == before_credits - config.VANGUARD_SHOCKWAVE_COST and stunned >= 1 and enemy_bullets == 0
    return success, f"used={game.vanguard_shockwave_used}, stunned={stunned}, enemy_bullets={enemy_bullets}, credits={game.credits}"


def elite_turret_event_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    turret = game.make_theme_enemy(arena, "elite_turret", min_distance=0.0)
    turret.pos = pygame.Vector2(arena.left + 180, arena.centery)
    install_room(game, layout, [turret], pygame.Vector2(arena.right - 180, arena.centery))
    simulate(game, 2.8, track=turret)
    rockets = [bullet for bullet in game.bullets if getattr(bullet, "style", "") == "rocket"]
    moved = turret.pos.distance_to(pygame.Vector2(arena.left + 180, arena.centery))
    homing = any(getattr(bullet, 'homing_strength', 0.0) > 0 for bullet in rockets)
    success = rockets and moved < 1.0 and homing
    return success, f"rockets={len(rockets)}, moved={moved:.2f}, homing={homing}"


def challenge_boss_skill_lock_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    boss = make_enemy(arena.centerx - 150, arena.centery, boss=True, variant="challenge")
    boss.phase = 2
    boss.hp = boss.max_hp * 0.45
    boss.shoot_timer = 0.22
    boss.summon_timer = 0.0
    boss.alt_special_timer = 0.0
    boss.special_timer = 0.0
    install_room(game, layout, [boss], pygame.Vector2(arena.centerx + 180, arena.centery))
    dt = 1.0 / config.FPS
    action_before_laser = False
    laser_fired = False
    for _ in range(int(1.0 * config.FPS)):
        game.update_enemies(dt)
        if not laser_fired and boss.action_state:
            action_before_laser = True
        if game.laser_traces:
            laser_fired = True
            break
    minions = sum(1 for enemy in game.enemies if enemy is not boss and not enemy.is_boss)
    success = laser_fired and not action_before_laser and minions == 0
    return success, f"laser_fired={laser_fired}, action_before_laser={action_before_laser}, minions={minions}"


def boss_hp_scaling_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    game.room_index = 6
    game.floor_index = 3
    boss_floor_three = game.make_boss(arena)
    floor_three_base = enemy_scaling(game.room_index, game.floor_index)[0]
    game.floor_index = 4
    boss_floor_four = game.make_boss(arena)
    floor_four_base = enemy_scaling(game.room_index, game.floor_index)[0]
    actual_ratio = boss_floor_four.max_hp / max(1.0, boss_floor_three.max_hp)
    base_ratio = floor_four_base / max(0.01, floor_three_base)
    success = actual_ratio > base_ratio * 1.08
    return success, f"hp3={boss_floor_three.max_hp:.1f}, hp4={boss_floor_four.max_hp:.1f}, actual_ratio={actual_ratio:.3f}, base_ratio={base_ratio:.3f}"


def weapon_tuning_scenario(game: Game) -> tuple[bool, str]:
    rail = next(weapon for weapon in WEAPONS if weapon.key == "rail")
    shotgun = next(weapon for weapon in WEAPONS if weapon.key == "shotgun")

    game.selected_character = CHARACTERS[0]
    game.selected_weapon = rail
    game.restart_run()
    game.apply_selected_loadout()
    rail_damage = game.player_damage
    rail_cooldown = game.fire_cooldown
    rail_speed = game.player_projectile_speed
    rail_ok = (
        math.isclose(rail_damage, config.RAIL_BASE_DAMAGE)
        and math.isclose(rail_cooldown, config.RAIL_FIRE_COOLDOWN)
        and math.isclose(
            rail_speed,
            config.BULLET_SPEED * config.RAIL_PROJECTILE_SPEED_SCALE,
        )
    )

    game.selected_weapon = shotgun
    game.restart_run()
    game.apply_selected_loadout()
    shotgun_pellets = game.player_shotgun_pellets
    shotgun_ttl = game.player_projectile_ttl
    shotgun_spread = game.player_shotgun_spread
    shotgun_ok = (
        shotgun_pellets == config.SHOTGUN_BASE_PELLETS
        and math.isclose(shotgun_ttl, config.SHOTGUN_BASE_TTL)
        and math.isclose(shotgun_spread, config.SHOTGUN_BASE_SPREAD)
    )
    success = rail_ok and shotgun_ok
    return success, (
        f"rail=({rail_damage:.1f},{rail_cooldown:.2f},{rail_speed:.1f}), "
        f"shotgun=(pellets={shotgun_pellets}, ttl={shotgun_ttl:.2f}, spread={shotgun_spread:.2f})"
    )


def upgrade_conversion_scenario(game: Game) -> tuple[bool, str]:
    game.restart_run()
    game.active_skill_key = "basketball"
    basketball_damage = game.basketball_damage
    basketball_radius = game.basketball_radius
    basketball_speed = game.basketball_speed_scale
    game.apply_upgrade(Upgrade("basketball_training", "篮球实习生", ""))
    basketball_ok = (
        math.isclose(game.basketball_damage, basketball_damage)
        and math.isclose(
            game.basketball_radius,
            basketball_radius + config.BASKETBALL_UPGRADE_RADIUS_STEP,
        )
        and math.isclose(
            game.basketball_speed_scale,
            basketball_speed * config.BASKETBALL_UPGRADE_SPEED_MULTIPLIER,
        )
    )

    game.active_skill_key = "mamba_smash"
    mamba_damage = game.mamba_skill_damage
    mamba_stun = game.mamba_skill_stun_duration
    mamba_angle = game.mamba_skill_half_angle
    game.apply_upgrade(Upgrade("what_can_i_say", "what can i say", ""))
    mamba_ok = (
        math.isclose(game.mamba_skill_damage, mamba_damage)
        and math.isclose(
            game.mamba_skill_stun_duration,
            mamba_stun + config.MAMBA_UPGRADE_STUN_STEP,
        )
        and math.isclose(
            game.mamba_skill_half_angle,
            mamba_angle + config.MAMBA_UPGRADE_HALF_ANGLE_STEP,
        )
    )

    game.player_max_hp = 100.0
    game.player_hp = 50.0
    game.apply_upgrade(Upgrade("max_hp", "强化核心", ""))
    max_hp_ok = math.isclose(game.player_max_hp, 110.0) and math.isclose(
        game.player_hp, 60.0
    )

    game.player_max_hp = 120.0
    game.player_hp = 30.0
    game.apply_upgrade(Upgrade("heal", "战地修补", ""))
    heal_ok = math.isclose(game.player_hp, 66.0)

    game.player_max_shield = 80.0
    game.player_shield = 10.0
    game.apply_upgrade(Upgrade("shield_core", "相位护盾", ""))
    shield_ok = math.isclose(game.player_max_shield, 88.0) and math.isclose(
        game.player_shield, 34.0
    )

    success = basketball_ok and mamba_ok and max_hp_ok and heal_ok and shield_ok
    return success, (
        f"basketball_radius={game.basketball_radius:.1f}, "
        f"mamba_stun={game.mamba_skill_stun_duration:.2f}, "
        f"hp={game.player_hp:.1f}/{game.player_max_hp:.1f}, "
        f"shield={game.player_shield:.1f}/{game.player_max_shield:.1f}"
    )


def enemy_resistance_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    turret = game.make_theme_enemy(arena, "turret", min_distance=0.0)
    turret.pos = pygame.Vector2(arena.left + 170, arena.centery - 120)
    boss = make_enemy(arena.centerx, arena.centery, boss=True)
    grunt = make_enemy(arena.right - 180, arena.centery + 90)
    install_room(
        game,
        layout,
        [turret, boss, grunt],
        pygame.Vector2(arena.centerx, arena.bottom - 140),
    )

    turret_start = turret.pos.copy()
    boss_start = boss.pos.copy()
    grunt_start = grunt.pos.copy()
    game.apply_enemy_knockback(turret, pygame.Vector2(80, 0))
    game.apply_enemy_knockback(boss, pygame.Vector2(80, 0))
    game.apply_enemy_knockback(grunt, pygame.Vector2(80, 0))
    turret_move = turret.pos.distance_to(turret_start)
    boss_move = boss.pos.distance_to(boss_start)
    grunt_move = grunt.pos.distance_to(grunt_start)
    boss_stun = game.apply_enemy_stun(boss, 1.0)
    grunt_stun = game.apply_enemy_stun(grunt, 1.0)
    success = (
        turret_move < 0.1
        and boss_move < grunt_move
        and boss_stun < grunt_stun
    )
    return success, (
        f"turret_move={turret_move:.2f}, boss_move={boss_move:.2f}, "
        f"grunt_move={grunt_move:.2f}, boss_stun={boss_stun:.2f}, grunt_stun={grunt_stun:.2f}"
    )


def maze_backtrack_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    maze_layout = build_maze_room_layout(
        arena,
        room_index=4,
        rng=random.Random(11),
        door_dirs=("west", "east"),
    )
    start_layout = make_room_layout(arena, [])
    exit_layout = make_room_layout(arena, [])
    start_room = RoomState(
        room_id=7001,
        coord=(0, 0),
        room_type="start",
        difficulty=1,
        neighbors={"east": 7002},
        layout=start_layout,
        visited=True,
        resolved=True,
    )
    maze_room = RoomState(
        room_id=7002,
        coord=(1, 0),
        room_type="maze",
        difficulty=4,
        neighbors={"west": 7001, "east": 7003},
        layout=maze_layout,
        visited=True,
        resolved=False,
    )
    maze_room.enemies = [make_enemy(arena.centerx + 120, arena.centery)]
    exit_room = RoomState(
        room_id=7003,
        coord=(2, 0),
        room_type="combat",
        difficulty=1,
        neighbors={"west": 7002},
        layout=exit_layout,
        visited=True,
        resolved=True,
    )
    game.room_states = {
        start_room.room_id: start_room,
        maze_room.room_id: maze_room,
        exit_room.room_id: exit_room,
    }
    game.enter_room(maze_room.room_id, "west")
    room = game.current_room_state
    assert room is not None
    retreat_open = not game.is_door_locked(room, "west")
    forward_locked = game.is_door_locked(room, "east")
    destructible = sum(1 for obstacle in maze_layout.obstacles if obstacle.destructible)
    thin_walls = any(
        obstacle.tag == "wall"
        and max(obstacle.rect.width, obstacle.rect.height) <= 80
        and min(obstacle.rect.width, obstacle.rect.height) < 40
        for obstacle in maze_layout.obstacles
    )
    game.room_transition_cooldown = 0.0
    game.player_pos = pygame.Vector2(maze_layout.screen_doors["west"].center)
    game.check_door_transition()
    backtracked = game.current_room_id == start_room.room_id
    success = retreat_open and forward_locked and destructible > 0 and thin_walls and backtracked
    return success, (
        f"retreat_open={retreat_open}, forward_locked={forward_locked}, "
        f"destructible={destructible}, thin_walls={thin_walls}, backtracked={backtracked}"
    )


def regression_scenario(game: Game) -> tuple[bool, str]:
    arena = game.arena_rect()
    layout = make_room_layout(arena, [])
    enemies = [
        make_enemy(arena.left + 180, arena.centery - 120, kind="shooter"),
        make_enemy(arena.left + 220, arena.centery + 120, kind="laser"),
        make_enemy(arena.left + 280, arena.centery - 40, kind="shotgunner"),
        make_enemy(arena.left + 320, arena.centery + 40, kind="elite"),
        make_enemy(arena.centerx - 40, arena.centery - 140, boss=True, variant=""),
        make_enemy(arena.centerx - 10, arena.centery + 140, boss=True, variant="challenge"),
    ]
    player = pygame.Vector2(arena.right - 220, arena.centery)
    install_room(game, layout, enemies, player)
    simulate(game, 3.2)
    fired = len(game.bullets)
    traced = len(game.laser_traces)
    active_actions = sum(1 for enemy in enemies if enemy.action_state)
    success = fired > 0 and traced > 0 and all(enemy.hp > 0 for enemy in enemies)
    return success, f"bullets={fired}, laser_traces={traced}, active_actions={active_actions}"


def main() -> int:
    pygame.init()
    game = Game()
    checks = [
        ("wall_gap", wall_gap_scenario),
        ("obstacle_detour", obstacle_detour_scenario),
        ("edge_corridor", edge_corridor_scenario),
        ("multi_enemy", multi_enemy_scenario),
        ("boss_recovery", boss_recovery_scenario),
        ("charger_dash", charger_dash_scenario),
        ("boss_phase_two_standard", standard_boss_phase_two_scenario),
        ("boss_phase_two_challenge", challenge_boss_phase_two_scenario),
        ("shop_upgrade_logic", shop_upgrade_logic_scenario),
        ("shop_purchase_limit", shop_purchase_limit_scenario),
        ("engineer_shield", engineer_shield_scenario),
        ("turret_stationary", turret_stationary_scenario),
        ("auto_aim", auto_aim_scenario),
        ("vanguard_shockwave", vanguard_shockwave_scenario),
        ("elite_turret_event", elite_turret_event_scenario),
        ("challenge_boss_skill_lock", challenge_boss_skill_lock_scenario),
        ("boss_hp_scaling", boss_hp_scaling_scenario),
        ("weapon_tuning", weapon_tuning_scenario),
        ("upgrade_conversion", upgrade_conversion_scenario),
        ("enemy_resistance", enemy_resistance_scenario),
        ("maze_backtrack", maze_backtrack_scenario),
        ("boss_skill_regression", regression_scenario),
    ]
    failures = []
    for name, fn in checks:
        try:
            ok, detail = fn(game)
        except Exception as exc:  # pragma: no cover - smoke harness
            ok = False
            detail = f"exception={exc!r}"
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")
        if not ok:
            failures.append(name)
    pygame.quit()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
