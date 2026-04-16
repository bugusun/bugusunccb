from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from . import config
from .balance import SHOP_OFFER_POOL, enemy_credit_drop, enemy_scaling, hazard_profile, obstacle_credit_drop, reward_credit_drop, scale_shop_cost
from .content import (
    CHARACTERS,
    STAGES,
    SUPPLY_OPTIONS,
    TITLE_PANEL_INFO,
    TITLE_SKILLS,
    UPGRADE_KEYS,
    UPGRADES,
    WEAPONS,
    CharacterOption,
    StageOption,
    SupplyOption,
    Upgrade,
    WeaponOption,
)
from .entities import Bullet, Enemy, ExplosionWave, FloatingText, GasCloud, LaserTrace, Particle, Pickup
from .map_system import FloorMap, FloorRoom, OPPOSITE_DIRECTIONS, RoomLayout, RoomObstacle, build_floor_map, build_stitched_layout


@dataclass
class ShopOffer:
    key: str
    name: str
    description: str
    cost: int
    pos: pygame.Vector2
    sold: bool = False


@dataclass
class RoomState:
    room_id: int
    coord: tuple[int, int]
    room_type: str
    difficulty: int
    neighbors: dict[str, int]
    layout: RoomLayout
    visited: bool = False
    resolved: bool = False
    encounter_spawned: bool = False
    doors_locked: bool = False
    chest_opened: bool = False
    exit_active: bool = False
    feature_anchor: pygame.Vector2 | None = None
    enemies: list[Enemy] = field(default_factory=list)
    pickups: list[Pickup] = field(default_factory=list)
    shop_offers: list[ShopOffer] = field(default_factory=list)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("钢铁蜂巢")
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"], 19)
        self.small_font = pygame.font.SysFont(["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"], 15)
        self.big_font = pygame.font.SysFont(["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"], 34, bold=True)
        self.rng = random.Random()
        self.running = True
        self.selected_stage = STAGES[0]
        self.selected_character = CHARACTERS[0]
        self.selected_weapon = WEAPONS[0]
        self.title_panel = "main"
        self.record_path = Path(__file__).resolve().parents[1] / "highscore.json"
        self.best_record = self.load_best_record()
        self.restart_run()

    def restart_run(self) -> None:
        self.player_pos = pygame.Vector2(config.WIDTH / 2, config.HEIGHT / 2)
        self.player_hp = float(config.PLAYER_BASE_HP)
        self.player_max_hp = float(config.PLAYER_BASE_HP)
        self.player_shield = 0.0
        self.player_max_shield = 60.0
        self.player_speed = float(config.PLAYER_BASE_SPEED)
        self.player_damage = float(config.BASE_DAMAGE)
        self.fire_cooldown = float(config.BASE_FIRE_COOLDOWN)
        self.fire_timer = 0.0
        self.bullet_pierce = 0
        self.multishot = 0
        self.player_bullet_bounces = 0
        self.player_spread = 0.018
        self.player_crit_chance = 0.08
        self.player_crit_multiplier = 1.75
        self.weapon_mode = "projectile"
        self.player_beam_width = 10
        self.player_beam_color = config.BULLET_COLOR
        self.pickup_radius = 72.0
        self.credit_gain_multiplier = 1.0
        self.enemy_bullet_speed_multiplier = 1.0
        self.dash_distance = float(config.DASH_DISTANCE)
        self.dash_cooldown = float(config.DASH_COOLDOWN)
        self.dash_timer = 0.0
        self.pulse_damage = float(config.PULSE_DAMAGE)
        self.pulse_radius = float(config.PULSE_RADIUS)
        self.pulse_cooldown = float(config.PULSE_COOLDOWN)
        self.pulse_timer = 0.0
        self.iframes = 0.0
        self.last_move = pygame.Vector2(1, 0)

        self.level = 1
        self.xp = 0
        self.xp_to_level = 30
        self.room_index = 1
        self.base_progress = 1
        self.floor_index = 1
        self.kills = 0
        self.rooms_cleared = 0
        self.credits = 0
        self.room_transition_cooldown = 0.0
        self.reward_source: str | None = None
        self.current_room_id: int | None = None
        self.current_room_state: RoomState | None = None
        self.floor_map: FloorMap | None = None
        self.room_states: dict[int, RoomState] = {}

        self.bullets: list[Bullet] = []
        self.enemies: list[Enemy] = []
        self.pickups: list[Pickup] = []
        self.floaters: list[FloatingText] = []
        self.particles: list[Particle] = []
        self.laser_traces: list[LaserTrace] = []
        self.explosion_waves: list[ExplosionWave] = []
        self.gas_clouds: list[GasCloud] = []
        self.obstacles: list[RoomObstacle] = []
        self.room_layout: RoomLayout | None = None
        self.room_clear_delay = 0.0
        self.mode = "title"
        self.upgrade_choices: list[Upgrade] = []
        self.reward_choices: list[Upgrade] = []
        self.supply_choices: list[SupplyOption] = list(SUPPLY_OPTIONS)
        self.current_score = 0
        self.message = "选择关卡、机体与武器，准备下潜钢铁蜂巢"

    def arena_rect(self) -> pygame.Rect:
        return pygame.Rect(
            config.ARENA_MARGIN,
            config.ARENA_MARGIN,
            config.ARENA_WIDTH,
            config.ARENA_HEIGHT,
        )

    def obstacle_rects(self) -> list[pygame.Rect]:
        return [obstacle.rect for obstacle in self.obstacles]

    def load_best_record(self) -> dict[str, int]:
        default = {"best_score": 0, "best_floor": 0, "best_rooms": 0}
        try:
            if self.record_path.exists():
                data = json.loads(self.record_path.read_text(encoding="utf-8"))
                return {
                    "best_score": int(data.get("best_score", 0)),
                    "best_floor": int(data.get("best_floor", 0)),
                    "best_rooms": int(data.get("best_rooms", 0)),
                }
        except (OSError, ValueError, TypeError):
            pass
        return default

    def save_best_record(self) -> None:
        try:
            self.record_path.write_text(json.dumps(self.best_record, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def calculate_score(self) -> int:
        return int(self.rooms_cleared * 70 + self.kills * 8 + self.level * 45 + self.floor_index * 120 + self.credits * 2)

    def update_best_record(self) -> None:
        self.current_score = self.calculate_score()
        changed = False
        if self.current_score > self.best_record["best_score"]:
            self.best_record["best_score"] = self.current_score
            changed = True
        if self.floor_index > self.best_record["best_floor"]:
            self.best_record["best_floor"] = self.floor_index
            changed = True
        if self.rooms_cleared > self.best_record["best_rooms"]:
            self.best_record["best_rooms"] = self.rooms_cleared
            changed = True
        if changed:
            self.save_best_record()

    def wrap_text(self, text: str, font: pygame.font.Font, max_width: int, max_lines: int | None = None) -> list[str]:
        if not text:
            return [""]
        segments = text.split() if " " in text else list(text)
        lines: list[str] = []
        current = segments[0]
        separator = " " if " " in text else ""
        for word in segments[1:]:
            trial = f"{current}{separator}{word}" if separator else f"{current}{word}"
            if font.size(trial)[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        if max_lines is not None and len(lines) > max_lines:
            trimmed = lines[:max_lines]
            while trimmed and font.size(trimmed[-1] + "...")[0] > max_width:
                trimmed[-1] = trimmed[-1][:-1]
                if not trimmed[-1]:
                    break
            trimmed[-1] = (trimmed[-1] or "").rstrip() + "..."
            return trimmed
        return lines

    def spawn_particles(
        self,
        pos: pygame.Vector2,
        color: tuple[int, int, int],
        count: int,
        speed_scale: float = 1.0,
        radius_range: tuple[float, float] = (2.0, 4.5),
        ttl_range: tuple[float, float] = (0.18, 0.45),
    ) -> None:
        for _ in range(count):
            direction = pygame.Vector2(self.rng.uniform(-1.0, 1.0), self.rng.uniform(-1.0, 1.0))
            if direction.length_squared() <= 0:
                direction = pygame.Vector2(1, 0)
            velocity = direction.normalize() * self.rng.uniform(config.PARTICLE_SPEED * 0.35, config.PARTICLE_SPEED * speed_scale)
            self.particles.append(
                Particle(
                    pos=pos.copy(),
                    velocity=velocity,
                    color=color,
                    radius=self.rng.uniform(*radius_range),
                    ttl=self.rng.uniform(*ttl_range),
                )
            )

    def update_particles(self, dt: float) -> None:
        remaining: list[Particle] = []
        for particle in self.particles:
            particle.pos += particle.velocity * dt
            particle.velocity *= max(0.0, 1.0 - (1.0 - config.PARTICLE_FRICTION) * 60 * dt)
            particle.ttl -= dt
            particle.radius = max(0.5, particle.radius - dt * 3.8)
            if particle.ttl > 0:
                remaining.append(particle)
        self.particles = remaining

    def update_gas_clouds(self, dt: float) -> None:
        remaining: list[GasCloud] = []
        for cloud in self.gas_clouds:
            cloud.ttl -= dt
            cloud.tick_timer -= dt
            if cloud.tick_timer <= 0:
                cloud.tick_timer = 0.35
                for enemy in self.enemies[:]:
                    if enemy.pos.distance_to(cloud.pos) <= cloud.radius + enemy.radius:
                        enemy.hp -= cloud.damage
                        self.floaters.append(FloatingText(enemy.pos.copy(), str(int(cloud.damage)), (148, 220, 118), 0.28))
                        if enemy.hp <= 0:
                            self.kill_enemy(enemy)
                if self.player_pos.distance_to(cloud.pos) <= cloud.radius + config.PLAYER_RADIUS and self.iframes <= 0:
                    self.damage_player(cloud.damage * 0.78, (148, 220, 118), 0.12)
            if cloud.ttl > 0:
                remaining.append(cloud)
        self.gas_clouds = remaining

    def update_explosion_waves(self, dt: float) -> None:
        remaining: list[ExplosionWave] = []
        for wave in self.explosion_waves:
            wave.ttl -= dt
            if wave.ttl > 0:
                remaining.append(wave)
        self.explosion_waves = remaining

    def get_enemy_avoidance(self, enemy: Enemy) -> pygame.Vector2:
        avoid = pygame.Vector2()
        for obstacle in self.obstacles:
            rect = obstacle.rect.inflate(40, 40)
            if not rect.collidepoint(enemy.pos.x, enemy.pos.y):
                continue
            center = pygame.Vector2(rect.center)
            delta = enemy.pos - center
            if delta.length_squared() > 0:
                weight = 1.0 if getattr(obstacle, "tag", "normal") == "wall" else 0.78
                avoid += delta.normalize() * weight
        for other in self.enemies:
            if other is enemy:
                continue
            delta = enemy.pos - other.pos
            dist_sq = delta.length_squared()
            if 0 < dist_sq < 52 * 52:
                avoid += delta.normalize() * (52 / max(12, dist_sq ** 0.5))
        return avoid

    def start_run(self, start_room: int | None = None) -> None:
        self.restart_run()
        self.apply_selected_loadout()
        self.base_progress = start_room or 1
        self.room_index = self.base_progress
        self.rooms_cleared = max(0, self.base_progress - 1)
        self.mode = "playing"
        self.title_panel = "main"
        self.build_floor()

    def apply_selected_loadout(self) -> None:
        if self.selected_character.key == "vanguard":
            self.player_max_hp += 18
            self.player_hp = self.player_max_hp
            self.player_max_shield += 18
            self.player_shield = min(self.player_max_shield, self.player_shield + 18)
            self.dash_cooldown *= 0.96
        elif self.selected_character.key == "ranger":
            self.player_speed += 28
            self.pickup_radius += 30
            self.dash_distance += 16
        elif self.selected_character.key == "engineer":
            self.pulse_cooldown *= 0.88
            self.pulse_damage += 8
            self.credits += 12

        self.weapon_mode = "projectile"
        self.player_beam_width = 10
        self.player_beam_color = config.BULLET_COLOR
        self.player_spread = 0.018
        self.player_crit_chance = 0.08
        self.player_crit_multiplier = 1.75
        if self.selected_weapon.key == "scatter":
            self.player_damage = 9.0
            self.fire_cooldown = 0.09
            self.player_spread = 0.085
            self.player_crit_chance = 0.05
            self.player_crit_multiplier = 1.55
        elif self.selected_weapon.key == "rail":
            self.player_damage = 36.0
            self.fire_cooldown = 0.52
            self.player_spread = 0.006
            self.player_crit_chance = 0.24
            self.player_crit_multiplier = 2.30
            self.bullet_pierce += 1
        elif self.selected_weapon.key == "laser_burst":
            self.weapon_mode = "laser"
            self.player_damage = 6.0
            self.fire_cooldown = 0.11
            self.player_beam_width = 12
            self.player_beam_color = config.LASER_LIGHT_COLOR
            self.player_crit_chance = 0.06
            self.player_crit_multiplier = 1.55
        elif self.selected_weapon.key == "laser_lance":
            self.weapon_mode = "laser"
            self.player_damage = 21.0
            self.fire_cooldown = 0.36
            self.player_beam_width = 18
            self.player_beam_color = config.LASER_HEAVY_COLOR
            self.player_crit_chance = 0.16
            self.player_crit_multiplier = 2.05
        else:
            self.player_damage += 2

    def build_floor(self) -> None:
        arena = self.arena_rect()
        base_difficulty = self.base_progress + (self.floor_index - 1) * 3
        self.floor_map = build_floor_map(arena, self.floor_index, base_difficulty, self.rng)
        self.room_states = {
            room_id: self.make_room_state(room_def)
            for room_id, room_def in self.floor_map.rooms.items()
        }
        self.bullets.clear()
        self.laser_traces.clear()
        self.explosion_waves.clear()
        self.floaters.clear()
        self.message = f"进入第 {self.floor_index} 层"
        if self.floor_map is None:
            return
        self.enter_room(self.floor_map.start_room_id, None)

    def make_room_state(self, room_def: FloorRoom) -> RoomState:
        state = RoomState(
            room_id=room_def.room_id,
            coord=room_def.coord,
            room_type=room_def.room_type,
            difficulty=room_def.difficulty,
            neighbors=dict(room_def.neighbors),
            layout=room_def.layout,
        )
        if room_def.room_type == "start":
            state.resolved = True
        elif room_def.room_type == "shop":
            state.resolved = True
            state.shop_offers = self.build_shop_offers(room_def.layout, room_def.difficulty)
        elif room_def.room_type in {"treasure", "boss"}:
            anchors = self.get_room_feature_points(room_def.layout, 1, collision_radius=40)
            if anchors:
                state.feature_anchor = anchors[0]
        return state

    def spawn_room(self) -> None:
        if self.floor_map is None:
            self.build_floor()
            return
        if self.current_room_id is not None:
            self.enter_room(self.current_room_id, None)

    def enter_room(self, room_id: int, entry_from: str | None) -> None:
        room_state = self.room_states[room_id]
        self.current_room_id = room_id
        self.current_room_state = room_state
        self.room_layout = room_state.layout
        self.obstacles = list(room_state.layout.obstacles)
        self.enemies = room_state.enemies
        self.pickups = room_state.pickups
        self.bullets.clear()
        self.laser_traces.clear()
        self.explosion_waves.clear()
        self.room_clear_delay = 0.0
        self.room_transition_cooldown = 0.45
        self.room_index = room_state.difficulty

        arena = self.arena_rect()
        if entry_from and self.room_layout is not None and entry_from in self.room_layout.door_entries:
            self.player_pos = self.room_layout.door_entries[entry_from].copy()
        else:
            self.player_pos = self.find_safe_spawn_position(arena)

        if not room_state.visited:
            room_state.visited = True
            self.prepare_room_state(room_state)
        else:
            if room_state.room_type in ("combat", "elite", "boss") and not room_state.resolved:
                room_state.doors_locked = bool(room_state.enemies)
            self.message = f"第 {self.floor_index} 层 · {self.room_type_label(room_state.room_type)}"

    def prepare_room_state(self, room_state: RoomState) -> None:
        arena = self.arena_rect()
        room_state.doors_locked = False
        if room_state.room_type == "start":
            self.message = f"第 {self.floor_index} 层起始间"
            return
        if room_state.room_type == "shop":
            self.message = f"第 {self.floor_index} 层 · 商店房"
            return
        if room_state.room_type == "treasure":
            self.message = f"第 {self.floor_index} 层 · 宝箱房"
            return

        room_state.encounter_spawned = True
        room_state.resolved = False
        room_state.doors_locked = True
        self.spawn_room_pickups(arena)
        self.populate_room_enemies(room_state, arena)
        self.message = f"第 {self.floor_index} 层 · {self.room_type_label(room_state.room_type)}"

    def populate_room_enemies(self, room_state: RoomState, arena: pygame.Rect) -> None:
        room_state.enemies.clear()
        theme = room_state.layout.theme
        shooter_cap = 1 if room_state.difficulty <= 5 else 2
        if theme == "反应堆室":
            shooter_cap += 1
        shooter_count = 0
        if room_state.room_type == "combat":
            count = 4 + room_state.difficulty * 2
            if theme == "开阔车间":
                count += 1
            elif theme == "封锁壁垒":
                count = max(4, count - 1)
            for _ in range(count):
                enemy = self.make_enemy(arena)
                shooter_count = self.limit_shooter(enemy, shooter_count, shooter_cap)
                room_state.enemies.append(enemy)
            return

        if room_state.room_type == "elite":
            count = 3 + room_state.difficulty
            if theme == "废料堆场":
                count += 1
            for idx in range(count):
                enemy = self.make_enemy(arena)
                if idx < 2:
                    self.promote_elite_enemy(enemy)
                shooter_count = self.limit_shooter(enemy, shooter_count, max(1, shooter_cap))
                room_state.enemies.append(enemy)
            return

        if room_state.room_type == "boss":
            room_state.enemies.append(self.make_boss(arena))
            add_count = 2 + max(0, room_state.difficulty // 3)
            if theme == "封锁壁垒":
                add_count += 1
            for idx in range(add_count):
                enemy = self.make_enemy(arena)
                if idx == 0 and enemy.kind == "grunt":
                    self.promote_elite_enemy(enemy)
                shooter_count = self.limit_shooter(enemy, shooter_count, max(1, shooter_cap))
                room_state.enemies.append(enemy)

    def limit_shooter(self, enemy: Enemy, shooter_count: int, shooter_cap: int) -> int:
        if enemy.kind not in {"shooter", "laser"}:
            return shooter_count
        if shooter_count >= shooter_cap:
            if enemy.kind == "laser":
                enemy.kind = "shooter"
                enemy.color = config.SHOOTER_COLOR
                enemy.speed *= 1.04
                enemy.damage *= 0.82
                enemy.max_hp *= 0.95
                enemy.hp = min(enemy.hp, enemy.max_hp)
                enemy.shoot_cooldown = max(1.0, enemy.shoot_cooldown * 0.78)
                enemy.shoot_timer = self.rng.random() * enemy.shoot_cooldown
                enemy.aim_direction = pygame.Vector2()
                return shooter_count
            enemy.kind = "grunt"
            enemy.color = config.ENEMY_COLOR
            enemy.speed *= 1.05
            enemy.damage *= 1.05
            enemy.shoot_cooldown = 0.0
            enemy.shoot_timer = 0.0
            enemy.aim_direction = pygame.Vector2()
            return shooter_count
        return shooter_count + 1

    def promote_elite_enemy(self, enemy: Enemy) -> None:
        enemy.kind = "elite"
        enemy.color = config.ELITE_COLOR
        enemy.speed *= 1.06
        enemy.damage *= 1.18
        enemy.radius = max(enemy.radius, config.ENEMY_RADIUS + 4)
        enemy.knockback_resist = max(enemy.knockback_resist, 1.8)
        enemy.max_hp *= 1.6
        enemy.hp = enemy.max_hp
        enemy.xp_reward += 10
        if enemy.shoot_cooldown <= 0:
            enemy.shoot_cooldown = max(0.95, 1.48 - self.room_index * 0.02 - max(0, self.floor_index - 1) * 0.04)
            enemy.shoot_timer = self.rng.random() * enemy.shoot_cooldown

    def build_room_layout(self, arena: pygame.Rect) -> RoomLayout:
        return build_stitched_layout(arena, self.room_index, self.rng)

    def find_safe_spawn_position(self, arena: pygame.Rect) -> pygame.Vector2:
        candidates: list[pygame.Vector2] = []
        if self.room_layout is not None:
            candidates.append(self.room_layout.player_spawn.copy())
            for chamber in self.room_layout.chambers.values():
                candidates.append(chamber.center.copy())
        candidates.extend(
            [
                pygame.Vector2(arena.center),
                pygame.Vector2(arena.centerx, arena.centery - 120),
                pygame.Vector2(arena.centerx, arena.centery + 120),
                pygame.Vector2(arena.centerx - 140, arena.centery),
                pygame.Vector2(arena.centerx + 140, arena.centery),
            ]
        )
        for pos in candidates:
            if not any(self.circle_intersects_rect(pos, config.PLAYER_RADIUS, rect) for rect in self.obstacle_rects()):
                return pos
        return self.random_free_position(arena, config.PLAYER_RADIUS + 8)

    def spawn_room_pickups(self, arena: pygame.Rect) -> None:
        for _ in range(self.rng.randint(0, 2)):
            if self.room_layout is not None:
                pos = self.random_free_position(
                    arena,
                    20,
                    allowed_cells=self.room_layout.pickup_cells,
                    min_distance=96,
                )
            else:
                pos = self.random_free_position(arena, 20)
            roll = self.rng.random()
            if roll < 0.45:
                self.pickups.append(Pickup(pos, 25, config.HEAL_PICKUP_RADIUS, "heal", config.HEAL_COLOR, "血包"))
            elif roll < 0.70:
                self.pickups.append(Pickup(pos, 22, config.ITEM_PICKUP_RADIUS, "shield", config.SHIELD_COLOR, "护盾"))
            else:
                self.pickups.append(Pickup(pos, 1, config.ITEM_PICKUP_RADIUS, "item", config.ITEM_COLOR, "道具"))

    def random_free_position(
        self,
        arena: pygame.Rect,
        radius: int,
        allowed_cells: tuple[tuple[int, int], ...] | list[tuple[int, int]] | None = None,
        min_distance: float = 120,
    ) -> pygame.Vector2:
        if self.room_layout is not None:
            for _ in range(32):
                pos = self.room_layout.sample_point(
                    self.rng,
                    allowed_cells,
                    margin=radius + 12,
                    avoid=self.player_pos,
                    min_distance=min_distance,
                )
                if any(self.circle_intersects_rect(pos, radius, rect) for rect in self.obstacle_rects()):
                    continue
                return pos
        for _ in range(40):
            pos = pygame.Vector2(
                self.rng.randint(arena.left + radius, arena.right - radius),
                self.rng.randint(arena.top + radius, arena.bottom - radius),
            )
            if pos.distance_to(self.player_pos) < min_distance:
                continue
            if any(self.circle_intersects_rect(pos, radius, rect) for rect in self.obstacle_rects()):
                continue
            return pos
        fallback = pygame.Vector2(arena.center)
        if any(self.circle_intersects_rect(fallback, radius, rect) for rect in self.obstacle_rects()):
            fallback = pygame.Vector2(arena.centerx, arena.centery + 140)
        return fallback

    def room_type_label(self, room_type: str) -> str:
        labels = {
            "start": "起始间",
            "combat": "战斗间",
            "elite": "精英间",
            "shop": "商店房",
            "treasure": "宝箱房",
            "boss": "首领房",
        }
        return labels.get(room_type, "战斗区")

    def is_safe_feature_position(
        self,
        pos: pygame.Vector2,
        obstacles: list[RoomObstacle],
        radius: int,
    ) -> bool:
        arena = self.arena_rect().inflate(-radius * 2, -radius * 2)
        if not arena.collidepoint(pos.x, pos.y):
            return False
        return not any(self.circle_intersects_rect(pos, radius, obstacle.rect) for obstacle in obstacles)

    def build_feature_anchor_candidates(self, layout: RoomLayout) -> list[pygame.Vector2]:
        arena = self.arena_rect()
        chambers = sorted(
            layout.chambers.values(),
            key=lambda chamber: (abs(chamber.center.y - arena.centery), chamber.center.x),
        )
        candidates = [chamber.center.copy() for chamber in chambers]
        candidates.extend(
            [
                pygame.Vector2(arena.center),
                pygame.Vector2(arena.centerx - 180, arena.centery),
                pygame.Vector2(arena.centerx + 180, arena.centery),
                pygame.Vector2(arena.centerx, arena.centery - 120),
                pygame.Vector2(arena.centerx, arena.centery + 120),
            ]
        )
        return candidates

    def get_room_feature_points(self, layout: RoomLayout, count: int, collision_radius: int = 26) -> list[pygame.Vector2]:
        points: list[pygame.Vector2] = []
        for candidate in self.build_feature_anchor_candidates(layout):
            if not self.is_safe_feature_position(candidate, layout.obstacles, collision_radius):
                continue
            if any(candidate.distance_to(existing) < collision_radius * 2.4 for existing in points):
                continue
            points.append(candidate)
            if len(points) >= count:
                break

        attempts = 0
        while len(points) < count and attempts < 40:
            attempts += 1
            candidate = layout.sample_point(self.rng, margin=collision_radius + 14)
            if not self.is_safe_feature_position(candidate, layout.obstacles, collision_radius):
                continue
            if any(candidate.distance_to(existing) < collision_radius * 2.4 for existing in points):
                continue
            points.append(candidate)

        if len(points) < count:
            fallback = [point for point in self.build_feature_anchor_candidates(layout) if point not in points]
            for candidate in fallback:
                if self.is_safe_feature_position(candidate, layout.obstacles, max(18, collision_radius - 4)):
                    points.append(candidate)
                if len(points) >= count:
                    break

        return points[:count]

    def build_shop_offers(self, layout: RoomLayout, difficulty: int) -> list[ShopOffer]:
        picks = self.rng.sample(list(SHOP_OFFER_POOL), 3)
        positions = self.get_room_feature_points(layout, 3)
        return [
            ShopOffer(
                key=offer.key,
                name=offer.name,
                description=offer.description,
                cost=scale_shop_cost(offer.base_cost, self.floor_index, difficulty),
                pos=pos.copy(),
            )
            for offer, pos in zip(picks, positions)
        ]

    def roll_upgrade_choices(self, count: int = 3) -> list[Upgrade]:
        laser_weapon = self.weapon_mode == "laser" or self.selected_weapon.key in {"laser_burst", "laser_lance"}
        filtered = [
            upgrade
            for upgrade in UPGRADES
            if not (
                (upgrade.key == "multishot" and self.multishot >= 2)
                or (laser_weapon and upgrade.key in {"multishot", "pierce"})
                or (upgrade.key == "ricochet" and self.player_bullet_bounces >= 1)
                or (not laser_weapon and upgrade.key == "accuracy" and self.player_spread <= 0.004)
                or (laser_weapon and upgrade.key == "accuracy" and self.player_beam_width <= 10)
                or (upgrade.key == "crit_rate" and self.player_crit_chance >= 0.45)
                or (upgrade.key == "crit_damage" and self.player_crit_multiplier >= 2.85)
                or (upgrade.key == "enemy_bullet_slow" and self.enemy_bullet_speed_multiplier <= 0.60)
                or (upgrade.key == "credit_boost" and self.credit_gain_multiplier >= 2.0)
            )
        ]
        pool = filtered if len(filtered) >= count else list(UPGRADES)
        return self.rng.sample(pool, count)

    def make_enemy(self, arena: pygame.Rect) -> Enemy:
        if self.room_layout is not None and self.room_layout.enemy_cells:
            pos = self.random_free_position(
                arena,
                config.ENEMY_RADIUS + 8,
                allowed_cells=self.room_layout.enemy_cells,
                min_distance=180,
            )
        else:
            pos = self.random_free_position(arena, config.ENEMY_RADIUS + 8)
        hp_scale, damage_scale, speed_bonus = enemy_scaling(self.room_index, self.floor_index)
        roll = self.rng.random()
        kind = "grunt"
        color = config.ENEMY_COLOR
        speed = config.ENEMY_SPEED + speed_bonus
        damage = config.ENEMY_TOUCH_DAMAGE * damage_scale
        xp_reward = 8 + self.room_index // 2 + max(0, self.floor_index - 1)
        radius = config.ENEMY_RADIUS
        shoot_cooldown = 0.0
        knockback_resist = 1.0
        max_hp = 33 * hp_scale
        laser_roll = 0.0 if self.room_index < 5 else (0.07 if self.room_index <= 7 else 0.10)
        shooter_roll = 0.14 if self.room_index <= 5 else 0.20
        if laser_roll > 0 and roll < laser_roll:
            kind = "laser"
            color = config.ENEMY_LASER_COLOR
            speed *= 0.76
            damage *= 0.95
            shoot_cooldown = max(1.5, 2.28 - self.room_index * 0.03 - max(0, self.floor_index - 1) * 0.05)
            xp_reward += 7
            max_hp *= 1.28
        elif self.room_index >= 2 and roll < laser_roll + shooter_roll:
            kind = "shooter"
            color = config.SHOOTER_COLOR
            speed *= 0.78 if self.room_index <= 5 else 0.84
            damage *= 0.62 if self.room_index <= 5 else 0.80
            shoot_cooldown = max(1.0, 1.92 - self.room_index * 0.03 - max(0, self.floor_index - 1) * 0.05)
            xp_reward += 4
            max_hp *= 1.10 if self.room_index <= 5 else 1.18
        elif self.room_index >= 3 and roll < 0.38:
            kind = "charger"
            speed *= 1.35
            damage *= 1.15
            color = (255, 150, 150)
            xp_reward += 3
            max_hp *= 1.1
        elif self.room_index >= 4 and roll < 0.48:
            kind = "elite"
            color = config.ELITE_COLOR
            speed *= 1.10
            damage *= 1.20
            radius += 4
            xp_reward += 10
            knockback_resist = 1.8
            max_hp *= 1.72
        return Enemy(
            pos=pos,
            hp=max_hp,
            max_hp=max_hp,
            speed=speed,
            radius=radius,
            damage=damage,
            xp_reward=xp_reward,
            color=color,
            knockback_resist=knockback_resist,
            kind=kind,
            shoot_cooldown=shoot_cooldown,
            shoot_timer=self.rng.random() * shoot_cooldown if shoot_cooldown else 0.0,
        )

    def make_boss(self, arena: pygame.Rect) -> Enemy:
        if self.room_layout is not None and self.room_layout.enemy_cells:
            pos = self.random_free_position(
                arena,
                config.BOSS_RADIUS + 10,
                allowed_cells=list(self.room_layout.enemy_cells[:2]) or list(self.room_layout.enemy_cells),
                min_distance=220,
            )
        else:
            pos = pygame.Vector2(arena.centerx, arena.top + 70)
        hp_scale, damage_scale, speed_bonus = enemy_scaling(self.room_index, self.floor_index)
        max_hp = 300 * hp_scale
        return Enemy(
            pos=pos,
            hp=max_hp,
            max_hp=max_hp,
            speed=config.BOSS_SPEED + speed_bonus * 0.35,
            radius=config.BOSS_RADIUS,
            damage=config.ENEMY_TOUCH_DAMAGE * 1.2 * damage_scale,
            xp_reward=50 + self.room_index * 3,
            color=config.BOSS_COLOR,
            knockback_resist=2.8,
            is_boss=True,
            kind="boss",
            shoot_cooldown=max(0.82, 1.42 - self.room_index * 0.02 - max(0, self.floor_index - 1) * 0.04),
            shoot_timer=0.7,
        )

    def give_xp(self, amount: int) -> None:
        self.xp += amount
        while self.xp >= self.xp_to_level:
            self.xp -= self.xp_to_level
            self.level += 1
            self.xp_to_level = int(self.xp_to_level * 1.22) + 10
            self.mode = "level_up"
            self.upgrade_choices = self.roll_upgrade_choices()

    def apply_upgrade(self, upgrade: Upgrade) -> str:
        applied_name = upgrade.name
        if upgrade.key == "damage":
            self.player_damage *= 1.12
        elif upgrade.key == "rapid":
            self.fire_cooldown = max(0.11, self.fire_cooldown * 0.94)
        elif upgrade.key == "accuracy":
            if self.weapon_mode == "laser":
                self.player_damage *= 1.06
                self.player_beam_width = max(10, self.player_beam_width - 1)
                applied_name = f"{upgrade.name}（转化为聚焦增益）"
            else:
                self.player_spread = max(0.004, self.player_spread * 0.82)
        elif upgrade.key == "crit_rate":
            self.player_crit_chance = min(0.45, self.player_crit_chance + 0.06)
        elif upgrade.key == "crit_damage":
            self.player_crit_multiplier = min(2.85, self.player_crit_multiplier + 0.18)
        elif upgrade.key == "speed":
            self.player_speed += 16
        elif upgrade.key == "max_hp":
            self.player_max_hp += 12
            self.player_hp = min(self.player_max_hp, self.player_hp + 12)
        elif upgrade.key == "heal":
            self.player_hp = min(self.player_max_hp, self.player_hp + 22)
        elif upgrade.key == "shield_core":
            self.player_max_shield += 10
            self.player_shield = min(self.player_max_shield, self.player_shield + 14)
        elif upgrade.key == "pierce":
            if self.weapon_mode == "laser":
                self.player_damage += 2
                applied_name = f"{upgrade.name}（转化为激光伤害 +2）"
            else:
                self.bullet_pierce += 1
        elif upgrade.key == "multishot":
            if self.weapon_mode == "laser":
                self.player_beam_width += 3
                applied_name = f"{upgrade.name}（转化为激光宽度 +3）"
            elif self.multishot < 2:
                self.multishot += 1
            else:
                self.player_damage += 2
                applied_name = f"{upgrade.name}（转化为火力 +2）"
        elif upgrade.key == "magnet":
            self.pickup_radius += 16
        elif upgrade.key == "pulse":
            self.pulse_damage += 8
            self.pulse_cooldown = max(4.8, self.pulse_cooldown * 0.94)
        elif upgrade.key == "dash":
            self.dash_cooldown = max(1.0, self.dash_cooldown * 0.93)
            self.player_speed += 8
        elif upgrade.key == "enemy_bullet_slow":
            self.enemy_bullet_speed_multiplier = max(0.60, self.enemy_bullet_speed_multiplier * 0.88)
        elif upgrade.key == "credit_boost":
            self.credit_gain_multiplier = min(2.0, self.credit_gain_multiplier + 0.25)
        elif upgrade.key == "ricochet":
            if self.player_bullet_bounces < 1:
                self.player_bullet_bounces = 1
            elif self.weapon_mode == "laser":
                self.player_beam_width += 2
                applied_name = f"{upgrade.name}（转化为激光宽度 +2）"
            else:
                self.bullet_pierce += 1
                applied_name = f"{upgrade.name}（转化为穿透 +1）"
        elif upgrade.key == "pulse_radius":
            self.pulse_radius += 22
        self.mode = "playing"
        self.message = f"已获得 {applied_name}"
        return applied_name

    def claim_reward(self, upgrade: Upgrade) -> None:
        applied_name = self.apply_upgrade(upgrade)
        if self.reward_source == "treasure" and self.current_room_state is not None:
            self.current_room_state.chest_opened = True
            self.current_room_state.resolved = True
            self.reward_source = None
            self.message = f"宝箱获得 {applied_name}"
            return
        self.reward_source = None

    def claim_supply(self, option: SupplyOption) -> None:
        if option.key == "repair":
            self.player_hp = min(self.player_max_hp, self.player_hp + 40)
        elif option.key == "overclock":
            self.player_damage += 4
            self.pulse_timer = 0.0
        elif option.key == "charge":
            self.dash_timer = 0.0
            self.pulse_timer = 0.0
        self.floaters.append(FloatingText(self.player_pos.copy(), option.name, config.PLAYER_COLOR, 0.8))
        self.mode = "playing"
        self.message = f"已获得 {option.name}"

    def get_choice_rects(self) -> list[pygame.Rect]:
        start_x = 180
        return [pygame.Rect(start_x + idx * 310, 220, 260, 200) for idx in range(3)]

    def get_stage_rects(self) -> list[pygame.Rect]:
        return [pygame.Rect(44, 136 + idx * 54, 338, 44) for idx in range(len(STAGES))]

    def get_character_rects(self) -> list[pygame.Rect]:
        return [pygame.Rect(44, 320 + idx * 48, 338, 38) for idx in range(len(CHARACTERS))]

    def get_weapon_rects(self) -> list[pygame.Rect]:
        return [pygame.Rect(44, 474 + idx * 44, 338, 36) for idx in range(len(WEAPONS))]

    def get_title_info_panel(self) -> pygame.Rect:
        return pygame.Rect(410, 124, 834, 548)

    def get_title_start_button(self) -> pygame.Rect:
        return pygame.Rect(992, 592, 216, 46)

    def title_detail_sections(self) -> tuple[tuple[str, str, str], ...]:
        return (
            ("\u4efb\u52a1\u7b80\u4ecb", self.selected_stage.name, self.selected_stage.description),
            ("\u5f53\u524d\u673a\u4f53", self.selected_character.name, self.selected_character.passive),
            ("\u5f53\u524d\u6b66\u5668", self.selected_weapon.name, self.selected_weapon.passive),
        )

    def apply_obstacle_damage(self, obstacle: RoomObstacle, damage: float) -> bool:
        if not obstacle.destructible:
            return False
        actual_damage = max(6.0, damage)
        destroyed = obstacle.damage(actual_damage)
        self.floaters.append(FloatingText(pygame.Vector2(obstacle.rect.center), f"{int(actual_damage)}", config.ITEM_COLOR, 0.35))
        if not destroyed:
            return False

        impact_pos = pygame.Vector2(obstacle.rect.center)
        if obstacle in self.obstacles:
            self.obstacles.remove(obstacle)
        self.floaters.append(FloatingText(impact_pos, "掩体破坏", config.ITEM_COLOR, 0.55))
        debris_color = obstacle.border_color if getattr(obstacle, "border_color", None) is not None else config.ITEM_COLOR
        dust_color = obstacle.fill_color if getattr(obstacle, "fill_color", None) is not None else config.OBSTACLE_BORDER
        self.spawn_particles(impact_pos, debris_color, 14, 1.35, (2.0, 5.4), (0.22, 0.55))
        self.spawn_particles(impact_pos, dust_color, 8, 0.95, (1.6, 3.8), (0.16, 0.34))
        if self.rng.random() < 0.12:
            self.pickups.append(
                Pickup(
                    impact_pos.copy(),
                    obstacle_credit_drop(self.room_index, self.floor_index),
                    config.ITEM_PICKUP_RADIUS,
                    "credit",
                    config.CREDIT_COLOR,
                    "晶片",
                )
            )
        self.handle_destroyed_obstacle(obstacle, impact_pos)
        if self.current_room_state is not None:
            self.current_room_state.layout.obstacles = self.obstacles
        return True

    def spawn_explosion_wave(self, pos: pygame.Vector2, radius: float, color: tuple[int, int, int], ttl: float = 0.42) -> None:
        self.explosion_waves.append(
            ExplosionWave(
                pos=pos.copy(),
                radius=radius,
                ttl=ttl,
                max_ttl=ttl,
                color=color,
            )
        )

    def apply_explosion_damage(
        self,
        center: pygame.Vector2,
        radius: float,
        damage: float,
        color: tuple[int, int, int],
        *,
        source: RoomObstacle | None = None,
    ) -> None:
        self.spawn_explosion_wave(center, radius, color)
        for enemy in self.enemies[:]:
            distance = enemy.pos.distance_to(center)
            if distance > radius + enemy.radius:
                continue
            falloff = max(0.46, 1.0 - distance / max(1.0, radius + enemy.radius))
            dealt = damage * falloff
            enemy.hp -= dealt
            self.floaters.append(FloatingText(enemy.pos.copy(), str(int(dealt)), color, 0.35))
            if enemy.hp <= 0:
                self.kill_enemy(enemy)

        player_distance = self.player_pos.distance_to(center)
        if player_distance <= radius + config.PLAYER_RADIUS and self.iframes <= 0:
            falloff = max(0.46, 1.0 - player_distance / max(1.0, radius + config.PLAYER_RADIUS))
            self.damage_player(damage * falloff, color, 0.22)

        obstacle_damage = max(12.0, damage * 1.75)
        for obstacle in self.obstacles[:]:
            if obstacle is source or not obstacle.destructible:
                continue
            if not self.circle_intersects_rect(center, int(radius), obstacle.rect.inflate(8, 8)):
                continue
            obstacle_center = pygame.Vector2(obstacle.rect.center)
            falloff = max(0.55, 1.0 - obstacle_center.distance_to(center) / max(1.0, radius + max(obstacle.rect.width, obstacle.rect.height) * 0.45))
            self.apply_obstacle_damage(obstacle, obstacle_damage * falloff)

    def handle_destroyed_obstacle(self, obstacle: RoomObstacle, impact_pos: pygame.Vector2) -> None:
        theme = self.current_room_state.layout.theme if self.current_room_state is not None else ""
        tag = getattr(obstacle, "tag", "normal")
        if tag == "normal":
            if theme == "反应堆室":
                tag = "reactor"
            elif theme == "废料堆场":
                tag = "toxic"
        if tag == "reactor" or (tag == "normal" and theme == "\u53cd\u5e94\u5806\u5ba4"):
            profile = hazard_profile("reactor", obstacle.rect)
            blast_radius = profile.radius
            blast_damage = profile.damage
            self.spawn_particles(impact_pos, config.BULLET_SHOCK_COLOR, int(18 + blast_radius / 18), 1.6, (2.5, 6.2), (0.22, 0.52))
            self.floaters.append(FloatingText(impact_pos.copy(), f"反应爆裂 {int(blast_radius)}", config.BULLET_SHOCK_COLOR, 0.6))
            self.apply_explosion_damage(impact_pos, blast_radius, blast_damage, config.BULLET_SHOCK_COLOR, source=obstacle)
        elif tag == "bullet":
            self.spawn_bullet_barrel_burst(impact_pos, obstacle.rect)
        elif tag == "toxic" or (tag == "normal" and theme == "\u5e9f\u6599\u5806\u573a"):
            profile = hazard_profile("toxic", obstacle.rect)
            self.gas_clouds.append(GasCloud(pos=impact_pos.copy(), radius=profile.radius, ttl=profile.ttl, damage=profile.damage))
            self.spawn_particles(impact_pos, (120, 210, 110), int(12 + profile.radius / 20), 0.84, (2.5, 5.0), (0.4, 0.9))
            self.floaters.append(FloatingText(impact_pos.copy(), f"毒气泄露 {int(profile.radius)}", (148, 220, 118), 0.6))

    def get_center_action_buttons(self, count: int) -> list[pygame.Rect]:
        total_width = count * 170 + (count - 1) * 24
        start_x = (config.WIDTH - total_width) // 2
        return [pygame.Rect(start_x + idx * 194, 430, 170, 52) for idx in range(count)]

    def handle_choice_click(self, mouse_pos: tuple[int, int], choices: list[Upgrade], callback) -> bool:
        for rect, choice in zip(self.get_choice_rects(), choices):
            if rect.collidepoint(mouse_pos):
                callback(choice)
                return True
        return False

    def handle_stage_click(self, mouse_pos: tuple[int, int]) -> bool:
        for rect, stage in zip(self.get_stage_rects(), STAGES):
            if rect.collidepoint(mouse_pos):
                self.selected_stage = stage
                return True
        return False

    def handle_character_click(self, mouse_pos: tuple[int, int]) -> bool:
        for rect, character in zip(self.get_character_rects(), CHARACTERS):
            if rect.collidepoint(mouse_pos):
                self.selected_character = character
                return True
        return False

    def handle_weapon_click(self, mouse_pos: tuple[int, int]) -> bool:
        for rect, weapon in zip(self.get_weapon_rects(), WEAPONS):
            if rect.collidepoint(mouse_pos):
                self.selected_weapon = weapon
                return True
        return False

    def get_title_menu_buttons(self) -> dict[str, pygame.Rect]:
        return {
            "stage": pygame.Rect(44, 150, 338, 64),
            "character": pygame.Rect(44, 236, 338, 64),
            "weapon": pygame.Rect(44, 322, 338, 64),
        }

    def get_title_panel_back_button(self) -> pygame.Rect:
        return pygame.Rect(42, 632, 110, 34)

    def get_title_panel_start_button(self) -> pygame.Rect:
        return pygame.Rect(260, 632, 122, 34)

    def get_title_panel_option_rects(self, count: int) -> list[pygame.Rect]:
        if count <= 0:
            return []
        top = 176
        gap = 10
        bottom = self.get_title_panel_back_button().top - 18
        available = bottom - top - gap * (count - 1)
        height = max(72, min(86, available // count))
        return [pygame.Rect(88, top + idx * (height + gap), 1104, height) for idx in range(count)]

    def current_title_options(self) -> list[StageOption | CharacterOption | WeaponOption]:
        if self.title_panel == "stage":
            return list(STAGES)
        if self.title_panel == "character":
            return list(CHARACTERS)
        if self.title_panel == "weapon":
            return list(WEAPONS)
        return []

    def select_title_option(self, idx: int) -> None:
        if self.title_panel == "stage":
            self.selected_stage = STAGES[idx]
        elif self.title_panel == "character":
            self.selected_character = CHARACTERS[idx]
        elif self.title_panel == "weapon":
            self.selected_weapon = WEAPONS[idx]

    def hotkey_to_index(self, key: int) -> int | None:
        mapping = {
            pygame.K_1: 0,
            pygame.K_KP1: 0,
            pygame.K_2: 1,
            pygame.K_KP2: 1,
            pygame.K_3: 2,
            pygame.K_KP3: 2,
            pygame.K_4: 3,
            pygame.K_KP4: 3,
            pygame.K_5: 4,
            pygame.K_KP5: 4,
        }
        return mapping.get(key)

    def open_title_panel(self, panel: str) -> None:
        self.title_panel = panel
        title, _ = TITLE_PANEL_INFO.get(panel, TITLE_PANEL_INFO["main"])
        self.message = title

    def handle_title_click(self, mouse_pos: tuple[int, int]) -> bool:
        if self.title_panel == "main":
            for key, rect in self.get_title_menu_buttons().items():
                if rect.collidepoint(mouse_pos):
                    self.open_title_panel(key)
                    return True
            if self.get_title_start_button().collidepoint(mouse_pos):
                self.start_run(self.selected_stage.start_room)
                return True
        else:
            if self.get_title_panel_back_button().collidepoint(mouse_pos):
                self.title_panel = "main"
                return True
            if self.get_title_panel_start_button().collidepoint(mouse_pos):
                self.start_run(self.selected_stage.start_room)
                return True
            options = self.current_title_options()
            for idx, rect in enumerate(self.get_title_panel_option_rects(len(options))):
                if rect.collidepoint(mouse_pos):
                    self.select_title_option(idx)
                    self.title_panel = "main"
                    return True
        return False

    def handle_pause_click(self, mouse_pos: tuple[int, int]) -> bool:
        buttons = self.get_center_action_buttons(3)
        if buttons[0].collidepoint(mouse_pos):
            self.mode = "playing"
            return True
        if buttons[1].collidepoint(mouse_pos):
            self.start_run(self.selected_stage.start_room)
            return True
        if buttons[2].collidepoint(mouse_pos):
            self.mode = "title"
            return True
        return False

    def handle_dead_click(self, mouse_pos: tuple[int, int]) -> bool:
        buttons = self.get_center_action_buttons(2)
        if buttons[0].collidepoint(mouse_pos):
            self.start_run(self.selected_stage.start_room)
            return True
        if buttons[1].collidepoint(mouse_pos):
            self.mode = "title"
            return True
        return False

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.mode == "level_up":
                    self.handle_choice_click(event.pos, self.upgrade_choices, self.apply_upgrade)
                elif self.mode == "reward_room":
                    self.handle_choice_click(event.pos, self.reward_choices, self.claim_reward)
                elif self.mode == "supply_room":
                    self.handle_choice_click(event.pos, self.supply_choices, self.claim_supply)
                elif self.mode == "title":
                    self.handle_title_click(event.pos)
                elif self.mode == "paused":
                    self.handle_pause_click(event.pos)
                elif self.mode == "dead":
                    self.handle_dead_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.mode == "title" and self.title_panel != "main":
                        self.title_panel = "main"
                    elif self.mode == "playing":
                        self.mode = "paused"
                    elif self.mode == "paused":
                        self.mode = "playing"
                elif self.mode == "title" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.start_run(self.selected_stage.start_room)
                elif self.mode == "title" and self.title_panel == "main" and event.key in (pygame.K_1, pygame.K_KP1):
                    self.open_title_panel("stage")
                elif self.mode == "title" and self.title_panel == "main" and event.key in (pygame.K_2, pygame.K_KP2):
                    self.open_title_panel("character")
                elif self.mode == "title" and self.title_panel == "main" and event.key in (pygame.K_3, pygame.K_KP3):
                    self.open_title_panel("weapon")
                elif self.mode == "title" and self.title_panel != "main":
                    idx = self.hotkey_to_index(event.key)
                    if idx is not None and idx < len(self.current_title_options()):
                        self.select_title_option(idx)
                        self.title_panel = "main"
                elif self.mode == "dead" and event.key == pygame.K_r:
                    self.start_run(self.selected_stage.start_room)
                elif self.mode == "dead" and event.key == pygame.K_m:
                    self.mode = "title"
                elif self.mode == "paused" and event.key == pygame.K_r:
                    self.start_run(self.selected_stage.start_room)
                elif self.mode == "paused" and event.key == pygame.K_m:
                    self.mode = "title"
                elif self.mode == "playing" and event.key == pygame.K_SPACE:
                    self.try_dash()
                elif self.mode == "playing" and event.key == pygame.K_q:
                    self.try_pulse()
                elif self.mode == "playing" and event.key == pygame.K_e:
                    self.handle_interaction()
                elif self.mode == "level_up":
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        self.apply_upgrade(self.upgrade_choices[0])
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        self.apply_upgrade(self.upgrade_choices[1])
                    elif event.key in (pygame.K_3, pygame.K_KP3):
                        self.apply_upgrade(self.upgrade_choices[2])
                elif self.mode == "reward_room":
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        self.claim_reward(self.reward_choices[0])
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        self.claim_reward(self.reward_choices[1])
                    elif event.key in (pygame.K_3, pygame.K_KP3):
                        self.claim_reward(self.reward_choices[2])
                elif self.mode == "supply_room":
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        self.claim_supply(self.supply_choices[0])
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        self.claim_supply(self.supply_choices[1])
                    elif event.key in (pygame.K_3, pygame.K_KP3):
                        self.claim_supply(self.supply_choices[2])

    def handle_interaction(self) -> None:
        room = self.current_room_state
        if room is None:
            return
        if room.room_type == "shop":
            offer = self.get_nearby_shop_offer()
            if offer is None:
                return
            if offer.sold:
                self.message = f"{offer.name} 已售出"
                return
            if self.credits < offer.cost:
                self.message = f"晶片不足：{offer.cost}"
                return
            self.credits -= offer.cost
            offer.sold = True
            self.apply_shop_offer(offer)
            return
        if room.room_type == "treasure" and not room.chest_opened:
            chest_pos = self.get_room_feature_anchor(room)
            if self.player_pos.distance_to(chest_pos) <= 70:
                self.reward_source = "treasure"
                self.reward_choices = self.roll_upgrade_choices()
                self.mode = "reward_room"
                return
        if room.room_type == "boss" and room.exit_active:
            portal_pos = self.get_room_feature_anchor(room)
            if self.player_pos.distance_to(portal_pos) <= 76:
                self.advance_floor()

    def get_nearby_shop_offer(self) -> ShopOffer | None:
        room = self.current_room_state
        if room is None or room.room_type != "shop":
            return None
        for offer in room.shop_offers:
            if self.player_pos.distance_to(offer.pos) <= 62:
                return offer
        return None

    def apply_shop_offer(self, offer: ShopOffer) -> None:
        if offer.key in UPGRADE_KEYS:
            applied_name = self.apply_upgrade(Upgrade(offer.key, offer.name, offer.description))
            self.message = f"已购买 {applied_name}"
            return
        elif offer.key == "repair":
            self.player_hp = min(self.player_max_hp, self.player_hp + 40)
            self.floaters.append(FloatingText(self.player_pos.copy(), "+40 生命", config.HEAL_COLOR, 0.8))
        elif offer.key == "shield_charge":
            self.player_shield = min(self.player_max_shield, self.player_shield + 30)
            self.floaters.append(FloatingText(self.player_pos.copy(), "+30 护盾", config.SHIELD_COLOR, 0.8))
        self.message = f"已购买 {offer.name}"

    def resolve_current_room(self) -> None:
        room = self.current_room_state
        if room is None or room.resolved:
            return
        room.resolved = True
        room.doors_locked = False
        self.room_clear_delay = 0.0
        self.room_transition_cooldown = 0.35
        self.rooms_cleared += 1
        if room.room_type == "elite":
            self.spawn_resolution_pickups("elite")
            self.message = "精英房已清空，房门已开启"
        elif room.room_type == "boss":
            room.exit_active = True
            self.spawn_resolution_pickups("boss")
            self.message = "首领已击败，传送门已启动"
        else:
            self.message = "区域已清空，房门已开启"

    def spawn_resolution_pickups(self, reward_type: str) -> None:
        if self.current_room_state is None:
            return
        anchor = self.get_room_feature_anchor(self.current_room_state)
        if reward_type == "elite":
            self.pickups.append(Pickup(anchor + pygame.Vector2(-18, 0), 24, config.ITEM_PICKUP_RADIUS, "shield", config.SHIELD_COLOR, "护盾"))
            self.pickups.append(Pickup(anchor + pygame.Vector2(18, 0), reward_credit_drop(self.floor_index, "elite"), config.ITEM_PICKUP_RADIUS, "credit", config.CREDIT_COLOR, "晶片"))
        elif reward_type == "boss":
            self.pickups.append(Pickup(anchor + pygame.Vector2(-24, 0), 34, config.ITEM_PICKUP_RADIUS, "shield", config.SHIELD_COLOR, "护盾"))
            self.pickups.append(Pickup(anchor + pygame.Vector2(24, 0), reward_credit_drop(self.floor_index, "boss"), config.ITEM_PICKUP_RADIUS, "credit", config.CREDIT_COLOR, "晶片"))
            self.pickups.append(Pickup(anchor + pygame.Vector2(0, -18), 1, config.ITEM_PICKUP_RADIUS, "item", config.ITEM_COLOR, "道具"))

    def get_room_feature_anchor(self, room: RoomState) -> pygame.Vector2:
        if room.feature_anchor is not None:
            return room.feature_anchor.copy()
        anchors = self.get_room_feature_points(room.layout, 1, collision_radius=40)
        room.feature_anchor = anchors[0] if anchors else room.layout.player_spawn.copy()
        return room.feature_anchor.copy()

    def current_interaction_prompt(self) -> str:
        room = self.current_room_state
        if room is None or self.mode != "playing":
            return ""
        if room.room_type == "shop":
            offer = self.get_nearby_shop_offer()
            if offer is not None:
                if offer.sold:
                    return f"{offer.name}（已售出）"
                return f"E 购买 {offer.name} - {offer.cost} 晶片"
        elif room.room_type == "treasure" and not room.chest_opened:
            if self.player_pos.distance_to(self.get_room_feature_anchor(room)) <= 70:
                return "E 打开宝箱"
        elif room.room_type == "boss" and room.exit_active:
            if self.player_pos.distance_to(self.get_room_feature_anchor(room)) <= 76:
                return "E 前往下一层"
        return ""

    def check_door_transition(self) -> None:
        room = self.current_room_state
        if room is None or self.room_layout is None or self.room_transition_cooldown > 0 or room.doors_locked:
            return
        for direction, door_rect in self.room_layout.screen_doors.items():
            if not door_rect.collidepoint(self.player_pos.x, self.player_pos.y):
                continue
            next_room_id = room.neighbors.get(direction)
            if next_room_id is None:
                continue
            self.enter_room(next_room_id, OPPOSITE_DIRECTIONS[direction])
            return

    def advance_floor(self) -> None:
        self.floor_index += 1
        self.bullets.clear()
        self.message = f"进入第 {self.floor_index} 层"
        self.build_floor()

    def update(self, dt: float) -> None:
        if self.mode != "playing":
            return
        self.iframes = max(0.0, self.iframes - dt)
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.pulse_timer = max(0.0, self.pulse_timer - dt)
        self.room_transition_cooldown = max(0.0, self.room_transition_cooldown - dt)
        self.update_player(dt)
        self.update_bullets(dt)
        self.update_enemies(dt)
        self.update_pickups(dt)
        self.update_gas_clouds(dt)
        self.update_explosion_waves(dt)
        self.update_particles(dt)
        self.update_laser_traces(dt)
        self.update_floaters(dt)
        if (
            self.current_room_state is not None
            and self.current_room_state.room_type in ("combat", "elite", "boss")
            and self.current_room_state.doors_locked
            and not self.enemies
        ):
            self.room_clear_delay += dt
            if self.room_clear_delay >= config.ROOM_CLEAR_FORCE_COLLECT_DELAY:
                self.absorb_all_pickups()
            if self.room_clear_delay >= config.ROOM_CLEAR_NEXT_ROOM_DELAY and not self.pickups:
                self.resolve_current_room()
        else:
            self.room_clear_delay = 0.0
        self.check_door_transition()

    def update_player(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            float(keys[pygame.K_d]) - float(keys[pygame.K_a]),
            float(keys[pygame.K_s]) - float(keys[pygame.K_w]),
        )
        if move.length_squared() > 0:
            move = move.normalize()
            self.last_move = move.copy()
            self.move_circle_with_collisions(self.player_pos, config.PLAYER_RADIUS, move * self.player_speed * dt)
        else:
            self.move_circle_with_collisions(self.player_pos, config.PLAYER_RADIUS, pygame.Vector2())

        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        pressed = pygame.mouse.get_pressed(num_buttons=3)[0]
        if pressed and self.fire_timer <= 0:
            aim = mouse_pos - self.player_pos
            if aim.length_squared() > 0:
                self.spawn_burst(aim.normalize())
                self.fire_timer = self.fire_cooldown

    def try_dash(self) -> None:
        if self.dash_timer > 0:
            return
        direction = self.last_move if self.last_move.length_squared() > 0 else pygame.Vector2(1, 0)
        self.move_circle_with_collisions(self.player_pos, config.PLAYER_RADIUS, direction.normalize() * self.dash_distance)
        self.iframes = max(self.iframes, 0.3)
        self.dash_timer = self.dash_cooldown
        self.floaters.append(FloatingText(self.player_pos.copy(), "冲刺", config.PLAYER_COLOR, 0.35))

    def try_pulse(self) -> None:
        if self.pulse_timer > 0:
            return
        self.pulse_timer = self.pulse_cooldown
        hits = 0
        for enemy in self.enemies[:]:
            dist = enemy.pos.distance_to(self.player_pos)
            if dist <= self.pulse_radius + enemy.radius:
                enemy.hp -= self.pulse_damage
                hits += 1
                knock = enemy.pos - self.player_pos
                if knock.length_squared() > 0:
                    self.move_circle_with_collisions(enemy.pos, enemy.radius, knock.normalize() * 32 / enemy.knockback_resist)
                self.floaters.append(FloatingText(enemy.pos.copy(), f"{int(self.pulse_damage)}", config.BULLET_SHOCK_COLOR, 0.45))
                if enemy.hp <= 0:
                    self.kill_enemy(enemy)
        self.floaters.append(FloatingText(self.player_pos.copy(), f"脉冲命中 {hits}", config.BULLET_SHOCK_COLOR, 0.6))

    def update_laser_traces(self, dt: float) -> None:
        remaining: list[LaserTrace] = []
        for trace in self.laser_traces:
            trace.ttl -= dt
            if trace.ttl > 0:
                remaining.append(trace)
        self.laser_traces = remaining

    def trace_beam(
        self,
        start: pygame.Vector2,
        direction: pygame.Vector2,
        radius: int,
        max_distance: float | None = None,
        bounces_left: int = 0,
    ) -> tuple[list[pygame.Vector2], list[pygame.Vector2]]:
        if direction.length_squared() <= 0:
            return [start.copy()], []
        beam_dir = direction.normalize()
        remaining_length = max_distance
        points = [start.copy()]
        impact_points: list[pygame.Vector2] = []
        current_start = start.copy()
        remaining_bounces = max(0, bounces_left)
        while True:
            end, normal = self.trace_beam_segment(current_start, beam_dir, radius, remaining_length)
            points.append(end)
            if normal is None:
                break
            impact_points.append(end.copy())
            if remaining_bounces <= 0:
                break
            if remaining_length is not None:
                remaining_length -= current_start.distance_to(end)
                if remaining_length <= 0:
                    break
            beam_dir = self.reflect_direction(beam_dir, normal)
            if beam_dir.length_squared() <= 0:
                break
            current_start = end + beam_dir * max(8, radius + 2)
            arena = self.arena_rect().inflate(-radius * 2, -radius * 2)
            if not arena.collidepoint(current_start.x, current_start.y):
                break
            remaining_bounces -= 1
        return points, impact_points

    def reflect_direction(self, direction: pygame.Vector2, normal: pygame.Vector2) -> pygame.Vector2:
        if direction.length_squared() <= 0 or normal.length_squared() <= 0:
            return pygame.Vector2()
        unit_dir = direction.normalize()
        unit_normal = normal.normalize()
        reflected = unit_dir - 2 * unit_dir.dot(unit_normal) * unit_normal
        if reflected.length_squared() <= 0:
            return pygame.Vector2()
        return reflected.normalize()

    def ray_to_rect_exit(
        self,
        origin: pygame.Vector2,
        direction: pygame.Vector2,
        rect: pygame.Rect,
    ) -> tuple[float, pygame.Vector2] | None:
        epsilon = 1e-6
        candidates: list[tuple[float, pygame.Vector2]] = []
        if direction.x > epsilon:
            candidates.append(((rect.right - origin.x) / direction.x, pygame.Vector2(-1, 0)))
        elif direction.x < -epsilon:
            candidates.append(((rect.left - origin.x) / direction.x, pygame.Vector2(1, 0)))
        if direction.y > epsilon:
            candidates.append(((rect.bottom - origin.y) / direction.y, pygame.Vector2(0, -1)))
        elif direction.y < -epsilon:
            candidates.append(((rect.top - origin.y) / direction.y, pygame.Vector2(0, 1)))
        positive = [(t, normal) for t, normal in candidates if t >= 0]
        if not positive:
            return None
        return min(positive, key=lambda item: item[0])

    def ray_to_rect_entry(
        self,
        origin: pygame.Vector2,
        direction: pygame.Vector2,
        rect: pygame.Rect,
    ) -> tuple[float, pygame.Vector2] | None:
        epsilon = 1e-6
        t_min = -math.inf
        t_max = math.inf
        hit_normal = pygame.Vector2()

        for axis in ("x", "y"):
            origin_value = getattr(origin, axis)
            direction_value = getattr(direction, axis)
            rect_min = rect.left if axis == "x" else rect.top
            rect_max = rect.right if axis == "x" else rect.bottom

            if abs(direction_value) <= epsilon:
                if origin_value < rect_min or origin_value > rect_max:
                    return None
                continue

            inv_dir = 1.0 / direction_value
            t1 = (rect_min - origin_value) * inv_dir
            t2 = (rect_max - origin_value) * inv_dir
            near = min(t1, t2)
            far = max(t1, t2)
            if near > t_min:
                t_min = near
                if axis == "x":
                    hit_normal = pygame.Vector2(-1, 0) if t1 < t2 else pygame.Vector2(1, 0)
                else:
                    hit_normal = pygame.Vector2(0, -1) if t1 < t2 else pygame.Vector2(0, 1)
            t_max = min(t_max, far)
            if t_min > t_max:
                return None

        if t_max < 0:
            return None
        if t_min <= epsilon:
            return None
        return t_min, hit_normal

    def trace_beam_segment(
        self,
        start: pygame.Vector2,
        direction: pygame.Vector2,
        radius: int,
        max_distance: float | None = None,
    ) -> tuple[pygame.Vector2, pygame.Vector2 | None]:
        if direction.length_squared() <= 0:
            return start.copy(), None
        beam_dir = direction.normalize()
        arena = self.arena_rect().inflate(-radius * 2, -radius * 2)
        arena_hit = self.ray_to_rect_exit(start, beam_dir, arena)
        if arena_hit is None:
            return start.copy(), None

        arena_distance, arena_normal = arena_hit
        best_distance = arena_distance
        best_normal: pygame.Vector2 | None = arena_normal
        if max_distance is not None and max_distance < best_distance:
            best_distance = max_distance
            best_normal = None

        for obstacle in self.obstacles:
            if obstacle.destructible:
                continue
            expanded = obstacle.rect.inflate(radius * 2, radius * 2)
            hit = self.ray_to_rect_entry(start, beam_dir, expanded)
            if hit is None:
                continue
            distance, normal = hit
            if 0 < distance < best_distance:
                best_distance = distance
                best_normal = normal

        end = start + beam_dir * best_distance
        return end, best_normal

    def point_to_segment_distance_squared(
        self,
        point: pygame.Vector2,
        start: pygame.Vector2,
        end: pygame.Vector2,
    ) -> float:
        segment = end - start
        if segment.length_squared() <= 0:
            return point.distance_squared_to(start)
        t = max(0.0, min(1.0, (point - start).dot(segment) / segment.length_squared()))
        closest = start + segment * t
        return point.distance_squared_to(closest)

    def segment_hits_circle(
        self,
        start: pygame.Vector2,
        end: pygame.Vector2,
        center: pygame.Vector2,
        radius: float,
    ) -> bool:
        return self.point_to_segment_distance_squared(center, start, end) <= radius * radius

    def segment_hits_rect(
        self,
        start: pygame.Vector2,
        end: pygame.Vector2,
        rect: pygame.Rect,
        padding: int = 0,
    ) -> bool:
        target = rect.inflate(padding * 2, padding * 2)
        clipped = target.clipline(
            (round(start.x), round(start.y)),
            (round(end.x), round(end.y)),
        )
        return bool(clipped)

    def get_accuracy_rating(self) -> int:
        if self.weapon_mode == "laser":
            return 100
        return max(35, min(99, int(round(100 - self.player_spread * 520))))

    def roll_player_hit(self, base_damage: float) -> tuple[float, bool]:
        crit = self.rng.random() < self.player_crit_chance
        if crit:
            return base_damage * self.player_crit_multiplier, True
        return base_damage, False

    def apply_projectile_offset(self, direction: pygame.Vector2) -> pygame.Vector2:
        if direction.length_squared() <= 0:
            return pygame.Vector2(1, 0)
        spread = 0.0 if self.weapon_mode == "laser" else self.player_spread
        adjusted = direction.normalize()
        if spread > 0:
            adjusted = adjusted.rotate_rad(self.rng.uniform(-spread, spread))
        return adjusted.normalize() if adjusted.length_squared() > 0 else pygame.Vector2(1, 0)

    def spawn_bullet_barrel_burst(self, origin: pygame.Vector2, rect: pygame.Rect) -> None:
        size = max(rect.width, rect.height)
        bullet_count = 8 if size <= 24 else 12 if size <= 34 else 16
        bullet_damage = 8.0 + size * 0.18 + self.floor_index * 0.55
        bullet_speed = config.BULLET_SPEED * (0.58 + min(0.22, size / 180))
        bullet_ttl = 1.2 + min(0.55, size / 110)
        for idx in range(bullet_count):
            angle = (math.tau / bullet_count) * idx + self.rng.uniform(-0.06, 0.06)
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            self.bullets.append(
                Bullet(
                    pos=origin.copy(),
                    velocity=direction * bullet_speed,
                    damage=bullet_damage,
                    radius=config.BULLET_RADIUS + 1,
                    ttl=bullet_ttl,
                    friendly=False,
                    color=config.BULLET_BARREL_COLOR,
                    hits_all=True,
                )
            )
        self.spawn_particles(origin.copy(), config.BULLET_BARREL_COLOR, 18, 1.25, (1.5, 4.2), (0.14, 0.34))
        self.floaters.append(FloatingText(origin.copy(), f"弹幕炸裂 x{bullet_count}", config.BULLET_BARREL_COLOR, 0.55))

    def fire_laser(
        self,
        origin: pygame.Vector2,
        direction: pygame.Vector2,
        damage: float,
        width: int,
        color: tuple[int, int, int],
        *,
        friendly: bool,
        trace_ttl: float = 0.12,
    ) -> None:
        if direction.length_squared() <= 0:
            return
        radius = max(3, width // 2)
        bounces_left = self.player_bullet_bounces if friendly else 0
        points, impact_points = self.trace_beam(origin, direction, radius, bounces_left=bounces_left)
        self.laser_traces.append(
            LaserTrace(
                points=[point.copy() for point in points],
                color=color,
                width=width,
                ttl=trace_ttl,
                max_ttl=trace_ttl,
                impact_points=[point.copy() for point in impact_points],
            )
        )
        self.spawn_particles(origin.copy(), color, 6 if friendly else 4, 0.82, (1.4, 3.2), (0.08, 0.18))
        for impact in impact_points:
            self.spawn_particles(impact.copy(), config.LASER_TRACE_CORE, 7, 1.18, (1.6, 3.8), (0.12, 0.24))

        if friendly:
            beam_hits = 0
            push_dir = direction.normalize()
            damaged_obstacles: set[int] = set()
            damaged_enemies: set[int] = set()
            for start, end in zip(points, points[1:]):
                for obstacle in self.obstacles[:]:
                    if not obstacle.destructible or id(obstacle) in damaged_obstacles:
                        continue
                    if not self.segment_hits_rect(start, end, obstacle.rect, max(5, int(width * 0.5))):
                        continue
                    damaged_obstacles.add(id(obstacle))
                    self.apply_obstacle_damage(obstacle, damage)
                for enemy in self.enemies[:]:
                    if id(enemy) in damaged_enemies:
                        continue
                    hit_radius = enemy.radius + width * 0.35
                    if not self.segment_hits_circle(start, end, enemy.pos, hit_radius):
                        continue
                    hit_damage, crit = self.roll_player_hit(damage)
                    enemy.hp -= hit_damage
                    beam_hits += 1
                    damaged_enemies.add(id(enemy))
                    self.move_circle_with_collisions(enemy.pos, enemy.radius, push_dir * 16 / enemy.knockback_resist)
                    floater_color = config.CRIT_COLOR if crit else color
                    floater_text = f"暴击 {int(hit_damage)}" if crit else str(int(hit_damage))
                    self.floaters.append(FloatingText(enemy.pos.copy(), floater_text, floater_color, 0.42))
                    if enemy.hp <= 0:
                        self.kill_enemy(enemy)
            if beam_hits:
                self.floaters.append(FloatingText(origin.copy() + pygame.Vector2(0, -22), f"激光命中 {beam_hits}", color, 0.35))
        else:
            hit_radius = config.PLAYER_RADIUS + width * 0.25
            for start, end in zip(points, points[1:]):
                if self.segment_hits_circle(start, end, self.player_pos, hit_radius) and self.iframes <= 0:
                    self.damage_player(damage, color, 0.38)
                    break

    def spawn_burst(self, direction: pygame.Vector2) -> None:
        if self.weapon_mode == "laser":
            self.fire_laser(
                self.player_pos.copy(),
                direction,
                self.player_damage,
                self.player_beam_width,
                self.player_beam_color,
                friendly=True,
                trace_ttl=0.14,
            )
            if self.selected_weapon.key == "laser_lance":
                recoil = direction.normalize() * -16
                self.move_circle_with_collisions(self.player_pos, config.PLAYER_RADIUS, recoil)
                self.spawn_particles(self.player_pos.copy(), self.player_beam_color, 5, 0.74, (1.5, 3.2), (0.08, 0.18))
            return
        spreads = [0.0]
        for i in range(self.multishot):
            angle = 0.24 + i * 0.06
            spreads.extend((angle, -angle))
        for angle in spreads:
            fired = self.apply_projectile_offset(direction.rotate_rad(angle))
            lateral = pygame.Vector2(-fired.y, fired.x)
            spawn_offset = lateral * self.rng.uniform(-self.player_spread * 180, self.player_spread * 180)
            damage, crit = self.roll_player_hit(self.player_damage)
            self.bullets.append(
                Bullet(
                    pos=self.player_pos.copy() + spawn_offset,
                    velocity=fired * config.BULLET_SPEED,
                    damage=damage,
                    radius=config.BULLET_RADIUS,
                    ttl=1.5,
                    pierce=self.bullet_pierce,
                    bounces_left=self.player_bullet_bounces,
                    friendly=True,
                    color=config.BULLET_COLOR,
                    crit=crit,
                )
            )

    def register_bullet_bounce(self, bullet: Bullet) -> None:
        bullet.bounces_left -= 1
        bullet.damage *= 0.92
        self.spawn_particles(bullet.pos.copy(), config.BULLET_COLOR, 4, 0.55, (1.2, 2.2), (0.08, 0.16))

    def try_bounce_from_arena(self, bullet: Bullet, arena: pygame.Rect) -> bool:
        if not bullet.friendly or bullet.bounces_left <= 0:
            return False
        bounced = False
        if bullet.pos.x - bullet.radius <= arena.left or bullet.pos.x + bullet.radius >= arena.right:
            bullet.velocity.x *= -1
            bullet.pos.x = max(arena.left + bullet.radius + 1, min(arena.right - bullet.radius - 1, bullet.pos.x))
            bounced = True
        if bullet.pos.y - bullet.radius <= arena.top or bullet.pos.y + bullet.radius >= arena.bottom:
            bullet.velocity.y *= -1
            bullet.pos.y = max(arena.top + bullet.radius + 1, min(arena.bottom - bullet.radius - 1, bullet.pos.y))
            bounced = True
        if bounced:
            self.register_bullet_bounce(bullet)
        return bounced

    def try_bounce_from_obstacle(self, bullet: Bullet, obstacle: RoomObstacle, previous_pos: pygame.Vector2) -> bool:
        if not bullet.friendly or bullet.bounces_left <= 0:
            return False
        rect = obstacle.rect
        horizontal_hit = previous_pos.x + bullet.radius <= rect.left or previous_pos.x - bullet.radius >= rect.right
        vertical_hit = previous_pos.y + bullet.radius <= rect.top or previous_pos.y - bullet.radius >= rect.bottom

        if not horizontal_hit and not vertical_hit:
            overlaps = {
                "left": abs((bullet.pos.x + bullet.radius) - rect.left),
                "right": abs(rect.right - (bullet.pos.x - bullet.radius)),
                "top": abs((bullet.pos.y + bullet.radius) - rect.top),
                "bottom": abs(rect.bottom - (bullet.pos.y - bullet.radius)),
            }
            side = min(overlaps, key=overlaps.get)
            horizontal_hit = side in {"left", "right"}
            vertical_hit = side in {"top", "bottom"}

        if horizontal_hit:
            bullet.velocity.x *= -1
            bullet.pos.x = rect.left - bullet.radius - 1 if previous_pos.x < rect.left else rect.right + bullet.radius + 1
        if vertical_hit:
            bullet.velocity.y *= -1
            bullet.pos.y = rect.top - bullet.radius - 1 if previous_pos.y < rect.top else rect.bottom + bullet.radius + 1
        self.register_bullet_bounce(bullet)
        return True

    def update_bullets(self, dt: float) -> None:
        arena = self.arena_rect()
        remaining: list[Bullet] = []
        for bullet in self.bullets:
            previous_pos = bullet.pos.copy()
            bullet.pos += bullet.velocity * dt
            bullet.ttl -= dt
            if bullet.ttl <= 0:
                continue
            if not arena.collidepoint(bullet.pos.x, bullet.pos.y):
                if self.try_bounce_from_arena(bullet, arena):
                    remaining.append(bullet)
                continue
            hit = False
            for obstacle in self.obstacles[:]:
                if not self.circle_intersects_rect(bullet.pos, bullet.radius, obstacle.rect):
                    continue
                hit = True
                if (bullet.friendly or bullet.hits_all) and obstacle.destructible:
                    destroyed = self.apply_obstacle_damage(obstacle, bullet.damage * 0.9)
                    if not destroyed and bullet.pierce > 0:
                        bullet.pierce -= 1
                        hit = False
                    elif not destroyed and self.try_bounce_from_obstacle(bullet, obstacle, previous_pos):
                        hit = False
                break
            if hit:
                continue
            if bullet.friendly or bullet.hits_all:
                for enemy in self.enemies[:]:
                    if bullet.pos.distance_to(enemy.pos) <= bullet.radius + enemy.radius:
                        enemy.hp -= bullet.damage
                        push = bullet.velocity.normalize() * 20 / enemy.knockback_resist
                        self.move_circle_with_collisions(enemy.pos, enemy.radius, push)
                        color = config.CRIT_COLOR if bullet.crit else (255, 220, 180)
                        text = f"暴击 {int(bullet.damage)}" if bullet.crit else str(int(bullet.damage))
                        self.floaters.append(FloatingText(enemy.pos.copy(), text, color, 0.45))
                        if enemy.hp <= 0:
                            self.kill_enemy(enemy)
                        if bullet.pierce > 0:
                            bullet.pierce -= 1
                        else:
                            hit = True
                        break
            if not hit and (not bullet.friendly or bullet.hits_all):
                if bullet.pos.distance_to(self.player_pos) <= bullet.radius + config.PLAYER_RADIUS and self.iframes <= 0:
                    self.damage_player(bullet.damage, (255, 130, 180), 0.35)
                    hit = True
            if not hit:
                remaining.append(bullet)
        self.bullets = remaining

    def kill_enemy(self, enemy: Enemy) -> None:
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        self.pickups.append(Pickup(enemy.pos.copy(), enemy.xp_reward, config.XP_PICKUP_RADIUS, "xp", config.XP_COLOR, "经验"))
        credit_amount = enemy_credit_drop(self.room_index, self.floor_index, enemy.kind)
        self.pickups.append(Pickup(enemy.pos.copy() + pygame.Vector2(0, 12), credit_amount, config.ITEM_PICKUP_RADIUS, "credit", config.CREDIT_COLOR, "晶片"))
        extra_roll = self.rng.random()
        if extra_roll < 0.10:
            self.pickups.append(Pickup(enemy.pos.copy() + pygame.Vector2(12, -8), 18, config.HEAL_PICKUP_RADIUS, "heal", config.HEAL_COLOR, "血包"))
        elif extra_roll < 0.18:
            self.pickups.append(Pickup(enemy.pos.copy() + pygame.Vector2(12, -8), 24, config.ITEM_PICKUP_RADIUS, "shield", config.SHIELD_COLOR, "护盾"))
        elif extra_roll < 0.26:
            self.pickups.append(Pickup(enemy.pos.copy() + pygame.Vector2(-12, 8), 1, config.ITEM_PICKUP_RADIUS, "item", config.ITEM_COLOR, "道具"))
        self.floaters.append(FloatingText(enemy.pos.copy(), f"+{enemy.xp_reward} 经验", config.XP_COLOR, 0.7))
        self.spawn_particles(enemy.pos.copy(), enemy.color, 12 if enemy.kind != "boss" else 22, 1.35, (2.0, 5.8), (0.22, 0.6))
        self.spawn_particles(enemy.pos.copy(), (255, 244, 220), 5 if enemy.kind != "boss" else 10, 0.9, (1.4, 3.2), (0.16, 0.36))
        if enemy.kind in ("elite", "boss"):
            self.spawn_particles(enemy.pos.copy(), config.CREDIT_COLOR, 8, 1.08, (2.0, 4.8), (0.22, 0.5))
        self.kills += 1

    def get_enemy_projectile_damage(self, enemy: Enemy) -> float:
        if enemy.kind == "shooter":
            return max(7.0, enemy.damage * 0.72)
        if enemy.kind == "boss":
            return max(14.0, enemy.damage * 1.02)
        return max(10.0, enemy.damage * 0.86)

    def get_enemy_laser_timing(self, enemy: Enemy) -> tuple[float, float]:
        telegraph_window = 0.95 if enemy.is_boss else 0.78
        lock_window = 0.34 if enemy.is_boss else 0.24
        return telegraph_window, lock_window

    def get_enemy_laser_damage(self, enemy: Enemy) -> float:
        if enemy.is_boss:
            return max(18.0, enemy.damage * 1.05)
        return max(12.0, enemy.damage * 0.92)

    def get_enemy_laser_width(self, enemy: Enemy) -> int:
        return 16 if enemy.is_boss else 12

    def update_enemies(self, dt: float) -> None:
        for enemy in self.enemies[:]:
            if enemy.shoot_cooldown > 0:
                enemy.shoot_timer -= dt
            nav_target, direct_engage = self.get_enemy_navigation_target(enemy.pos)
            delta_to_nav = nav_target - enemy.pos
            delta_to_player = self.player_pos - enemy.pos
            has_los = self.has_line_of_sight(enemy.pos, self.player_pos, max(6, enemy.radius // 2))
            move_delta = pygame.Vector2()
            if delta_to_nav.length_squared() > 0:
                nav_direction = delta_to_nav.normalize()
                if enemy.kind == "shooter":
                    engage = direct_engage or has_los
                    if engage and delta_to_player.length_squared() > 0:
                        player_direction = delta_to_player.normalize()
                        distance = delta_to_player.length()
                        if distance > 320:
                            move_delta += player_direction * enemy.speed * dt
                        elif distance < 240:
                            move_delta -= player_direction * enemy.speed * 0.75 * dt
                        move_delta += pygame.Vector2(-player_direction.y, player_direction.x) * 18 * dt
                        if enemy.shoot_timer <= 0:
                            self.enemy_shoot(enemy, player_direction, self.get_enemy_projectile_damage(enemy), config.BULLET_ENEMY_COLOR)
                            enemy.shoot_timer = enemy.shoot_cooldown
                    else:
                        move_delta += nav_direction * enemy.speed * 0.9 * dt
                elif enemy.kind == "laser":
                    engage = direct_engage or has_los
                    telegraph_window, lock_window = self.get_enemy_laser_timing(enemy)
                    tracking = 0 < enemy.shoot_timer <= telegraph_window
                    locked = 0 < enemy.shoot_timer <= lock_window
                    if delta_to_player.length_squared() > 0 and tracking and not locked:
                        enemy.aim_direction = delta_to_player.normalize()
                    elif enemy.aim_direction.length_squared() <= 0 and delta_to_player.length_squared() > 0:
                        enemy.aim_direction = delta_to_player.normalize()

                    if engage and delta_to_player.length_squared() > 0:
                        player_direction = delta_to_player.normalize()
                        distance = delta_to_player.length()
                        if enemy.shoot_timer > telegraph_window:
                            if distance > 340:
                                move_delta += player_direction * enemy.speed * dt
                            elif distance < 230:
                                move_delta -= player_direction * enemy.speed * 0.85 * dt
                            move_delta += pygame.Vector2(-player_direction.y, player_direction.x) * 14 * dt
                        elif not locked:
                            if distance > 330:
                                move_delta += player_direction * enemy.speed * 0.26 * dt
                            elif distance < 210:
                                move_delta -= player_direction * enemy.speed * 0.22 * dt
                    else:
                        move_delta += nav_direction * enemy.speed * 0.8 * dt

                    if enemy.shoot_timer <= 0 and enemy.aim_direction.length_squared() > 0:
                        self.fire_laser(
                            enemy.pos.copy(),
                            enemy.aim_direction,
                            self.get_enemy_laser_damage(enemy),
                            self.get_enemy_laser_width(enemy),
                            config.ENEMY_LASER_COLOR,
                            friendly=False,
                            trace_ttl=0.18,
                        )
                        enemy.shoot_timer = enemy.shoot_cooldown
                        enemy.aim_direction = pygame.Vector2()
                else:
                    speed_scale = 1.18 if enemy.kind == "charger" else 1.0
                    pursue_direction = delta_to_player.normalize() if direct_engage and delta_to_player.length_squared() > 0 else nav_direction
                    move_delta += pursue_direction * enemy.speed * speed_scale * dt
                    if enemy.kind in ("elite", "boss") and enemy.shoot_timer <= 0 and has_los and delta_to_player.length_squared() > 0:
                        self.enemy_shoot(
                            enemy,
                            delta_to_player.normalize(),
                            self.get_enemy_projectile_damage(enemy),
                            config.BULLET_ELITE_COLOR,
                            spread=0.14 if enemy.kind == "boss" else 0.0,
                        )
                        enemy.shoot_timer = enemy.shoot_cooldown
            if move_delta.length_squared() > 0:
                avoid = self.get_enemy_avoidance(enemy)
                if avoid.length_squared() > 0:
                    move_delta += avoid.normalize() * enemy.speed * 0.42 * dt
            self.move_circle_with_collisions(enemy.pos, enemy.radius, move_delta)
            if enemy.pos.distance_to(self.player_pos) <= enemy.radius + config.PLAYER_RADIUS:
                if self.iframes <= 0:
                    self.damage_player(enemy.damage, (255, 130, 130), 0.45)

    def enemy_shoot(
        self,
        enemy: Enemy,
        direction: pygame.Vector2,
        damage: float,
        color: tuple[int, int, int],
        spread: float = 0.0,
    ) -> None:
        angles = [0.0] if spread <= 0 else [-spread, 0.0, spread]
        for angle in angles:
            fired = direction.rotate_rad(angle)
            self.bullets.append(
                Bullet(
                    pos=enemy.pos.copy(),
                    velocity=fired * (config.BULLET_SPEED * 0.62 * self.enemy_bullet_speed_multiplier),
                    damage=damage,
                    radius=config.BULLET_RADIUS + 1,
                    ttl=2.0,
                    pierce=0,
                    friendly=False,
                    color=color,
                )
            )

    def update_pickups(self, dt: float) -> None:
        collected: list[Pickup] = []
        room_clear_absorb = not self.enemies
        for pickup in self.pickups:
            pickup.hover_phase += dt * (6.5 if pickup.absorbing else 3.0)
            if room_clear_absorb:
                pickup.absorbing = True
                pickup.absorb_timer += dt
                delta = self.player_pos - pickup.pos
                distance = delta.length()
                if distance > 0:
                    speed = config.AUTO_ABSORB_BASE_SPEED + pickup.absorb_timer * config.AUTO_ABSORB_ACCEL
                    pickup.pos += delta.normalize() * min(speed * dt, distance)
            else:
                pickup.absorbing = False
                pickup.absorb_timer = 0.0
                delta = self.player_pos - pickup.pos
                distance = delta.length()
                if distance > 0:
                    if pickup.kind == "xp":
                        magnet_radius = self.pickup_radius
                        magnet_speed = config.XP_MAGNET_SPEED
                    elif pickup.kind == "credit":
                        magnet_radius = self.pickup_radius + 56
                        magnet_speed = config.CREDIT_MAGNET_SPEED
                    elif pickup.kind in ("heal", "shield"):
                        magnet_radius = max(88.0, self.pickup_radius * 0.72)
                        magnet_speed = config.SUPPORT_MAGNET_SPEED
                    else:
                        magnet_radius = max(80.0, self.pickup_radius * 0.62)
                        magnet_speed = config.ITEM_MAGNET_SPEED
                    if distance <= magnet_radius:
                        pickup.pos += delta.normalize() * min(magnet_speed * dt, distance)
            if pickup.pos.distance_to(self.player_pos) <= pickup.radius + config.PLAYER_RADIUS:
                collected.append(pickup)
                self.collect_pickup(pickup)
        for pickup in collected:
            if pickup in self.pickups:
                self.pickups.remove(pickup)

    def collect_pickup(self, pickup: Pickup) -> None:
        if pickup.kind == "xp":
            self.give_xp(pickup.amount)
            self.floaters.append(FloatingText(self.player_pos.copy(), f"+{pickup.amount} 经验", config.XP_COLOR, 0.45))
        else:
            self.apply_pickup_effect(pickup)

    def apply_pickup_effect(self, pickup: Pickup) -> None:
        if pickup.kind == "heal":
            self.player_hp = min(self.player_max_hp, self.player_hp + pickup.amount)
            self.floaters.append(FloatingText(self.player_pos.copy(), f"+{pickup.amount} 生命", config.HEAL_COLOR, 0.6))
        elif pickup.kind == "shield":
            self.player_shield = min(self.player_max_shield, self.player_shield + pickup.amount)
            self.floaters.append(FloatingText(self.player_pos.copy(), f"+{pickup.amount} 护盾", config.SHIELD_COLOR, 0.6))
        elif pickup.kind == "credit":
            gained = max(1, int(round(pickup.amount * self.credit_gain_multiplier)))
            self.credits += gained
            self.floaters.append(FloatingText(self.player_pos.copy(), f"+{gained} 晶片", config.CREDIT_COLOR, 0.6))
        elif pickup.kind == "item":
            effect = self.rng.choice(("damage", "speed", "cooldown", "shield"))
            if effect == "damage":
                self.player_damage += 2
                text = "道具：火力 +2"
            elif effect == "speed":
                self.player_speed += 8
                text = "道具：移速 +8"
            elif effect == "shield":
                self.player_shield = min(self.player_max_shield, self.player_shield + 12)
                text = "道具：护盾 +12"
            else:
                self.fire_cooldown = max(0.11, self.fire_cooldown * 0.98)
                text = "道具：射速提升"
            self.floaters.append(FloatingText(self.player_pos.copy(), text, config.ITEM_COLOR, 0.8))

    def absorb_all_pickups(self) -> None:
        for pickup in self.pickups[:]:
            pickup.absorbing = True
            self.collect_pickup(pickup)
            self.pickups.remove(pickup)

    def update_floaters(self, dt: float) -> None:
        remaining: list[FloatingText] = []
        for floater in self.floaters:
            floater.pos.y -= 36 * dt
            floater.ttl -= dt
            if floater.ttl > 0:
                remaining.append(floater)
        self.floaters = remaining

    def draw(self) -> None:
        self.screen.fill(config.BACKGROUND)
        if self.mode == "title":
            self.draw_title_menu()
            pygame.display.flip()
            return
        arena = self.arena_rect()
        pygame.draw.rect(self.screen, config.ARENA_FILL, arena, border_radius=12)
        pygame.draw.rect(self.screen, config.ARENA_BORDER, arena, width=3, border_radius=12)

        if self.room_layout is not None:
            for chamber in self.room_layout.chambers.values():
                pygame.draw.rect(self.screen, config.CHAMBER_OUTLINE, chamber.rect, 1, border_radius=12)
            for door in self.room_layout.doorways:
                pygame.draw.rect(self.screen, config.DOOR_GLOW, door.inflate(14, 14), border_radius=10)
                pygame.draw.rect(self.screen, config.DOOR_FILL, door, border_radius=8)
            self.draw_screen_doors()

        for cloud in self.gas_clouds:
            radius = int(cloud.radius)
            alpha = max(40, min(120, int(120 * (cloud.ttl / 2.6))))
            surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(surf, (110, 190, 90, alpha), (radius + 4, radius + 4), radius)
            pygame.draw.circle(surf, (150, 220, 130, alpha // 2), (radius + 4, radius + 4), max(10, radius - 10), 3)
            self.screen.blit(surf, surf.get_rect(center=cloud.pos))

        for obstacle in self.obstacles:
            rect = obstacle.rect
            fill = obstacle.fill_color if getattr(obstacle, "fill_color", None) is not None else (config.OBSTACLE_FILL if not obstacle.destructible else (95, 78, 58))
            border = obstacle.border_color if getattr(obstacle, "border_color", None) is not None else (config.OBSTACLE_BORDER if not obstacle.destructible else (194, 156, 106))
            radius = 6 if rect.width < 24 or rect.height < 24 else 10
            pygame.draw.rect(self.screen, fill, rect, border_radius=radius)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=radius)
            if obstacle.tag == "bullet":
                center = pygame.Vector2(rect.center)
                inner = max(4, min(rect.width, rect.height) // 4)
                pygame.draw.circle(self.screen, config.BULLET_BARREL_COLOR, center, inner, 2)
                pygame.draw.line(self.screen, config.BULLET_BARREL_COLOR, (rect.left + 5, center.y), (rect.right - 5, center.y), 2)
            elif obstacle.tag == "reactor":
                pygame.draw.circle(self.screen, config.BULLET_SHOCK_COLOR, rect.center, max(4, min(rect.width, rect.height) // 5), 2)
            elif obstacle.tag == "toxic":
                pygame.draw.circle(self.screen, (150, 220, 130), rect.center, max(4, min(rect.width, rect.height) // 5), 2)
            if obstacle.destructible and obstacle.max_hp > 0:
                ratio = max(0.0, obstacle.hp / obstacle.max_hp)
                bar = pygame.Rect(rect.left, rect.bottom + 4, rect.width, 5)
                pygame.draw.rect(self.screen, (48, 28, 20), bar, border_radius=3)
                pygame.draw.rect(self.screen, config.ITEM_COLOR, (bar.left, bar.top, bar.width * ratio, bar.height), border_radius=3)

        self.draw_explosion_waves()
        self.draw_room_specials()
        self.draw_enemy_telegraphs()

        for pickup in self.pickups:
            visual_pos = pickup.pos.copy()
            if not pickup.absorbing:
                visual_pos.y += math.sin(pickup.hover_phase * 3.2) * 2.5
            if pickup.absorbing:
                pygame.draw.line(self.screen, pickup.color, visual_pos, self.player_pos, 2)
                pygame.draw.circle(self.screen, pickup.color, visual_pos, pickup.radius + 5, 1)
            pygame.draw.circle(self.screen, pickup.color, visual_pos, pickup.radius)
            pygame.draw.circle(self.screen, (255, 255, 255), visual_pos, pickup.radius, 2)

        for bullet in self.bullets:
            pygame.draw.circle(self.screen, bullet.color, bullet.pos, bullet.radius)

        for enemy in self.enemies:
            pygame.draw.circle(self.screen, enemy.color, enemy.pos, enemy.radius)
            self.draw_actor_face(enemy.pos, enemy.radius, enemy.kind, is_boss=enemy.is_boss)
            hp_ratio = max(0.0, enemy.hp / enemy.max_hp)
            width = enemy.radius * 2
            top = enemy.pos.y - enemy.radius - 10
            pygame.draw.rect(self.screen, (40, 30, 30), (enemy.pos.x - enemy.radius, top, width, 5), border_radius=3)
            pygame.draw.rect(self.screen, (255, 100, 100), (enemy.pos.x - enemy.radius, top, width * hp_ratio, 5), border_radius=3)

        self.draw_laser_traces()

        player_color = config.PLAYER_HIT_COLOR if self.iframes > 0 else config.PLAYER_COLOR
        pygame.draw.circle(self.screen, player_color, self.player_pos, config.PLAYER_RADIUS)
        self.draw_actor_face(self.player_pos, config.PLAYER_RADIUS, "player")
        if self.pulse_timer > self.pulse_cooldown - 0.18:
            pygame.draw.circle(self.screen, config.BULLET_SHOCK_COLOR, self.player_pos, int(self.pulse_radius), 3)
        mouse = pygame.Vector2(pygame.mouse.get_pos())
        aim = mouse - self.player_pos
        if aim.length_squared() > 0:
            aim.scale_to_length(28)
            pygame.draw.line(self.screen, (200, 245, 230), self.player_pos, self.player_pos + aim, 4)

        for particle in self.particles:
            pygame.draw.circle(self.screen, particle.color, particle.pos, max(1, int(particle.radius)))

        for floater in self.floaters:
            surf = self.small_font.render(floater.text, True, floater.color)
            self.screen.blit(surf, surf.get_rect(center=floater.pos))

        self.draw_hud()
        self.draw_overlay()
        pygame.display.flip()

    def draw_actor_face(self, pos: pygame.Vector2, radius: int, kind: str, *, is_boss: bool = False) -> None:
        eye_color = (18, 20, 28)
        accent = (240, 244, 255)
        eye_dx = radius * 0.34
        eye_y = pos.y - radius * 0.14
        eye_size = max(2, int(radius * 0.12))

        if kind == "player":
            pygame.draw.circle(self.screen, accent, (int(pos.x - eye_dx), int(eye_y)), eye_size + 1)
            pygame.draw.circle(self.screen, accent, (int(pos.x + eye_dx), int(eye_y)), eye_size + 1)
            pygame.draw.circle(self.screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size)
            pygame.draw.circle(self.screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size)
            mouth_rect = pygame.Rect(0, 0, radius, max(8, radius // 2))
            mouth_rect.center = (int(pos.x), int(pos.y + radius * 0.18))
            pygame.draw.arc(self.screen, eye_color, mouth_rect, 0.15, math.pi - 0.15, 2)
            return

        if is_boss or kind == "boss":
            eye_w = radius * 0.48
            eye_h = radius * 0.30
            left_eye = pygame.Rect(0, 0, int(eye_w), int(eye_h))
            right_eye = pygame.Rect(0, 0, int(eye_w), int(eye_h))
            left_eye.center = (int(pos.x - eye_dx * 1.08), int(eye_y))
            right_eye.center = (int(pos.x + eye_dx * 1.08), int(eye_y))
            pygame.draw.arc(self.screen, eye_color, left_eye, math.pi, math.tau, 3)
            pygame.draw.arc(self.screen, eye_color, right_eye, math.pi, math.tau, 3)
            pygame.draw.line(self.screen, eye_color, (left_eye.left - 2, left_eye.top + 2), (left_eye.right + 2, left_eye.top - 4), 3)
            pygame.draw.line(self.screen, eye_color, (right_eye.left - 2, right_eye.top - 4), (right_eye.right + 2, right_eye.top + 2), 3)
            mouth_rect = pygame.Rect(0, 0, int(radius * 0.92), max(10, int(radius * 0.42)))
            mouth_rect.center = (int(pos.x), int(pos.y + radius * 0.34))
            pygame.draw.arc(self.screen, eye_color, mouth_rect, math.pi + 0.25, math.tau - 0.25, 3)
            return

        if kind == "shooter":
            pygame.draw.circle(self.screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size)
            pygame.draw.circle(self.screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size)
            pygame.draw.circle(self.screen, eye_color, (int(pos.x), int(pos.y + radius * 0.20)), max(2, eye_size - 1), 1)
            return

        if kind == "laser":
            left_eye = (int(pos.x - eye_dx), int(eye_y))
            right_eye = (int(pos.x + eye_dx), int(eye_y))
            pygame.draw.line(self.screen, eye_color, (left_eye[0] - eye_size, left_eye[1]), (left_eye[0] + eye_size, left_eye[1]), 3)
            pygame.draw.line(self.screen, eye_color, (right_eye[0] - eye_size, right_eye[1]), (right_eye[0] + eye_size, right_eye[1]), 3)
            pygame.draw.line(self.screen, eye_color, (int(pos.x - radius * 0.18), int(pos.y + radius * 0.24)), (int(pos.x + radius * 0.18), int(pos.y + radius * 0.24)), 2)
            return

        if kind in {"charger", "elite"}:
            pygame.draw.line(self.screen, eye_color, (int(pos.x - eye_dx - eye_size), int(eye_y - 2)), (int(pos.x - eye_dx + eye_size), int(eye_y + 2)), 3)
            pygame.draw.line(self.screen, eye_color, (int(pos.x + eye_dx - eye_size), int(eye_y + 2)), (int(pos.x + eye_dx + eye_size), int(eye_y - 2)), 3)
            pygame.draw.arc(self.screen, eye_color, pygame.Rect(int(pos.x - radius * 0.34), int(pos.y + radius * 0.04), int(radius * 0.68), max(8, int(radius * 0.36))), math.pi + 0.15, math.tau - 0.15, 2)
            return

        pygame.draw.circle(self.screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size)
        pygame.draw.circle(self.screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size)
        pygame.draw.line(self.screen, eye_color, (int(pos.x - radius * 0.18), int(pos.y + radius * 0.22)), (int(pos.x + radius * 0.18), int(pos.y + radius * 0.22)), 2)

    def draw_screen_doors(self) -> None:
        if self.room_layout is None or self.current_room_state is None:
            return
        locked = self.current_room_state.doors_locked
        door_marks = {"north": "↑", "east": "→", "south": "↓", "west": "←"}
        for direction, rect in self.room_layout.screen_doors.items():
            fill = (155, 66, 66) if locked else config.DOOR_FILL
            glow = (210, 96, 96) if locked else config.DOOR_GLOW
            pygame.draw.rect(self.screen, glow, rect.inflate(14, 14), border_radius=12)
            pygame.draw.rect(self.screen, fill, rect, border_radius=8)
            if not locked:
                arrow = self.small_font.render(door_marks[direction], True, config.TEXT_COLOR)
                self.screen.blit(arrow, arrow.get_rect(center=rect.center))

    def draw_enemy_telegraphs(self) -> None:
        for enemy in self.enemies:
            if enemy.kind != "laser" or enemy.aim_direction.length_squared() <= 0:
                continue
            telegraph_window, lock_window = self.get_enemy_laser_timing(enemy)
            if not (0 < enemy.shoot_timer <= telegraph_window):
                continue
            points, _ = self.trace_beam(enemy.pos, enemy.aim_direction, 3)
            locked = enemy.shoot_timer <= lock_window
            color = config.ENEMY_LASER_LOCK_COLOR if locked else config.ENEMY_LASER_COLOR
            width = 3 if locked else 2
            for start, end in zip(points, points[1:]):
                pygame.draw.line(self.screen, color, start, end, width)
            pygame.draw.circle(self.screen, color, enemy.pos, enemy.radius + 4, 1)

    def draw_explosion_waves(self) -> None:
        if not self.explosion_waves:
            return
        overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        for wave in self.explosion_waves:
            life = max(0.0, min(1.0, wave.ttl / max(0.01, wave.max_ttl)))
            radius = int(wave.radius * (0.55 + 0.45 * (1.0 - life)))
            fill_alpha = int(26 + 44 * life)
            ring_alpha = int(110 + 90 * life)
            ring_width = max(3, int(8 * life) + 2)
            pygame.draw.circle(overlay, (*wave.color, fill_alpha), wave.pos, radius)
            pygame.draw.circle(overlay, (*config.LASER_TRACE_CORE, ring_alpha), wave.pos, radius, ring_width)
            pygame.draw.circle(overlay, (*wave.color, min(255, ring_alpha + 25)), wave.pos, max(12, radius - ring_width * 2), 2)
        self.screen.blit(overlay, (0, 0))

    def draw_laser_traces(self) -> None:
        if not self.laser_traces:
            return
        overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        for trace in self.laser_traces:
            life = max(0.0, min(1.0, trace.ttl / max(0.01, trace.max_ttl)))
            outer_width = trace.width + max(4, int(8 * life))
            mid_width = trace.width + max(2, int(4 * life))
            core_width = max(2, trace.width // 2)
            for start, end in zip(trace.points, trace.points[1:]):
                segment = end - start
                offset = pygame.Vector2()
                if segment.length_squared() > 0:
                    offset = pygame.Vector2(-segment.y, segment.x)
                    offset.scale_to_length(max(0.8, trace.width * 0.12 * life))
                pygame.draw.line(overlay, (*trace.color, int(58 + 82 * life)), start, end, outer_width)
                pygame.draw.line(overlay, (*config.LASER_TRACE_CORE, int(110 + 105 * life)), start + offset, end + offset, mid_width)
                pygame.draw.line(overlay, (*config.LASER_TRACE_CORE, int(96 + 92 * life)), start - offset, end - offset, mid_width)
                pygame.draw.line(overlay, (*trace.color, int(170 + 70 * life)), start, end, core_width)
            muzzle = trace.points[0]
            pygame.draw.circle(overlay, (*trace.color, int(130 + 80 * life)), muzzle, max(8, trace.width), 0)
            for impact in trace.impact_points:
                impact_radius = max(trace.width + 4, 10)
                pygame.draw.circle(overlay, (*config.LASER_TRACE_CORE, int(118 + 105 * life)), impact, impact_radius)
                pygame.draw.circle(overlay, (*trace.color, int(178 + 65 * life)), impact, max(4, impact_radius // 2), 2)
        self.screen.blit(overlay, (0, 0))

    def draw_room_specials(self) -> None:
        room = self.current_room_state
        if room is None:
            return
        if room.room_type == "shop":
            for offer in room.shop_offers:
                fill = (58, 62, 86) if not offer.sold else (52, 48, 48)
                border = config.CREDIT_COLOR if not offer.sold else (120, 120, 120)
                panel = pygame.Rect(0, 0, 140, 94)
                panel.center = (offer.pos.x, offer.pos.y + 18)
                pygame.draw.rect(self.screen, fill, panel, border_radius=16)
                pygame.draw.rect(self.screen, border, panel, 2, border_radius=16)
                orb_color = config.CREDIT_COLOR if offer.key != "shield_charge" else config.SHIELD_COLOR
                pygame.draw.circle(self.screen, orb_color, offer.pos, 18)
                name = self.small_font.render(offer.name, True, config.TEXT_COLOR)
                cost = self.small_font.render(f"{offer.cost} 晶片", True, border)
                self.screen.blit(name, name.get_rect(center=(panel.centerx, panel.top + 48)))
                label = "已售出" if offer.sold else cost
                if not offer.sold:
                    self.screen.blit(cost, cost.get_rect(center=(panel.centerx, panel.bottom - 18)))
                else:
                    sold = self.small_font.render("已售出", True, config.MUTED_TEXT)
                    self.screen.blit(sold, sold.get_rect(center=(panel.centerx, panel.bottom - 18)))
        elif room.room_type == "treasure" and not room.chest_opened:
            pos = self.get_room_feature_anchor(room)
            chest = pygame.Rect(0, 0, 68, 48)
            chest.center = pos
            pygame.draw.rect(self.screen, (118, 88, 38), chest, border_radius=10)
            pygame.draw.rect(self.screen, config.CREDIT_COLOR, chest, 3, border_radius=10)
            pygame.draw.rect(self.screen, (255, 236, 150), (chest.left, chest.centery - 4, chest.width, 8), border_radius=4)
        elif room.room_type == "boss" and room.exit_active:
            pos = self.get_room_feature_anchor(room)
            pygame.draw.circle(self.screen, (110, 170, 255), pos, 34, 3)
            pygame.draw.circle(self.screen, (70, 120, 210), pos, 18, 2)
            text = self.small_font.render("出口", True, config.TEXT_COLOR)
            self.screen.blit(text, text.get_rect(center=(pos.x, pos.y + 54)))

    def draw_hud(self) -> None:
        hp_ratio = self.player_hp / self.player_max_hp
        shield_ratio = 0.0 if self.player_max_shield <= 0 else self.player_shield / self.player_max_shield
        xp_ratio = self.xp / self.xp_to_level
        room_label = self.room_type_label(self.current_room_state.room_type) if self.current_room_state is not None else "未进入房间"
        pygame.draw.rect(self.screen, config.PANEL, (20, 18, 360, 128), border_radius=12)
        pygame.draw.rect(self.screen, (48, 30, 30), (34, 38, 240, 16), border_radius=8)
        pygame.draw.rect(self.screen, (80, 220, 145), (34, 38, 240 * hp_ratio, 16), border_radius=8)
        pygame.draw.rect(self.screen, (26, 42, 76), (34, 61, 240, 12), border_radius=6)
        pygame.draw.rect(self.screen, (112, 198, 255), (34, 61, 240 * shield_ratio, 12), border_radius=6)
        pygame.draw.rect(self.screen, (38, 48, 82), (34, 80, 240, 14), border_radius=7)
        pygame.draw.rect(self.screen, (98, 168, 255), (34, 80, 240 * xp_ratio, 14), border_radius=7)

        info = [
            f"生命 {int(self.player_hp)}/{int(self.player_max_hp)}",
            f"护盾 {int(self.player_shield)}/{int(self.player_max_shield)}",
            f"等级 {self.level}",
            f"晶片 {self.credits}",
        ]
        for idx, text in enumerate(info):
            surf = self.small_font.render(text, True, config.TEXT_COLOR)
            self.screen.blit(surf, (34 + idx * 76, 10))

        floor_info = self.small_font.render(f"楼层 {self.floor_index}   当前 {room_label}   击杀 {self.kills}", True, config.MUTED_TEXT)
        self.screen.blit(floor_info, (34, 102))
        loadout = self.small_font.render(
            f"机体 {self.selected_character.name}   武器 {self.selected_weapon.name}   已清战斗房 {self.rooms_cleared}",
            True,
            config.MUTED_TEXT,
        )
        self.screen.blit(loadout, (34, 118))

        if self.weapon_mode == "laser":
            weapon_text = f"武器 {self.selected_weapon.name}  伤害 {int(self.player_damage)}  射速 {self.fire_cooldown:.2f}s  宽度 {self.player_beam_width}  暴击 {int(self.player_crit_chance * 100)}%"
            if self.player_bullet_bounces > 0:
                weapon_text += f"  反射 {self.player_bullet_bounces}"
        else:
            weapon_text = (
                f"武器 {self.selected_weapon.name}  伤害 {int(self.player_damage)}  射速 {self.fire_cooldown:.2f}s"
                f"  准度 {self.get_accuracy_rating()}%  暴击 {int(self.player_crit_chance * 100)}%  穿透 {self.bullet_pierce}"
            )
            if self.multishot > 0:
                weapon_text += f"  散射 {self.multishot}"
            if self.player_bullet_bounces > 0:
                weapon_text += f"  反弹 {self.player_bullet_bounces}"
        weapons = self.small_font.render(weapon_text, True, config.MUTED_TEXT)
        self.screen.blit(weapons, (20, config.HEIGHT - 34))

        dash_text = "就绪" if self.dash_timer <= 0 else f"{self.dash_timer:.1f}s"
        pulse_text = "就绪" if self.pulse_timer <= 0 else f"{self.pulse_timer:.1f}s"
        skills = self.small_font.render(f"冲刺 {dash_text}  脉冲 {pulse_text}", True, config.MUTED_TEXT)
        self.screen.blit(skills, (20, config.HEIGHT - 58))
        prompt = self.current_interaction_prompt()
        if prompt:
            prompt_surf = self.font.render(prompt, True, config.PLAYER_HIT_COLOR)
            self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(config.WIDTH / 2, config.HEIGHT - 52)))
        self.draw_minimap()

    def draw_minimap(self) -> None:
        if self.floor_map is None:
            return
        panel = pygame.Rect(config.WIDTH - 190, 18, 160, 118)
        pygame.draw.rect(self.screen, config.PANEL, panel, border_radius=12)
        pygame.draw.rect(self.screen, config.ARENA_BORDER, panel, 2, border_radius=12)
        coords = [room.coord for room in self.room_states.values()]
        xs = [coord[0] for coord in coords]
        ys = [coord[1] for coord in coords]
        cell_size = 22
        origin_x = panel.centerx - ((max(xs) - min(xs) + 1) * cell_size) / 2
        origin_y = panel.centery - ((max(ys) - min(ys) + 1) * cell_size) / 2 + 8
        for room in self.room_states.values():
            x = origin_x + (room.coord[0] - min(xs)) * cell_size
            y = origin_y + (room.coord[1] - min(ys)) * cell_size
            rect = pygame.Rect(x, y, 16, 16)
            color = (90, 219, 170) if room.visited else (74, 78, 96)
            if room.room_type == "shop":
                color = config.CREDIT_COLOR if room.visited else (110, 98, 72)
            elif room.room_type == "treasure":
                color = (255, 180, 88) if room.visited else (104, 86, 66)
            elif room.room_type == "elite":
                color = (255, 130, 96) if room.visited else (112, 74, 66)
            elif room.room_type == "boss":
                color = (255, 84, 84) if room.visited else (96, 58, 58)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            if room.room_id == self.current_room_id:
                pygame.draw.rect(self.screen, (255, 255, 255), rect.inflate(6, 6), 2, border_radius=5)
        title = self.small_font.render("楼层地图", True, config.MUTED_TEXT)
        self.screen.blit(title, (panel.left + 12, panel.top + 8))

    def draw_overlay(self) -> None:
        if self.mode == "title":
            self.draw_title_menu()
        elif self.mode == "paused":
            self.draw_pause_menu()
        elif self.mode == "dead":
            self.draw_dead_menu()
        elif self.mode == "level_up":
            self.draw_level_up()
        elif self.mode == "reward_room":
            self.draw_reward_room()
        elif self.mode == "supply_room":
            self.draw_supply_room()
        elif self.room_clear_delay > 0:
            title = "战利品回收中" if self.pickups else "区域已清空"
            surf = self.big_font.render(title, True, config.TEXT_COLOR)
            self.screen.blit(surf, surf.get_rect(center=(config.WIDTH / 2, 54)))

    def draw_center_card(self, title: str, subtitle: str, prompt: str) -> None:
        panel = pygame.Rect(0, 0, 520, 240)
        panel.center = (config.WIDTH / 2, config.HEIGHT / 2)
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 130))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, config.PANEL, panel, border_radius=18)
        pygame.draw.rect(self.screen, config.ARENA_BORDER, panel, 3, border_radius=18)
        texts = [
            self.big_font.render(title, True, config.TEXT_COLOR),
            self.font.render(subtitle, True, config.MUTED_TEXT),
            self.font.render(prompt, True, config.PLAYER_COLOR),
        ]
        ys = [panel.top + 48, panel.top + 112, panel.top + 170]
        for surf, y in zip(texts, ys):
            self.screen.blit(surf, surf.get_rect(center=(panel.centerx, y)))

    def draw_level_up(self) -> None:
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 165))
        self.screen.blit(shade, (0, 0))
        title = self.big_font.render("选择增益", True, config.TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(config.WIDTH / 2, 110)))
        prompt = self.font.render("按 1 / 2 / 3 或点击卡片", True, config.MUTED_TEXT)
        self.screen.blit(prompt, prompt.get_rect(center=(config.WIDTH / 2, 150)))
        mouse_pos = pygame.mouse.get_pos()
        for idx, (upgrade, rect) in enumerate(zip(self.upgrade_choices, self.get_choice_rects())):
            pygame.draw.rect(self.screen, config.CARD, rect, border_radius=18)
            border = config.PLAYER_COLOR if rect.collidepoint(mouse_pos) else config.CARD_HILITE
            pygame.draw.rect(self.screen, border, rect, 3, border_radius=18)
            num = self.big_font.render(str(idx + 1), True, config.PLAYER_COLOR)
            name = self.font.render(upgrade.name, True, config.TEXT_COLOR)
            desc = self.small_font.render(upgrade.description, True, config.MUTED_TEXT)
            self.screen.blit(num, (rect.left + 20, rect.top + 12))
            self.screen.blit(name, (rect.left + 24, rect.top + 78))
            self.screen.blit(desc, (rect.left + 24, rect.top + 120))

    def draw_reward_room(self) -> None:
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 155))
        self.screen.blit(shade, (0, 0))
        title_text = "宝箱奖励" if self.reward_source == "treasure" else "奖励房"
        sub_text = "打开宝箱后选择一个强化：点击或按 1 / 2 / 3" if self.reward_source == "treasure" else "免费获得一个强化：点击或按 1 / 2 / 3"
        title = self.big_font.render(title_text, True, config.TEXT_COLOR)
        sub = self.font.render(sub_text, True, config.MUTED_TEXT)
        self.screen.blit(title, title.get_rect(center=(config.WIDTH / 2, 102)))
        self.screen.blit(sub, sub.get_rect(center=(config.WIDTH / 2, 146)))
        mouse_pos = pygame.mouse.get_pos()
        for idx, (upgrade, rect) in enumerate(zip(self.reward_choices, self.get_choice_rects())):
            pygame.draw.rect(self.screen, config.CARD, rect, border_radius=18)
            border = config.PLAYER_HIT_COLOR if rect.collidepoint(mouse_pos) else config.PLAYER_COLOR
            pygame.draw.rect(self.screen, border, rect, 3, border_radius=18)
            num = self.big_font.render(str(idx + 1), True, config.PLAYER_COLOR)
            name = self.font.render(upgrade.name, True, config.TEXT_COLOR)
            desc = self.small_font.render(upgrade.description, True, config.MUTED_TEXT)
            self.screen.blit(num, (rect.left + 20, rect.top + 12))
            self.screen.blit(name, (rect.left + 24, rect.top + 78))
            self.screen.blit(desc, (rect.left + 24, rect.top + 120))

    def draw_supply_room(self) -> None:
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 155))
        self.screen.blit(shade, (0, 0))
        title = self.big_font.render("补给房", True, config.TEXT_COLOR)
        sub = self.font.render("选择一项补给：点击或按 1 / 2 / 3", True, config.MUTED_TEXT)
        self.screen.blit(title, title.get_rect(center=(config.WIDTH / 2, 102)))
        self.screen.blit(sub, sub.get_rect(center=(config.WIDTH / 2, 146)))
        mouse_pos = pygame.mouse.get_pos()
        for idx, (option, rect) in enumerate(zip(self.supply_choices, self.get_choice_rects())):
            pygame.draw.rect(self.screen, config.CARD, rect, border_radius=18)
            border = config.XP_COLOR if rect.collidepoint(mouse_pos) else config.CARD_HILITE
            pygame.draw.rect(self.screen, border, rect, 3, border_radius=18)
            num = self.big_font.render(str(idx + 1), True, config.PLAYER_COLOR)
            name = self.font.render(option.name, True, config.TEXT_COLOR)
            desc = self.small_font.render(option.description, True, config.MUTED_TEXT)
            self.screen.blit(num, (rect.left + 20, rect.top + 12))
            self.screen.blit(name, (rect.left + 24, rect.top + 78))
            self.screen.blit(desc, (rect.left + 24, rect.top + 120))

    def draw_title_menu(self) -> None:
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 152))
        self.screen.blit(shade, (0, 0))
        title = self.big_font.render("\u94a2\u94c1\u8702\u5de2", True, config.TEXT_COLOR)
        sub = self.small_font.render("\u4e3b\u83dc\u5355\u5df2\u62c6\u5206\u4e3a\u72ec\u7acb\u914d\u7f6e\u9875\u3002\u56de\u8f66 / Space \u5f00\u59cb\u3002", True, config.MUTED_TEXT)
        self.screen.blit(title, title.get_rect(midleft=(44, 48)))
        self.screen.blit(sub, sub.get_rect(midleft=(46, 80)))
        mouse_pos = pygame.mouse.get_pos()
        panel = self.get_title_info_panel()
        pygame.draw.rect(self.screen, config.PANEL, panel, border_radius=18)
        pygame.draw.rect(self.screen, config.ARENA_BORDER, panel, 2, border_radius=18)

        if self.title_panel == "main":
            left_panel = pygame.Rect(28, 112, 368, 560)
            pygame.draw.rect(self.screen, config.PANEL, left_panel, border_radius=18)
            pygame.draw.rect(self.screen, config.ARENA_BORDER, left_panel, 2, border_radius=18)
            btns = self.get_title_menu_buttons()
            items = (
                ("stage", "1 \u5173\u5361\u9009\u62e9", self.selected_stage.name, self.selected_stage.description, config.PLAYER_COLOR),
                ("character", "2 \u89d2\u8272\u9009\u62e9", self.selected_character.name, self.selected_character.passive, config.SHIELD_COLOR),
                ("weapon", "3 \u6b66\u5668\u9009\u62e9", self.selected_weapon.name, self.selected_weapon.passive, config.CREDIT_COLOR),
            )
            for key, title_text, selected_name, desc, color in items:
                rect = btns[key]
                hovered = rect.collidepoint(mouse_pos)
                border = color if hovered else config.CARD_HILITE
                pygame.draw.rect(self.screen, config.CARD, rect, border_radius=14)
                pygame.draw.rect(self.screen, border, rect, 2, border_radius=14)
                self.screen.blit(self.small_font.render(title_text, True, border), (rect.left + 12, rect.top + 8))
                self.screen.blit(self.font.render(selected_name, True, config.TEXT_COLOR), (rect.left + 12, rect.top + 24))
                self.screen.blit(self.small_font.render(self.wrap_text(desc, self.small_font, rect.width - 24, 1)[0], True, config.MUTED_TEXT), (rect.left + 12, rect.top + 45))

            record_card = pygame.Rect(44, 420, 338, 122)
            pygame.draw.rect(self.screen, config.CARD, record_card, border_radius=14)
            pygame.draw.rect(self.screen, config.CARD_HILITE, record_card, 2, border_radius=14)
            self.screen.blit(self.small_font.render("\u5386\u53f2\u7eaa\u5f55", True, config.MUTED_TEXT), (record_card.left + 12, record_card.top + 8))
            for idx, line in enumerate((f"\u6700\u9ad8\u5206\uff1a{self.best_record['best_score']}", f"\u6700\u9ad8\u697c\u5c42\uff1a{self.best_record['best_floor']}", f"\u6700\u9ad8\u6e05\u623f\uff1a{self.best_record['best_rooms']}")):
                self.screen.blit(self.font.render(line, True, config.TEXT_COLOR), (record_card.left + 12, record_card.top + 28 + idx * 26))

            deploy_card = pygame.Rect(panel.left + 16, panel.top + 16, panel.width - 32, 86)
            pygame.draw.rect(self.screen, config.CARD, deploy_card, border_radius=14)
            pygame.draw.rect(self.screen, config.CARD_HILITE, deploy_card, 2, border_radius=14)
            self.screen.blit(self.font.render("当前部署", True, config.TEXT_COLOR), (deploy_card.left + 14, deploy_card.top + 10))
            deploy_lines = (
                f"关卡：{self.selected_stage.name}",
                f"机体：{self.selected_character.name}",
                f"武器：{self.selected_weapon.name}",
            )
            for idx, line in enumerate(deploy_lines):
                self.screen.blit(self.small_font.render(line, True, config.MUTED_TEXT), (deploy_card.left + 14 + idx * 210, deploy_card.top + 44))

            detail_width = (panel.width - 48) // 2
            for idx, (title_text, name_text, desc_text) in enumerate(self.title_detail_sections()):
                col = idx % 2
                row = idx // 2
                card = pygame.Rect(panel.left + 16 + col * (detail_width + 16), panel.top + 118 + row * 100, detail_width, 84)
                pygame.draw.rect(self.screen, config.CARD, card, border_radius=14)
                pygame.draw.rect(self.screen, config.CARD_HILITE, card, 2, border_radius=14)
                self.screen.blit(self.small_font.render(title_text, True, config.MUTED_TEXT), (card.left + 12, card.top + 8))
                self.screen.blit(self.font.render(name_text, True, config.TEXT_COLOR), (card.left + 12, card.top + 24))
                for line_no, wrapped in enumerate(self.wrap_text(desc_text, self.small_font, card.width - 22, 2)):
                    self.screen.blit(self.small_font.render(wrapped, True, config.MUTED_TEXT), (card.left + 12, card.top + 48 + line_no * 16))

            skills_card = pygame.Rect(panel.left + 16, panel.top + 336, panel.width - 32, 78)
            pygame.draw.rect(self.screen, config.CARD, skills_card, border_radius=14)
            pygame.draw.rect(self.screen, config.CARD_HILITE, skills_card, 2, border_radius=14)
            self.screen.blit(self.small_font.render("\u57fa\u7840\u64cd\u4f5c", True, config.MUTED_TEXT), (skills_card.left + 12, skills_card.top + 8))
            for idx, line in enumerate(TITLE_SKILLS):
                col = idx % 2
                row = idx // 2
                self.screen.blit(self.small_font.render(line, True, config.TEXT_COLOR), (skills_card.left + 12 + col * 214, skills_card.top + 28 + row * 18))

            action_card = pygame.Rect(panel.left + 16, panel.bottom - 90, panel.width - 32, 66)
            pygame.draw.rect(self.screen, config.CARD, action_card, border_radius=14)
            pygame.draw.rect(self.screen, config.CARD_HILITE, action_card, 2, border_radius=14)
            hint = self.small_font.render("确认配置后，按 Enter / Space 或点击右侧按钮开始部署", True, config.MUTED_TEXT)
            self.screen.blit(hint, hint.get_rect(midleft=(action_card.left + 16, action_card.centery)))

            start_rect = self.get_title_start_button()
            hovered = start_rect.collidepoint(mouse_pos)
            fill = config.PLAYER_COLOR if hovered else config.CARD_HILITE
            pygame.draw.rect(self.screen, fill, start_rect, border_radius=16)
            pygame.draw.rect(self.screen, (240, 248, 255), start_rect, 2, border_radius=16)
            label = self.font.render("\u5f00\u59cb\u90e8\u7f72", True, (15, 18, 28))
            self.screen.blit(label, label.get_rect(center=start_rect.center))
        else:
            title_text, subtitle = TITLE_PANEL_INFO[self.title_panel]
            header = pygame.Rect(44, 116, 1192, 60)
            pygame.draw.rect(self.screen, config.CARD, header, border_radius=16)
            pygame.draw.rect(self.screen, config.CARD_HILITE, header, 2, border_radius=16)
            self.screen.blit(self.font.render(title_text, True, config.TEXT_COLOR), (header.left + 18, header.top + 10))
            self.screen.blit(self.small_font.render(subtitle, True, config.MUTED_TEXT), (header.left + 18, header.top + 34))
            options = self.current_title_options()
            selected_key = self.selected_stage.key if self.title_panel == "stage" else self.selected_character.key if self.title_panel == "character" else self.selected_weapon.key
            for idx, (option, rect) in enumerate(zip(options, self.get_title_panel_option_rects(len(options)))):
                active = option.key == selected_key
                hovered = rect.collidepoint(mouse_pos)
                border = config.PLAYER_COLOR if active else (config.CREDIT_COLOR if hovered else config.CARD_HILITE)
                pygame.draw.rect(self.screen, config.CARD, rect, border_radius=16)
                pygame.draw.rect(self.screen, border, rect, 2, border_radius=16)
                self.screen.blit(self.small_font.render(str(idx + 1), True, border), (rect.left + 16, rect.top + 14))
                self.screen.blit(self.font.render(option.name, True, config.TEXT_COLOR), (rect.left + 48, rect.top + 10))
                self.screen.blit(self.small_font.render(option.description, True, config.MUTED_TEXT), (rect.left + 48, rect.top + 38))
                passive = option.passive if hasattr(option, "passive") else f"\u8d77\u59cb\u96be\u5ea6\uff1a{option.start_room}"
                self.screen.blit(self.small_font.render(passive, True, config.TEXT_COLOR), (rect.left + 48, rect.top + 58))
            self.draw_action_button(self.get_title_panel_back_button(), "\u8fd4\u56de")
            self.draw_action_button(self.get_title_panel_start_button(), "\u5f00\u5c40")

    def draw_pause_menu(self) -> None:
        self.draw_center_card("\u5df2\u6682\u505c", "\u70b9\u51fb\u6309\u94ae\u6216\u6309\u952e\u7ee7\u7eed\u64cd\u4f5c", "ESC \u7ee7\u7eed")
        labels = ["\u7ee7\u7eed", "\u91cd\u5f00", "\u83dc\u5355"]
        for rect, label in zip(self.get_center_action_buttons(3), labels):
            self.draw_action_button(rect, label)

    def draw_dead_menu(self) -> None:
        current_score = self.calculate_score()
        self.draw_center_card(
            "\u672c\u5c40\u5931\u8d25",
            f"\u5206\u6570\uff1a{current_score}    \u6e05\u623f\uff1a{self.rooms_cleared}    \u51fb\u6740\uff1a{self.kills}    \u697c\u5c42\uff1a{self.floor_index}",
            f"\u6700\u9ad8\u5206 {self.best_record['best_score']} / \u6700\u9ad8\u5c42 {self.best_record['best_floor']}",
        )
        labels = ["\u91cd\u5f00", "\u83dc\u5355"]
        for rect, label in zip(self.get_center_action_buttons(2), labels):
            self.draw_action_button(rect, label)

    def draw_action_button(self, rect: pygame.Rect, label: str) -> None:
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        fill = config.CARD_HILITE if hovered else config.CARD
        border = config.PLAYER_COLOR if hovered else config.ARENA_BORDER
        pygame.draw.rect(self.screen, fill, rect, border_radius=12)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=12)
        text = self.font.render(label, True, config.TEXT_COLOR)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def clamp_circle_to_arena(self, pos: pygame.Vector2, radius: int) -> None:
        arena = self.arena_rect()
        pos.x = max(arena.left + radius, min(arena.right - radius, pos.x))
        pos.y = max(arena.top + radius, min(arena.bottom - radius, pos.y))

    def damage_player(self, amount: float, color: tuple[int, int, int], iframe_duration: float) -> None:
        self.iframes = iframe_duration
        remaining = amount
        if self.player_shield > 0:
            absorbed = min(self.player_shield, remaining)
            self.player_shield -= absorbed
            remaining -= absorbed
            self.floaters.append(FloatingText(self.player_pos.copy() + pygame.Vector2(0, -20), f"护盾 -{int(absorbed)}", config.SHIELD_COLOR, 0.45))
        if remaining > 0:
            self.player_hp -= remaining
            self.floaters.append(FloatingText(self.player_pos.copy(), f"-{int(remaining)}", color, 0.5))
        if self.player_hp <= 0:
            self.player_hp = 0
            self.update_best_record()
            self.mode = "dead"
            self.message = "信号中断"

    def get_enemy_navigation_target(self, pos: pygame.Vector2) -> tuple[pygame.Vector2, bool]:
        if self.room_layout is None or len(self.room_layout.chambers) <= 1:
            return self.player_pos.copy(), True
        if self.has_line_of_sight(pos, self.player_pos, 6):
            return self.player_pos.copy(), True
        enemy_cell = self.room_layout.closest_cell(pos)
        player_cell = self.room_layout.closest_cell(self.player_pos)
        if enemy_cell is None or player_cell is None or enemy_cell == player_cell:
            return self.player_pos.copy(), True
        path = self.room_layout.path_between(enemy_cell, player_cell)
        if len(path) >= 2:
            door = self.room_layout.door_between(path[0], path[1])
            if door is not None:
                next_center = self.room_layout.chambers[path[1]].center if path[1] in self.room_layout.chambers else self.player_pos
                return door.lerp(next_center, 0.2), False
        return self.player_pos.copy(), False

    def has_line_of_sight(self, start: pygame.Vector2, end: pygame.Vector2, radius: int = 4) -> bool:
        delta = end - start
        distance = delta.length()
        if distance <= 0:
            return True
        steps = max(1, int(distance / 12))
        for step in range(1, steps + 1):
            sample = start.lerp(end, step / steps)
            if any(self.circle_intersects_rect(sample, radius, rect) for rect in self.obstacle_rects()):
                return False
        return True

    def move_circle_with_collisions(self, pos: pygame.Vector2, radius: int, delta: pygame.Vector2) -> None:
        if delta.length_squared() <= 0:
            self.clamp_circle_to_arena(pos, radius)
            self.push_circle_out_of_obstacles(pos, radius)
            return
        steps = max(1, int(delta.length() / config.COLLISION_STEP) + 1)
        step = delta / steps
        for _ in range(steps):
            if step.x != 0:
                trial = pygame.Vector2(pos.x + step.x, pos.y)
                self.clamp_circle_to_arena(trial, radius)
                if not self.position_hits_obstacle(trial, radius):
                    pos.x = trial.x
            if step.y != 0:
                trial = pygame.Vector2(pos.x, pos.y + step.y)
                self.clamp_circle_to_arena(trial, radius)
                if not self.position_hits_obstacle(trial, radius):
                    pos.y = trial.y
        self.clamp_circle_to_arena(pos, radius)
        self.push_circle_out_of_obstacles(pos, radius)

    def position_hits_obstacle(self, pos: pygame.Vector2, radius: int) -> bool:
        return any(self.circle_intersects_rect(pos, radius, obstacle.rect) for obstacle in self.obstacles)

    def push_circle_out_of_obstacles(self, pos: pygame.Vector2, radius: int) -> None:
        for _ in range(4):
            collided = False
            for obstacle in self.obstacles:
                rect = obstacle.rect
                if not self.circle_intersects_rect(pos, radius, rect):
                    continue
                collided = True
                nearest_x = max(rect.left, min(pos.x, rect.right))
                nearest_y = max(rect.top, min(pos.y, rect.bottom))
                offset = pygame.Vector2(pos.x - nearest_x, pos.y - nearest_y)
                if offset.length_squared() > 0:
                    distance = offset.length()
                    pos += offset.normalize() * max(0.0, radius - distance + 0.5)
                else:
                    pushes = (
                        pygame.Vector2(rect.left - radius - pos.x, 0),
                        pygame.Vector2(rect.right + radius - pos.x, 0),
                        pygame.Vector2(0, rect.top - radius - pos.y),
                        pygame.Vector2(0, rect.bottom + radius - pos.y),
                    )
                    pos += min(pushes, key=lambda item: abs(item.x) + abs(item.y))
                self.clamp_circle_to_arena(pos, radius)
            if not collided:
                return

    def circle_intersects_rect(self, pos: pygame.Vector2, radius: int, rect: pygame.Rect) -> bool:
        nearest_x = max(rect.left, min(pos.x, rect.right))
        nearest_y = max(rect.top, min(pos.y, rect.bottom))
        dx = pos.x - nearest_x
        dy = pos.y - nearest_y
        return dx * dx + dy * dy <= radius * radius

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


def run() -> None:
    Game().run()
