from __future__ import annotations

import json
import math
import random
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

import pygame

from . import config
from .balance import (
    SHOP_OFFER_POOL,
    boss_floor_hp_multiplier,
    enemy_attack_cooldown,
    enemy_credit_drop,
    enemy_scaling,
    hazard_profile,
    nuke_event_profile,
    obstacle_credit_drop,
    reward_credit_drop,
    scale_shop_cost,
)
from .content import (
    CHARACTERS,
    CHARACTER_PROFILES,
    CHARACTER_SKILLS,
    PLAYER_BUFFS,
    STAGES,
    SUPPLY_OPTIONS,
    TITLE_PANEL_INFO,
    TITLE_SKILLS,
    UPGRADE_KEYS,
    UPGRADES,
    WEAPONS,
    WEAPON_EXCLUSIVE_UPGRADES,
    UPGRADE_WEAPON_RULES,
    WEAPON_TAGS,
    CharacterOption,
    CharacterProfile,
    CharacterSkill,
    StageOption,
    SupplyOption,
    Upgrade,
    WeaponOption,
)
from .entities import (
    ActiveEnemyStatus,
    ActivePlayerBuff,
    Bullet,
    Enemy,
    ExplosionWave,
    FloatingText,
    GasCloud,
    LaserTrace,
    Particle,
    Pickup,
)
from .map_system import (
    FloorMap,
    FloorRoom,
    OPPOSITE_DIRECTIONS,
    RoomLayout,
    RoomObstacle,
    build_floor_map,
    build_stitched_layout,
)
from .navigation import NavigationField


ChoiceT = TypeVar("ChoiceT", Upgrade, SupplyOption)


CHARACTER_SPRITE_SPECS = {
    "vanguard": {"anchor": (22.0, 22.0), "base_radius": float(config.PLAYER_RADIUS)},
    "mamba": {"anchor": (18.0, 18.0), "base_radius": float(config.PLAYER_RADIUS)},
    "kunkun": {"anchor": (18.0, 19.0), "base_radius": float(config.PLAYER_RADIUS)},
}

WEAPON_SPRITE_ANCHORS = {
    "rifle": (12.0, 8.0),
    "scatter": (12.0, 8.0),
    "shotgun": (12.0, 7.0),
    "rail": (12.0, 9.0),
    "rocket": (12.0, 9.0),
    "laser_burst": (12.0, 8.0),
    "laser_lance": (12.0, 9.0),
}

BULLET_SPRITE_SPECS = {
    "bullet": {"anchor": (8.0, 8.0), "base_radius": 6.0},
    "bullet_enemy": {"anchor": (8.0, 8.0), "base_radius": 6.0},
    "bullet_elite": {"anchor": (9.0, 9.0), "base_radius": 7.0},
    "bullet_shock": {"anchor": (9.0, 9.0), "base_radius": 7.0},
    "rail": {"anchor": (22.0, 10.0), "base_radius": 6.0},
    "shotgun_pellet": {"anchor": (15.0, 7.0), "base_radius": 5.0},
    "rocket": {
        "anchor": (28.0, 8.0),
        "base_radius": float(config.ROCKET_PROJECTILE_RADIUS),
    },
    "basketball": {
        "anchor": (13.0, 13.0),
        "base_radius": float(config.BASKETBALL_RADIUS),
    },
}

ENEMY_SPRITE_SPECS = {
    "grunt": {
        "anchor": (18.0, 18.0),
        "base_radius": float(config.ENEMY_RADIUS),
        "rotates": False,
    },
    "laser": {
        "anchor": (18.0, 18.0),
        "base_radius": float(config.ENEMY_RADIUS),
        "rotates": False,
    },
    "shooter": {
        "anchor": (20.0, 20.0),
        "base_radius": float(config.ENEMY_RADIUS),
        "rotates": False,
    },
    "shotgunner": {
        "anchor": (18.0, 18.0),
        "base_radius": float(config.ENEMY_RADIUS),
        "rotates": False,
    },
    "charger": {
        "anchor": (18.0, 18.0),
        "base_radius": float(config.ENEMY_RADIUS),
        "rotates": False,
    },
    "elite": {
        "anchor": (23.0, 23.0),
        "base_radius": float(config.ENEMY_RADIUS + 2),
        "rotates": False,
    },
    "boss": {
        "anchor": (37.0, 37.0),
        "base_radius": float(config.BOSS_RADIUS),
        "rotates": False,
    },
    "challenge": {
        "anchor": (49.0, 49.0),
        "base_radius": float(config.BOSS_RADIUS + 4),
        "rotates": False,
    },
    "engineer": {
        "anchor": (21.0, 21.0),
        "base_radius": float(config.ENEMY_RADIUS + 1),
        "rotates": False,
    },
    "turret": {
        "anchor": (19.0, 13.0),
        "base_radius": float(config.ENEMY_RADIUS + 3),
        "rotates": True,
    },
    "elite_turret": {
        "anchor": (31.0, 31.0),
        "base_radius": float(config.ENEMY_RADIUS + 6),
        "rotates": True,
    },
    "toxic_bloater": {
        "anchor": (19.0, 19.0),
        "base_radius": float(config.ENEMY_RADIUS + 1),
        "rotates": False,
    },
    "reactor_bomber": {
        "anchor": (22.0, 22.0),
        "base_radius": float(config.ENEMY_RADIUS + 2),
        "rotates": False,
    },
}

TURRET_PART_SPRITE_SPECS = {
    "turret": {
        "base_anchor": (48.0, 48.0),
        "top_anchor": (48.0, 48.0),
        "base_radius": float(config.ENEMY_RADIUS + 3),
        "ring_offset_y": 0.58,
    },
    "elite_turret": {
        "base_anchor": (48.0, 48.0),
        "top_anchor": (48.0, 48.0),
        "base_radius": float(config.ENEMY_RADIUS + 6),
        "ring_offset_y": 0.58,
    },
}

MAP_SPRITE_SPECS = {
    "wall": {"anchor": (50.0, 14.0), "body_size": (96.0, 24.0)},
    "cover": {"anchor": (29.0, 17.0), "body_size": (54.0, 30.0)},
    "crate": {"anchor": (16.0, 16.0), "body_size": (28.0, 28.0)},
    "bullet": {"anchor": (14.0, 14.0), "body_size": (24.0, 24.0)},
    "toxic": {"anchor": (15.0, 15.0), "body_size": (26.0, 26.0)},
    "reactor": {"anchor": (21.0, 21.0), "body_size": (38.0, 38.0)},
    "nuke": {"anchor": (44.0, 44.0), "body_size": (84.0, 84.0)},
    "treasure": {"anchor": (42.0, 30.0), "body_size": (84.0, 60.0)},
    "exit_active": {"anchor": (36.0, 36.0), "body_size": (68.0, 68.0)},
    "north": {"anchor": (31.0, 21.0), "body_size": (44.0, 24.0)},
    "east": {"anchor": (21.0, 31.0), "body_size": (24.0, 44.0)},
    "south": {"anchor": (31.0, 21.0), "body_size": (44.0, 24.0)},
    "west": {"anchor": (21.0, 31.0), "body_size": (24.0, 44.0)},
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_resource_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    return Path(bundle_root) if bundle_root else project_root()


def runtime_record_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


@dataclass
class ShopOffer:
    key: str
    name: str
    description: str
    cost: int
    pos: pygame.Vector2
    sold: bool = False


@dataclass
class RoomEventState:
    key: str
    anchor: pygame.Vector2 | None = None
    spawned: bool = False
    completed: bool = False


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
    shop_purchases: int = 0
    room_event: RoomEventState | None = None
    challenge_tag: str | None = None
    retreat_door: str | None = None
    nav_version: int = 0


@dataclass
class EnemyNavigationPlan:
    target: pygame.Vector2
    has_los: bool
    direct_engage: bool
    mode: str
    blocker: RoomObstacle | None = None


@dataclass
class ObstacleSpatialIndex:
    cell_size: int
    obstacles: tuple[RoomObstacle, ...] = field(default_factory=tuple)
    buckets: dict[tuple[int, int], tuple[RoomObstacle, ...]] = field(
        default_factory=dict
    )

    @classmethod
    def build(
        cls, obstacles: Sequence[RoomObstacle], cell_size: int
    ) -> "ObstacleSpatialIndex":
        size = max(24, int(cell_size))
        built = cls(cell_size=size, obstacles=tuple(obstacles))
        bucket_lists: dict[tuple[int, int], list[RoomObstacle]] = {}
        for obstacle in built.obstacles:
            rect = obstacle.rect
            left = rect.left // size
            right = max(rect.left, rect.right - 1) // size
            top = rect.top // size
            bottom = max(rect.top, rect.bottom - 1) // size
            for gx in range(left, right + 1):
                for gy in range(top, bottom + 1):
                    bucket_lists.setdefault((gx, gy), []).append(obstacle)
        built.buckets = {
            cell: tuple(items) for cell, items in bucket_lists.items()
        }
        return built

    def query_rect(self, rect: pygame.Rect) -> tuple[RoomObstacle, ...]:
        if not self.obstacles:
            return ()
        left = rect.left // self.cell_size
        right = max(rect.left, rect.right - 1) // self.cell_size
        top = rect.top // self.cell_size
        bottom = max(rect.top, rect.bottom - 1) // self.cell_size
        matches: list[RoomObstacle] = []
        seen: set[int] = set()
        for gx in range(left, right + 1):
            for gy in range(top, bottom + 1):
                for obstacle in self.buckets.get((gx, gy), ()):
                    marker = id(obstacle)
                    if marker in seen:
                        continue
                    seen.add(marker)
                    matches.append(obstacle)
        return tuple(matches)

    def query_circle(
        self, pos: pygame.Vector2, radius: float
    ) -> tuple[RoomObstacle, ...]:
        diameter = max(1, int(math.ceil(radius * 2)))
        rect = pygame.Rect(0, 0, diameter, diameter)
        rect.center = (round(pos.x), round(pos.y))
        return self.query_rect(rect)

    def query_segment(
        self, start: pygame.Vector2, end: pygame.Vector2, padding: int = 0
    ) -> tuple[RoomObstacle, ...]:
        left = int(min(start.x, end.x))
        top = int(min(start.y, end.y))
        width = max(1, int(abs(end.x - start.x)))
        height = max(1, int(abs(end.y - start.y)))
        rect = pygame.Rect(left, top, width, height).inflate(
            padding * 2 + 2, padding * 2 + 2
        )
        return self.query_rect(rect)


@dataclass
class EnemySpatialIndex:
    cell_size: int
    enemies: tuple[Enemy, ...] = field(default_factory=tuple)
    buckets: dict[tuple[int, int], tuple[Enemy, ...]] = field(default_factory=dict)

    @classmethod
    def build(
        cls, enemies: Sequence[Enemy], cell_size: int
    ) -> "EnemySpatialIndex":
        size = max(24, int(cell_size))
        built = cls(cell_size=size, enemies=tuple(enemies))
        bucket_lists: dict[tuple[int, int], list[Enemy]] = {}
        for enemy in built.enemies:
            gx = int(enemy.pos.x) // size
            gy = int(enemy.pos.y) // size
            bucket_lists.setdefault((gx, gy), []).append(enemy)
        built.buckets = {
            cell: tuple(items) for cell, items in bucket_lists.items()
        }
        return built

    def query_circle(self, pos: pygame.Vector2, radius: float) -> tuple[Enemy, ...]:
        if not self.enemies:
            return ()
        cell_radius = max(1, int(math.ceil(radius / max(1, self.cell_size))))
        center_x = int(pos.x) // self.cell_size
        center_y = int(pos.y) // self.cell_size
        matches: list[Enemy] = []
        seen: set[int] = set()
        max_distance_sq = radius * radius
        for gx in range(center_x - cell_radius, center_x + cell_radius + 1):
            for gy in range(center_y - cell_radius, center_y + cell_radius + 1):
                for enemy in self.buckets.get((gx, gy), ()):
                    marker = id(enemy)
                    if marker in seen:
                        continue
                    seen.add(marker)
                    if enemy.pos.distance_squared_to(pos) <= max_distance_sq:
                        matches.append(enemy)
        return tuple(matches)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("钢铁蜂巢")
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(
            ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"], 19
        )
        self.small_font = pygame.font.SysFont(
            ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"], 15
        )
        self.tiny_font = pygame.font.SysFont(
            ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"], 13
        )
        self.big_font = pygame.font.SysFont(
            ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"],
            34,
            bold=True,
        )
        self.rng = random.Random()
        self.running = True
        self.selected_stage = STAGES[0]
        self.selected_character = CHARACTERS[0]
        self.selected_weapon = WEAPONS[0]
        self.title_panel = "main"
        self.record_path = runtime_record_root() / "highscore.json"
        self.record_path.parent.mkdir(parents=True, exist_ok=True)
        self.resources_path = runtime_resource_root() / "resources"
        self.sound_path = self.resources_path / "sound"
        self.effects_path = self.resources_path / "effects"
        self.character_sprites = self.load_named_surfaces(
            self.resources_path / "characters"
        )
        self.weapon_sprites = self.load_named_surfaces(
            self.resources_path / "weapons"
        )
        self.bullet_sprites = self.load_named_surfaces(
            self.resources_path / "bullets"
        )
        self.enemy_sprites = self.load_named_surfaces(
            self.resources_path / "enemies"
        )
        self.map_sprites = self.load_named_surfaces(self.resources_path / "map")
        self.sounds: dict[str, pygame.mixer.Sound | None] = {}
        self.pulse_effect_frames = self.load_effect_frames("skills/pulse")
        self.mamba_startup_frames = self.load_effect_frames("skills/mamba_smash_startup")
        self.mamba_impact_frames = self.load_effect_frames("skills/mamba_smash_impact")
        self.explosion_wave_frames = self.load_effect_frames("combat/explosion_wave")
        self.laser_trace_frames = self.load_effect_frames("combat/laser_trace")
        self.laser_lance_trace_frames = self.load_effect_frames(
            "combat/laser_lance_trace"
        )
        self.enemy_laser_trace_frames = self.load_effect_frames(
            "combat/enemy_laser_trace"
        )
        self.boss_stomp_frames = self.load_effect_frames("telegraphs/boss_stomp")
        self.boss_nova_frames = self.load_effect_frames("telegraphs/boss_nova")
        self.challenge_dash_charge_frames = self.load_effect_frames(
            "telegraphs/challenge_dash_charge"
        )
        self.challenge_summon_frames = self.load_effect_frames(
            "telegraphs/challenge_summon"
        )
        self.enemy_laser_frames = self.load_effect_frames("telegraphs/enemy_laser")
        self.stun_marker_frames = self.load_effect_frames("status/stun_marker")
        self.poison_marker_frames = self.load_effect_frames("status/poison_marker")
        self.gas_cloud_frames = self.load_effect_frames("environment/gas_cloud")
        self.nuke_event_frames = self.load_effect_frames("room_events/nuke")
        self.elite_turret_event_frames = self.load_effect_frames(
            "room_events/elite_turret"
        )
        self.auto_aim_frames = self.load_effect_frames("ui/auto_aim")
        self.screen_flash_frames = self.load_effect_frames("ui/screen_flash")
        self.wall_surface_cache: dict[tuple[int, int, bool], pygame.Surface] = {}
        self.laser_frame_part_cache: dict[
            int, tuple[pygame.Surface, pygame.Surface, pygame.Surface]
        ] = {}
        self.effect_tint_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self.best_record = self.load_best_record()
        self.init_sounds()
        self.restart_run()

    def load_effect_frames(self, relative_dir: str) -> list[pygame.Surface]:
        directory = self.effects_path / relative_dir
        if not directory.exists():
            return []
        frames: list[pygame.Surface] = []
        for path in sorted(directory.glob("*.png")):
            try:
                frames.append(pygame.image.load(path.as_posix()).convert_alpha())
            except pygame.error:
                continue
        return frames

    def load_named_surfaces(self, directory: Path) -> dict[str, pygame.Surface]:
        if not directory.exists():
            return {}
        loaded: dict[str, pygame.Surface] = {}
        for path in sorted(directory.glob("*.png")):
            try:
                loaded[path.stem] = pygame.image.load(path.as_posix()).convert_alpha()
            except pygame.error:
                continue
        return loaded

    def effect_frame(
        self, frames: list[pygame.Surface], progress: float
    ) -> pygame.Surface | None:
        if not frames:
            return None
        index = min(
            len(frames) - 1,
            max(0, int(round(max(0.0, min(1.0, progress)) * (len(frames) - 1)))),
        )
        return frames[index]

    def timed_effect_frame(
        self, frames: list[pygame.Surface], timer: float, total: float
    ) -> pygame.Surface | None:
        if total <= 0:
            return None
        progress = 1.0 - timer / max(0.01, total)
        return self.effect_frame(frames, progress)

    def blit_effect_frame(
        self,
        frame: pygame.Surface | None,
        center: pygame.Vector2 | tuple[float, float],
        *,
        scale: float | tuple[float, float] = 1.0,
        angle_degrees: float = 0.0,
    ) -> None:
        if frame is None:
            return
        image = frame
        if isinstance(scale, (int, float)):
            scale_x = float(scale)
            scale_y = float(scale)
        else:
            scale_x, scale_y = scale
        scale_x = max(0.01, scale_x)
        scale_y = max(0.01, scale_y)
        if abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01:
            size = (
                max(1, int(round(frame.get_width() * scale_x))),
                max(1, int(round(frame.get_height() * scale_y))),
            )
            image = pygame.transform.smoothscale(frame, size)
        if abs(angle_degrees) > 0.01:
            image = pygame.transform.rotate(image, angle_degrees)
        rect = image.get_rect(center=(int(center[0]), int(center[1])))
        self.screen.blit(image, rect)

    def resolve_scale(
        self, scale: float | tuple[float, float]
    ) -> tuple[float, float]:
        if isinstance(scale, (int, float)):
            scale_x = float(scale)
            scale_y = float(scale)
        else:
            scale_x, scale_y = scale
        return max(0.01, scale_x), max(0.01, scale_y)

    def blit_anchored_surface(
        self,
        surface: pygame.Surface | None,
        anchor_world: pygame.Vector2 | tuple[float, float],
        anchor_px: tuple[float, float],
        *,
        scale: float | tuple[float, float] = 1.0,
        angle_degrees: float = 0.0,
        alpha: int | None = None,
    ) -> None:
        if surface is None:
            return
        scale_x, scale_y = self.resolve_scale(scale)
        image = surface
        if abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01:
            image = pygame.transform.smoothscale(
                surface,
                (
                    max(1, int(round(surface.get_width() * scale_x))),
                    max(1, int(round(surface.get_height() * scale_y))),
                ),
            )
        offset = pygame.Vector2(
            anchor_px[0] - surface.get_width() / 2,
            anchor_px[1] - surface.get_height() / 2,
        )
        offset.x *= scale_x
        offset.y *= scale_y
        if abs(angle_degrees) > 0.01:
            image = pygame.transform.rotate(image, angle_degrees)
            offset = offset.rotate(angle_degrees)
        if alpha is not None:
            image.set_alpha(max(0, min(255, int(alpha))))
        world = pygame.Vector2(anchor_world)
        center = world - offset
        rect = image.get_rect(center=(round(center.x), round(center.y)))
        self.screen.blit(image, rect)

    def blit_surface_center(
        self,
        surface: pygame.Surface | None,
        center: pygame.Vector2 | tuple[float, float],
        *,
        angle_degrees: float = 0.0,
    ) -> None:
        if surface is None:
            return
        image = surface
        if abs(angle_degrees) > 0.01:
            image = pygame.transform.rotate(surface, angle_degrees)
        rect = image.get_rect(center=(round(center[0]), round(center[1])))
        self.screen.blit(image, rect)

    def scaled_surface(
        self, surface: pygame.Surface, width: float, height: float
    ) -> pygame.Surface:
        return pygame.transform.smoothscale(
            surface,
            (
                max(1, int(round(width))),
                max(1, int(round(height))),
            ),
        )

    def tiled_wall_surface(self, width: int, height: int) -> pygame.Surface | None:
        horizontal = width >= height
        length = max(1, width if horizontal else height)
        thickness = max(1, height if horizontal else width)
        cache_key = (length, thickness, horizontal)
        cached = self.wall_surface_cache.get(cache_key)
        if cached is not None:
            return cached
        sprite = self.map_sprites.get("wall")
        if sprite is None:
            return None
        scale_y = thickness / max(1.0, float(sprite.get_height()))
        cap_src_w = min(sprite.get_width() // 3, max(10, sprite.get_height() // 2))
        tile_src_w = min(14, max(8, sprite.get_width() - cap_src_w * 2))
        if length <= 0 or thickness <= 0:
            return None
        if length <= max(20, int(round(cap_src_w * scale_y * 2.2))):
            strip = self.scaled_surface(sprite, length, thickness)
        else:
            left_cap_src = sprite.subsurface((0, 0, cap_src_w, sprite.get_height())).copy()
            right_cap_src = sprite.subsurface(
                (sprite.get_width() - cap_src_w, 0, cap_src_w, sprite.get_height())
            ).copy()
            tile_x = (sprite.get_width() - tile_src_w) // 2
            tile_src = sprite.subsurface((tile_x, 0, tile_src_w, sprite.get_height())).copy()
            target_h = max(1, thickness)
            cap_w = max(1, int(round(cap_src_w * scale_y)))
            tile_w = max(1, int(round(tile_src_w * scale_y)))
            strip = pygame.Surface((length, target_h), pygame.SRCALPHA)
            left_cap = self.scaled_surface(left_cap_src, cap_w, target_h)
            right_cap = self.scaled_surface(right_cap_src, cap_w, target_h)
            tile = self.scaled_surface(tile_src, tile_w, target_h)
            strip.blit(left_cap, (0, 0))
            strip.blit(right_cap, (length - cap_w, 0))
            body_left = cap_w
            body_right = max(body_left, length - cap_w)
            x = body_left
            while x < body_right:
                remaining = body_right - x
                if remaining >= tile_w:
                    strip.blit(tile, (x, 0))
                else:
                    strip.blit(tile, (x, 0), pygame.Rect(0, 0, remaining, target_h))
                x += tile_w
        final = strip if horizontal else pygame.transform.rotate(strip, 90)
        self.wall_surface_cache[cache_key] = final
        return final

    def laser_frame_parts(
        self, frame: pygame.Surface
    ) -> tuple[pygame.Surface, pygame.Surface, pygame.Surface]:
        cached = self.laser_frame_part_cache.get(id(frame))
        if cached is not None:
            return cached
        cap_span = min(frame.get_width() // 3, frame.get_height())
        body_start = min(frame.get_width() - 2, cap_span)
        body_width = max(1, frame.get_width() - cap_span * 2)
        left_cap = frame.subsurface((0, 0, cap_span, frame.get_height())).copy()
        body = frame.subsurface((body_start, 0, body_width, frame.get_height())).copy()
        right_cap = frame.subsurface(
            (frame.get_width() - cap_span, 0, cap_span, frame.get_height())
        ).copy()
        parts = (left_cap, body, right_cap)
        self.laser_frame_part_cache[id(frame)] = parts
        return parts

    def tinted_effect_frame(
        self,
        frame: pygame.Surface | None,
        color: tuple[int, int, int] | None,
    ) -> pygame.Surface | None:
        if frame is None or color is None:
            return frame
        r = max(0, min(255, int(color[0])))
        g = max(0, min(255, int(color[1])))
        b = max(0, min(255, int(color[2])))
        cache_key = (id(frame), r, g, b)
        cached = self.effect_tint_cache.get(cache_key)
        if cached is not None:
            return cached
        tinted = frame.copy()
        tint_layer = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
        tint_layer.fill((r, g, b, 255))
        tinted.blit(tint_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.effect_tint_cache[cache_key] = tinted
        return tinted

    def boss_stomp_effect_color(self, enemy: Enemy) -> tuple[int, int, int]:
        if enemy.variant == "challenge":
            return config.CHALLENGE_ROOM_COLOR
        return config.BULLET_SHOCK_COLOR

    def draw_laser_segment_sprite(
        self,
        frame: pygame.Surface | None,
        start: pygame.Vector2,
        end: pygame.Vector2,
        color: tuple[int, int, int],
        width: int,
        base_width: float,
    ) -> None:
        segment = end - start
        if segment.length_squared() <= 0:
            return
        direction = segment.normalize()
        angle = -math.degrees(math.atan2(direction.y, direction.x))
        if frame is None:
            pygame.draw.line(self.screen, color, start, end, max(2, width))
            cap_radius = max(3, int(width * 0.7))
            for point in (start, end):
                pygame.draw.circle(self.screen, color, point, cap_radius)
                pygame.draw.circle(
                    self.screen,
                    config.LASER_TRACE_CORE,
                    point,
                    max(2, cap_radius - 2),
                )
            return
        width_scale = max(0.12, width / max(1.0, base_width))
        target_h = max(1, int(round(frame.get_height() * width_scale)))
        left_cap_src, body_src, right_cap_src = self.laser_frame_parts(frame)
        body = self.scaled_surface(body_src, segment.length(), target_h)
        cap_w = max(1, int(round(left_cap_src.get_width() * width_scale)))
        left_cap = self.scaled_surface(left_cap_src, cap_w, target_h)
        right_cap = self.scaled_surface(right_cap_src, cap_w, target_h)
        self.blit_surface_center(body, start.lerp(end, 0.5), angle_degrees=angle)
        self.blit_surface_center(left_cap, start, angle_degrees=angle)
        self.blit_surface_center(right_cap, end, angle_degrees=angle)

    def enemy_asset_key(self, enemy: Enemy) -> str:
        if enemy.kind == "boss" and enemy.variant == "challenge":
            return "challenge"
        if enemy.kind == "turret" and enemy.variant == "elite_turret":
            return "elite_turret"
        return enemy.kind

    def bullet_asset_key(self, bullet: Bullet) -> str:
        if bullet.style == "basketball":
            return "basketball"
        if bullet.style == "rail":
            return "rail"
        if bullet.style == "rocket":
            return "rocket"
        if bullet.style == "shotgun_pellet":
            return "shotgun_pellet"
        if bullet.color == config.BULLET_SHOCK_COLOR:
            return "bullet_shock"
        if bullet.color == config.BULLET_ELITE_COLOR:
            return "bullet_elite"
        if not bullet.friendly or bullet.color == config.BULLET_ENEMY_COLOR:
            return "bullet_enemy"
        return "bullet"

    def laser_trace_asset(
        self, trace: LaserTrace
    ) -> tuple[list[pygame.Surface], float, float]:
        if trace.color == config.LASER_HEAVY_COLOR:
            return (
                self.laser_lance_trace_frames or self.laser_trace_frames,
                480.0,
                18.0,
            )
        if trace.color == config.ENEMY_LASER_COLOR:
            return (
                self.enemy_laser_trace_frames or self.laser_trace_frames,
                480.0,
                12.0,
            )
        return self.laser_trace_frames, 480.0, 12.0

    def turret_aim_angle(self, enemy: Enemy) -> float:
        direction = enemy.aim_direction
        if direction.length_squared() <= 0:
            direction = self.player_pos - enemy.pos
        if direction.length_squared() <= 0:
            direction = pygame.Vector2(1, 0)
        direction = direction.normalize()
        return -math.degrees(math.atan2(direction.y, direction.x))

    def draw_elite_turret_rings(
        self, center: pygame.Vector2, radius: float
    ) -> None:
        pulse = pygame.time.get_ticks() * 0.006
        overlay = pygame.Surface((int(radius * 4.8), int(radius * 3.2)), pygame.SRCALPHA)
        overlay_center = pygame.Vector2(overlay.get_width() / 2, overlay.get_height() / 2)
        rings = (
            (
                radius * (1.12 + 0.04 * math.sin(pulse)),
                radius * (0.54 + 0.03 * math.sin(pulse)),
                122,
            ),
            (
                radius * (0.76 + 0.05 * math.sin(pulse + 1.4)),
                radius * (0.34 + 0.03 * math.sin(pulse + 1.4)),
                164,
            ),
        )
        for ring_rx, ring_ry, alpha in rings:
            rect = pygame.Rect(0, 0, int(ring_rx * 2), int(ring_ry * 2))
            rect.center = (round(overlay_center.x), round(overlay_center.y))
            pygame.draw.ellipse(
                overlay,
                (*config.TURRET_ELITE_COLOR, alpha),
                rect,
                2,
            )
        self.screen.blit(
            overlay,
            overlay.get_rect(center=(round(center.x), round(center.y))),
        )

    def draw_turret_enemy_sprite(self, enemy: Enemy) -> None:
        key = self.enemy_asset_key(enemy)
        part_spec = TURRET_PART_SPRITE_SPECS.get(key)
        base_sprite = self.enemy_sprites.get(f"{key}_base")
        top_sprite = self.enemy_sprites.get(f"{key}_top")
        if part_spec is None or base_sprite is None or top_sprite is None:
            sprite = self.enemy_sprites.get(key)
            spec = ENEMY_SPRITE_SPECS.get(key)
            if sprite is not None and spec is not None:
                self.blit_anchored_surface(
                    sprite,
                    enemy.pos,
                    spec["anchor"],
                    scale=enemy.radius / max(1.0, float(spec["base_radius"])),
                )
            else:
                pygame.draw.circle(self.screen, enemy.color, enemy.pos, enemy.radius)
            return
        scale = enemy.radius / max(1.0, float(part_spec["base_radius"]))
        self.blit_anchored_surface(
            base_sprite,
            enemy.pos,
            part_spec["base_anchor"],
            scale=scale,
        )
        if enemy.variant == "elite_turret":
            ring_center = enemy.pos + pygame.Vector2(
                0, enemy.radius * float(part_spec.get("ring_offset_y", 0.42))
            )
            self.draw_elite_turret_rings(ring_center, enemy.radius)
        self.blit_anchored_surface(
            top_sprite,
            enemy.pos,
            part_spec["top_anchor"],
            scale=scale,
            angle_degrees=self.turret_aim_angle(enemy),
        )

    def draw_enemy_sprite(self, enemy: Enemy) -> None:
        if enemy.kind == "turret":
            self.draw_turret_enemy_sprite(enemy)
            return
        key = self.enemy_asset_key(enemy)
        sprite = self.enemy_sprites.get(key)
        spec = ENEMY_SPRITE_SPECS.get(key)
        if sprite is None or spec is None:
            pygame.draw.circle(self.screen, enemy.color, enemy.pos, enemy.radius)
            self.draw_actor_face(
                enemy.pos, enemy.radius, enemy.kind, is_boss=enemy.is_boss
            )
            return
        scale = enemy.radius / max(1.0, float(spec["base_radius"]))
        angle = 0.0
        if spec.get("rotates"):
            direction = enemy.aim_direction
            if direction.length_squared() <= 0:
                direction = self.player_pos - enemy.pos
            if direction.length_squared() <= 0:
                direction = pygame.Vector2(1, 0)
            direction = direction.normalize()
            angle = -math.degrees(math.atan2(direction.y, direction.x))
        self.blit_anchored_surface(
            sprite,
            enemy.pos,
            spec["anchor"],
            scale=scale,
            angle_degrees=angle,
        )

    def draw_bullet_sprite_instance(self, bullet: Bullet, radius: int) -> None:
        key = self.bullet_asset_key(bullet)
        sprite = self.bullet_sprites.get(key)
        spec = BULLET_SPRITE_SPECS.get(key)
        if sprite is None or spec is None:
            pygame.draw.circle(self.screen, bullet.color, bullet.pos, radius)
            return
        angle = 0.0
        if key in {"rocket", "shotgun_pellet", "rail"} and bullet.velocity.length_squared() > 0:
            direction = bullet.velocity.normalize()
            angle = -math.degrees(math.atan2(direction.y, direction.x))
        alpha = None
        if bullet.max_ttl > 0 and bullet.decay_visual:
            alpha = 96 + int(159 * max(0.0, min(1.0, bullet.ttl / bullet.max_ttl)))
        scale = radius / max(1.0, float(spec["base_radius"]))
        self.blit_anchored_surface(
            sprite,
            bullet.pos,
            spec["anchor"],
            scale=scale,
            angle_degrees=angle,
            alpha=alpha,
        )

    def draw_obstacle_sprite(self, obstacle: RoomObstacle) -> None:
        key = obstacle.tag if obstacle.tag in self.map_sprites else (
            "cover" if obstacle.destructible else "wall"
        )
        if key == "wall":
            wall_surface = self.tiled_wall_surface(
                obstacle.rect.width, obstacle.rect.height
            )
            if wall_surface is not None:
                self.screen.blit(
                    wall_surface,
                    wall_surface.get_rect(center=obstacle.rect.center),
                )
                return
        sprite = self.map_sprites.get(key)
        spec = MAP_SPRITE_SPECS.get(key)
        if sprite is None or spec is None:
            rect = obstacle.rect
            fill = (
                obstacle.fill_color
                if getattr(obstacle, "fill_color", None) is not None
                else (
                    config.OBSTACLE_FILL if not obstacle.destructible else (95, 78, 58)
                )
            )
            border = (
                obstacle.border_color
                if getattr(obstacle, "border_color", None) is not None
                else (
                    config.OBSTACLE_BORDER
                    if not obstacle.destructible
                    else (194, 156, 106)
                )
            )
            radius = 6 if rect.width < 24 or rect.height < 24 else 10
            pygame.draw.rect(self.screen, fill, rect, border_radius=radius)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=radius)
            return
        base_width, base_height = spec["body_size"]
        self.blit_anchored_surface(
            sprite,
            pygame.Vector2(obstacle.rect.center),
            spec["anchor"],
            scale=(
                obstacle.rect.width / max(1.0, float(base_width)),
                obstacle.rect.height / max(1.0, float(base_height)),
            ),
        )

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
        self.player_projectile_speed = float(config.BULLET_SPEED)
        self.player_projectile_ttl = 1.5
        self.player_projectile_radius = config.BULLET_RADIUS
        self.player_projectile_knockback = config.PROJECTILE_BASE_KNOCKBACK
        self.player_rocket_explosion_radius = 0.0
        self.player_rocket_explosion_knockback = 0.0
        self.player_shotgun_pellets = 1
        self.player_shotgun_spread = 0.0
        self.pickup_radius = 72.0
        self.credit_gain_multiplier = 1.0
        self.enemy_bullet_speed_multiplier = 1.0
        self.shotgun_range_bonus = 0.0
        self.shot_serial = 0
        self.dash_distance = float(config.DASH_DISTANCE)
        self.dash_cooldown = float(config.DASH_COOLDOWN)
        self.dash_timer = 0.0
        self.pulse_radius = float(config.PULSE_RADIUS)
        self.pulse_push_force = float(config.PULSE_PUSH_FORCE)
        self.pulse_cooldown = float(config.PULSE_COOLDOWN)
        self.pulse_effect_duration = float(config.PULSE_EFFECT_DURATION)
        self.pulse_effect_timer = 0.0
        self.pulse_effect_total = 0.0
        self.basketball_damage = float(config.BASKETBALL_DAMAGE)
        self.basketball_radius = float(config.BASKETBALL_RADIUS)
        self.basketball_speed_scale = float(config.BASKETBALL_SPEED_SCALE)
        self.basketball_upgrade_level = 0
        self.mamba_skill_damage = float(config.MAMBA_SKILL_DAMAGE)
        self.mamba_skill_stun_duration = float(config.MAMBA_SKILL_STUN_DURATION)
        self.mamba_skill_half_angle = float(config.MAMBA_SKILL_HALF_ANGLE)
        self.mamba_upgrade_level = 0
        self.skill_cast_key: str | None = None
        self.skill_cast_timer = 0.0
        self.skill_cast_total = 0.0
        self.skill_cast_direction = pygame.Vector2()
        self.mamba_impact_timer = 0.0
        self.mamba_impact_total = 0.0
        self.mamba_impact_direction = pygame.Vector2()
        self.mamba_impact_center = self.player_pos.copy()
        self.active_skill_key = "pulse"
        self.skill_timer = 0.0
        self.active_skill_name = "电弧脉冲"
        self.active_skill_label = "脉冲"
        self.iframes = 0.0
        self.last_move = pygame.Vector2(1, 0)
        self.player_revives_remaining = 0
        self.kunkun_chip_barrage_used = False
        self.vanguard_shockwave_used = False
        self.q_skill_hold_active = False
        self.q_skill_hold_timer = 0.0
        self.auto_aim_target = pygame.Vector2()

        self.level = 1
        self.xp = 0
        self.xp_to_level = config.XP_TO_LEVEL_BASE
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
        self.navigation_fields: dict[tuple[int, int, int], NavigationField] = {}
        self.obstacle_index = ObstacleSpatialIndex(config.OBSTACLE_QUERY_CELL_SIZE)
        self.enemy_index = EnemySpatialIndex(config.ENEMY_SPATIAL_QUERY_CELL_SIZE)
        self.obstacle_rect_cache: tuple[pygame.Rect, ...] = ()
        self.enemy_pause_timer = 0.0
        self.floor_entry_enemy_grace_pending = False
        self.screen_shake_timer = 0.0
        self.screen_shake_total = 0.0
        self.screen_shake_strength = 0.0
        self.screen_flash_timer = 0.0
        self.screen_flash_total = 0.0
        self.screen_flash_alpha = 0
        self.screen_flash_color = (255, 255, 255)

        self.bullets: list[Bullet] = []
        self.enemies: list[Enemy] = []
        self.pickups: list[Pickup] = []
        self.floaters: list[FloatingText] = []
        self.particles: list[Particle] = []
        self.laser_traces: list[LaserTrace] = []
        self.explosion_waves: list[ExplosionWave] = []
        self.gas_clouds: list[GasCloud] = []
        self.player_buffs: list[ActivePlayerBuff] = []
        self.obstacles: list[RoomObstacle] = []
        self.refresh_obstacle_state()
        self.room_layout: RoomLayout | None = None
        self.room_clear_delay = 0.0
        self.mode = "title"
        self.floor_transition_timer = 0.0
        self.floor_transition_total = 0.0
        self.floor_transition_target = 0
        self.floor_transition_switched = False
        self.upgrade_choices: list[Upgrade] = []
        self.reward_choices: list[Upgrade] = []
        self.supply_choices: list[SupplyOption] = list(SUPPLY_OPTIONS)
        self.current_score = 0
        self.message = "完成配置后开始下潜"
        self.title_panel_scroll = 0.0
        self.title_panel_scroll_target = 0.0

    def init_sounds(self) -> None:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            self.sounds = {
                "ui_click": None,
                "prism_lance_fire": None,
                "pulse_laser_fire": None,
                "pulse_wave": None,
                "switch": None,
                "boom": None,
            }
            return
        self.sounds = {
            "ui_click": self._load_sound("ui_click.wav"),
            "prism_lance_fire": self._load_sound("prism_lance_fire.wav", volume=0.32),
            "pulse_laser_fire": self._load_sound("pulse_laser_fire.wav", volume=0.36),
            "pulse_wave": None,
            "switch": self._load_sound("switch.wav"),
            "boom": self._load_sound("boom.wav", volume=0.5),
        }

    def _load_sound(
        self, filename: str, volume: float = 1.0
    ) -> pygame.mixer.Sound | None:
        try:
            sound = pygame.mixer.Sound(str(self.sound_path / filename))
            sound.set_volume(volume)
            return sound
        except (pygame.error, FileNotFoundError):
            return None

    def play_sound(self, name: str) -> None:
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def arena_rect(self) -> pygame.Rect:
        return pygame.Rect(
            config.ARENA_MARGIN,
            config.ARENA_MARGIN,
            config.ARENA_WIDTH,
            config.ARENA_HEIGHT,
        )

    def obstacle_rects(self) -> tuple[pygame.Rect, ...]:
        return self.obstacle_rect_cache

    def refresh_obstacle_state(self) -> None:
        self.obstacle_rect_cache = tuple(obstacle.rect for obstacle in self.obstacles)
        self.obstacle_index = ObstacleSpatialIndex.build(
            self.obstacles, config.OBSTACLE_QUERY_CELL_SIZE
        )

    def refresh_enemy_spatial_index(self) -> None:
        self.enemy_index = EnemySpatialIndex.build(
            self.enemies, config.ENEMY_SPATIAL_QUERY_CELL_SIZE
        )

    def query_obstacles_near(
        self, pos: pygame.Vector2, radius: float
    ) -> tuple[RoomObstacle, ...]:
        return self.obstacle_index.query_circle(pos, radius)

    def query_obstacles_in_segment(
        self, start: pygame.Vector2, end: pygame.Vector2, padding: int = 0
    ) -> tuple[RoomObstacle, ...]:
        return self.obstacle_index.query_segment(start, end, padding)

    def query_enemies_near(
        self, pos: pygame.Vector2, radius: float
    ) -> tuple[Enemy, ...]:
        return self.enemy_index.query_circle(pos, radius)

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
            self.record_path.write_text(
                json.dumps(self.best_record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def calculate_score(self) -> int:
        return int(
            self.rooms_cleared * 70
            + self.kills * 8
            + self.level * 45
            + self.floor_index * 120
            + self.credits * 2
        )

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

    def wrap_text(
        self,
        text: str,
        font: pygame.font.Font,
        max_width: int,
        max_lines: int | None = None,
    ) -> list[str]:
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

    def fit_text_line(self, text: str, font: pygame.font.Font, max_width: int) -> str:
        return self.wrap_text(text, font, max_width, 1)[0]

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
            direction = pygame.Vector2(
                self.rng.uniform(-1.0, 1.0), self.rng.uniform(-1.0, 1.0)
            )
            if direction.length_squared() <= 0:
                direction = pygame.Vector2(1, 0)
            velocity = direction.normalize() * self.rng.uniform(
                config.PARTICLE_SPEED * 0.35, config.PARTICLE_SPEED * speed_scale
            )
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
            particle.velocity *= max(
                0.0, 1.0 - (1.0 - config.PARTICLE_FRICTION) * 60 * dt
            )
            particle.ttl -= dt
            particle.radius = max(0.5, particle.radius - dt * 3.8)
            if particle.ttl > 0:
                remaining.append(particle)
        self.particles = remaining

    def update_gas_clouds(self, dt: float) -> None:
        remaining: list[GasCloud] = []
        for cloud in self.gas_clouds:
            cloud.ttl -= dt
            cloud.activation_delay = max(0.0, cloud.activation_delay - dt)
            if cloud.target_radius > cloud.radius and cloud.growth_speed > 0:
                cloud.radius = min(
                    cloud.target_radius, cloud.radius + cloud.growth_speed * dt
                )
            if cloud.activation_delay > 0:
                cloud.tick_timer = max(cloud.tick_timer, cloud.activation_delay)
            cloud.tick_timer -= dt
            if cloud.activation_delay <= 0 and cloud.tick_timer <= 0:
                cloud.tick_timer = 0.35
                for enemy in self.enemies[:]:
                    if enemy.pos.distance_to(cloud.pos) <= cloud.radius + enemy.radius:
                        enemy.hp -= cloud.damage
                        self.floaters.append(
                            FloatingText(
                                enemy.pos.copy(),
                                str(int(cloud.damage)),
                                (148, 220, 118),
                                0.28,
                            )
                        )
                        if enemy.hp <= 0:
                            self.kill_enemy(enemy)
                if (
                    self.player_pos.distance_to(cloud.pos)
                    <= cloud.radius + config.PLAYER_RADIUS
                    and self.iframes <= 0
                ):
                    self.damage_player(cloud.damage * 0.78, (148, 220, 118), 0.12)
            if cloud.ttl > 0:
                remaining.append(cloud)
        self.gas_clouds = remaining

    def make_gas_cloud(
        self,
        pos: pygame.Vector2,
        target_radius: float,
        ttl: float,
        damage: float,
        *,
        start_ratio: float = 0.22,
        growth_time: float = 0.52,
        activation_delay: float = 0.34,
    ) -> GasCloud:
        initial_radius = max(16.0, target_radius * start_ratio)
        growth_speed = max(
            0.0, (target_radius - initial_radius) / max(0.01, growth_time)
        )
        return GasCloud(
            pos=pos.copy(),
            radius=initial_radius,
            ttl=ttl,
            damage=damage,
            tick_timer=activation_delay,
            target_radius=target_radius,
            growth_speed=growth_speed,
            activation_delay=activation_delay,
        )

    def update_explosion_waves(self, dt: float) -> None:
        remaining: list[ExplosionWave] = []
        for wave in self.explosion_waves:
            wave.ttl -= dt
            if wave.ttl > 0:
                remaining.append(wave)
        self.explosion_waves = remaining

    def get_enemy_obstacle_avoidance(self, enemy: Enemy) -> pygame.Vector2:
        avoid = pygame.Vector2()
        influence_radius = enemy.radius + config.ENEMY_OBSTACLE_AVOID_RADIUS
        for obstacle in self.query_obstacles_near(enemy.pos, influence_radius):
            rect = obstacle.rect.inflate(18, 18)
            nearest_x = max(rect.left, min(enemy.pos.x, rect.right))
            nearest_y = max(rect.top, min(enemy.pos.y, rect.bottom))
            delta = enemy.pos - pygame.Vector2(nearest_x, nearest_y)
            dist_sq = delta.length_squared()
            if dist_sq <= 0 or dist_sq >= influence_radius * influence_radius:
                continue
            distance = dist_sq**0.5
            weight = 1.0 - distance / max(1.0, influence_radius)
            if getattr(obstacle, "tag", "normal") == "wall":
                weight *= 1.2
            avoid += delta.normalize() * weight
        return avoid

    def get_enemy_separation(self, enemy: Enemy) -> pygame.Vector2:
        avoid = pygame.Vector2()
        separation_radius = config.ENEMY_SEPARATION_RADIUS
        for other in self.query_enemies_near(enemy.pos, separation_radius):
            if other is enemy:
                continue
            delta = enemy.pos - other.pos
            dist_sq = delta.length_squared()
            if dist_sq <= 0 or dist_sq >= separation_radius * separation_radius:
                continue
            avoid += delta.normalize() * (separation_radius / max(12.0, dist_sq**0.5))
        return avoid

    def get_enemy_avoidance(self, enemy: Enemy) -> pygame.Vector2:
        avoid = self.get_enemy_obstacle_avoidance(enemy)
        separation = self.get_enemy_separation(enemy)
        if separation.length_squared() > 0:
            avoid += separation.normalize() * config.ENEMY_STEER_SEPARATION_WEIGHT
        return avoid

    def blend_enemy_steering(
        self,
        enemy: Enemy,
        move_delta: pygame.Vector2,
        nav_target: pygame.Vector2,
    ) -> pygame.Vector2:
        base = move_delta.copy()
        if base.length_squared() <= 0:
            base = nav_target - enemy.pos
        if base.length_squared() <= 0:
            return move_delta

        steering = base.normalize()
        obstacle_avoid = self.get_enemy_obstacle_avoidance(enemy)
        separation = self.get_enemy_separation(enemy)
        nearby_count = max(
            0,
            len(
                self.query_enemies_near(
                    enemy.pos, config.ENEMY_SEPARATION_RADIUS + enemy.radius
                )
            )
            - 1,
        )
        crowd_scale = 1.0 + min(0.85, nearby_count * 0.16)
        if obstacle_avoid.length_squared() > 0:
            steering += (
                obstacle_avoid.normalize() * config.ENEMY_STEER_OBSTACLE_WEIGHT
            )
        if separation.length_squared() > 0:
            steering += (
                separation.normalize()
                * config.ENEMY_STEER_SEPARATION_WEIGHT
                * crowd_scale
            )
        if steering.length_squared() <= 0:
            return move_delta

        magnitude = (
            move_delta.length()
            if move_delta.length_squared() > 0
            else enemy.speed * 0.72 / config.FPS
        )
        return steering.normalize() * magnitude

    def move_enemy_with_navigation(
        self,
        enemy: Enemy,
        desired_delta: pygame.Vector2,
        nav_target: pygame.Vector2,
        dt: float,
    ) -> pygame.Vector2:
        start = enemy.pos.copy()
        moved = self.move_circle_with_collisions(
            enemy.pos, enemy.radius, desired_delta
        )
        if (
            desired_delta.length_squared() <= 16
            or moved.length_squared() >= desired_delta.length_squared() * 0.18
        ):
            return enemy.pos - start

        candidate_dirs: list[pygame.Vector2] = []
        toward_target = nav_target - enemy.pos
        if toward_target.length_squared() > 0:
            toward_target = toward_target.normalize()
            candidate_dirs.extend(
                (
                    toward_target.rotate(90),
                    toward_target.rotate(-90),
                    toward_target,
                )
            )
        if desired_delta.length_squared() > 0:
            desired_dir = desired_delta.normalize()
            candidate_dirs.extend(
                (
                    desired_dir.rotate(90),
                    desired_dir.rotate(-90),
                    -desired_dir,
                )
            )

        tried: set[tuple[int, int]] = set()
        nudge_distance = max(16.0, enemy.speed * dt * 0.72)
        best_gain = moved.length_squared()
        for direction in candidate_dirs:
            if direction.length_squared() <= 0:
                continue
            normalized = direction.normalize()
            key = (int(round(normalized.x * 1000)), int(round(normalized.y * 1000)))
            if key in tried:
                continue
            tried.add(key)
            before = enemy.pos.copy()
            extra = self.move_circle_with_collisions(
                enemy.pos,
                enemy.radius,
                normalized * nudge_distance,
            )
            if extra.length_squared() > best_gain + 4:
                return enemy.pos - start
            enemy.pos = before
        return enemy.pos - start

    def start_run(self, start_room: int | None = None) -> None:
        self.restart_run()
        self.apply_selected_loadout()
        self.base_progress = start_room or 1
        self.room_index = self.base_progress
        self.rooms_cleared = max(0, self.base_progress - 1)
        self.mode = "playing"
        self.open_title_panel("main")
        self.build_floor()

    def character_profile(self, character_key: str | None = None) -> CharacterProfile:
        key = self.selected_character.key if character_key is None else character_key
        return CHARACTER_PROFILES.get(key, CharacterProfile())

    def character_skill_data(self, skill_key: str | None = None) -> CharacterSkill:
        key = self.active_skill_key if skill_key is None else skill_key
        return CHARACTER_SKILLS.get(key, CHARACTER_SKILLS["pulse"])

    def active_skill_cooldown(self) -> float:
        if self.active_skill_key == "pulse":
            return self.pulse_cooldown
        return self.character_skill_data().cooldown

    def basketball_projectile_speed(self) -> float:
        return config.BULLET_SPEED * self.basketball_speed_scale

    def basketball_upgrade_cap_reached(self) -> bool:
        return self.basketball_upgrade_level >= config.BASKETBALL_UPGRADE_CAP

    def mamba_upgrade_cap_reached(self) -> bool:
        return self.mamba_upgrade_level >= config.MAMBA_UPGRADE_CAP

    def kunkun_chip_bonus_tiers(self) -> int:
        if self.selected_character.key != "kunkun":
            return 0
        return min(
            int(round(config.KUNKUN_CHIP_DAMAGE_CAP / config.KUNKUN_CHIP_DAMAGE_STEP)),
            self.credits // config.KUNKUN_CHIP_DAMAGE_INTERVAL,
        )

    def player_damage_multiplier(self) -> float:
        return 1.0 + self.kunkun_chip_bonus_tiers() * config.KUNKUN_CHIP_DAMAGE_STEP

    def displayed_player_damage(self) -> float:
        return self.player_damage * self.player_damage_multiplier()

    def configure_character_skill(self, skill_key: str) -> None:
        skill = self.character_skill_data(skill_key)
        self.active_skill_key = skill.key
        self.active_skill_name = skill.name
        self.active_skill_label = skill.hud_label

    def active_skill_handler(self):
        return {
            "pulse": self.try_pulse,
            "basketball": self.try_basketball_skill,
            "mamba_smash": self.try_mamba_smash,
        }.get(self.active_skill_key)

    def vanguard_shockwave_available(self) -> bool:
        return (
            self.selected_character.key == "vanguard"
            and self.active_skill_key == "pulse"
        )

    def can_begin_q_hold(self) -> bool:
        return (
            (self.selected_character.key == "kunkun" and self.active_skill_key == "basketball")
            or self.vanguard_shockwave_available()
        )

    def reset_q_skill_hold_state(self) -> None:
        self.q_skill_hold_active = False
        self.q_skill_hold_timer = 0.0

    def begin_q_skill_hold(self) -> bool:
        if not self.can_begin_q_hold():
            return False
        self.q_skill_hold_active = True
        self.q_skill_hold_timer = 0.0
        return True

    def release_q_skill_hold(self) -> bool:
        if not self.q_skill_hold_active:
            return False
        hold_time = self.q_skill_hold_timer
        self.reset_q_skill_hold_state()
        if self.selected_character.key == "kunkun" and self.active_skill_key == "basketball":
            if hold_time >= config.KUNKUN_BARRAGE_HOLD_TIME:
                self.try_kunkun_chip_barrage()
            else:
                self.try_use_active_skill()
            return True
        if self.vanguard_shockwave_available():
            if hold_time >= config.VANGUARD_SHOCKWAVE_HOLD_TIME:
                self.try_vanguard_shockwave()
            else:
                self.try_use_active_skill()
        return True

    def active_skill_status_text(self) -> str:
        return "\u5c31\u7eea" if self.skill_timer <= 0 else f"{self.skill_timer:.1f}s"

    def active_player_buff_status_text(self) -> str:
        if not self.player_buffs:
            return ""
        parts: list[str] = []
        for buff in sorted(self.player_buffs, key=lambda item: item.duration, reverse=True):
            definition = PLAYER_BUFFS.get(buff.key)
            if definition is None:
                continue
            parts.append(f"{definition.hud_label} {max(1, int(math.ceil(buff.duration)))}s")
            if len(parts) >= 2:
                break
        return " \u00b7 ".join(parts)

    def get_player_buff(self, key: str) -> ActivePlayerBuff | None:
        for buff in self.player_buffs:
            if buff.key == key and buff.duration > 0:
                return buff
        return None

    def has_player_buff(self, key: str) -> bool:
        return self.get_player_buff(key) is not None

    def add_player_buff(self, key: str, duration: float, potency: float = 1.0) -> None:
        definition = PLAYER_BUFFS.get(key)
        if definition is None or duration <= 0:
            return
        existing = self.get_player_buff(key)
        if existing is None:
            self.player_buffs.append(
                ActivePlayerBuff(
                    key=key,
                    duration=duration,
                    max_duration=duration,
                    potency=potency,
                )
            )
        else:
            existing.duration = max(existing.duration, duration)
            existing.max_duration = max(existing.max_duration, duration)
            existing.potency = max(existing.potency, potency)
        self.floaters.append(
            FloatingText(
                self.player_pos.copy() + pygame.Vector2(0, -26),
                definition.name,
                definition.color,
                0.9,
            )
        )
        self.message = f"获得 {definition.name} 状态"

    def update_player_buffs(self, dt: float) -> None:
        remaining: list[ActivePlayerBuff] = []
        for buff in self.player_buffs:
            buff.duration = max(0.0, buff.duration - dt)
            if buff.duration > 0:
                remaining.append(buff)
        self.player_buffs = remaining

    def player_healing_blocked(self) -> bool:
        for buff in self.player_buffs:
            definition = PLAYER_BUFFS.get(buff.key)
            if definition is not None and definition.blocks_healing and buff.duration > 0:
                return True
        return False

    def show_heal_blocked_feedback(self, pos: pygame.Vector2 | None = None) -> None:
        anchor = self.player_pos.copy() if pos is None else pos.copy()
        self.floaters.append(
            FloatingText(anchor, "辐射抑制", config.RADIATION_COLOR, 0.72)
        )
        self.message = "辐射状态下无法回血"

    def heal_player(
        self, amount: float, *, pos: pygame.Vector2 | None = None
    ) -> float:
        if amount <= 0:
            return 0.0
        if self.player_healing_blocked():
            self.show_heal_blocked_feedback(pos)
            return 0.0
        healed = min(float(amount), max(0.0, self.player_max_hp - self.player_hp))
        if healed <= 0:
            return 0.0
        self.player_hp += healed
        anchor = self.player_pos.copy() if pos is None else pos.copy()
        self.floaters.append(
            FloatingText(anchor, f"+{int(round(healed))} 生命", config.HEAL_COLOR, 0.6)
        )
        return healed

    @staticmethod
    def scaled_ratio_amount(base_value: float, ratio: float, minimum: float = 1.0) -> float:
        if base_value <= 0 or ratio <= 0:
            return 0.0
        return max(minimum, base_value * ratio)

    def restore_player_shield(
        self, amount: float, *, pos: pygame.Vector2 | None = None
    ) -> float:
        if amount <= 0:
            return 0.0
        restored = min(
            float(amount),
            max(0.0, self.player_max_shield - self.player_shield),
        )
        if restored <= 0:
            return 0.0
        self.player_shield += restored
        anchor = self.player_pos.copy() if pos is None else pos.copy()
        self.floaters.append(
            FloatingText(anchor, f"+{int(round(restored))} 护盾", config.SHIELD_COLOR, 0.6)
        )
        return restored

    def player_damage_taken_multiplier(self) -> float:
        multiplier = 1.0
        for buff in self.player_buffs:
            definition = PLAYER_BUFFS.get(buff.key)
            if definition is None or buff.duration <= 0:
                continue
            multiplier *= definition.damage_taken_multiplier
        return max(0.0, multiplier)

    def player_prevents_stun(self) -> bool:
        for buff in self.player_buffs:
            definition = PLAYER_BUFFS.get(buff.key)
            if definition is not None and definition.prevents_stun and buff.duration > 0:
                return True
        return False

    def player_actions_locked(self) -> bool:
        for buff in self.player_buffs:
            definition = PLAYER_BUFFS.get(buff.key)
            if definition is not None and definition.locks_input and buff.duration > 0:
                return True
        return False

    def cancel_skill_cast(self) -> None:
        self.skill_cast_key = None
        self.skill_cast_timer = 0.0
        self.skill_cast_total = 0.0
        self.skill_cast_direction = pygame.Vector2()

    def try_apply_player_stun(self, duration: float) -> bool:
        if duration <= 0 or self.player_prevents_stun():
            return False
        self.cancel_skill_cast()
        self.add_player_buff("stunned", duration)
        return True

    def add_enemy_status(
        self,
        enemy: Enemy,
        key: str,
        duration: float,
        damage: float,
        tick_interval: float,
        color: tuple[int, int, int],
    ) -> None:
        if duration <= 0 or damage <= 0 or tick_interval <= 0:
            return
        existing = next((status for status in enemy.statuses if status.key == key), None)
        if existing is None:
            enemy.statuses.append(
                ActiveEnemyStatus(
                    key=key,
                    duration=duration,
                    max_duration=duration,
                    tick_interval=tick_interval,
                    tick_timer=tick_interval,
                    damage=damage,
                    color=color,
                )
            )
            self.floaters.append(
                FloatingText(enemy.pos.copy(), "中毒", color, 0.42)
            )
            return
        existing.duration = max(existing.duration, duration)
        existing.max_duration = max(existing.max_duration, duration)
        existing.damage = max(existing.damage, damage)
        existing.tick_interval = min(existing.tick_interval, tick_interval)
        existing.tick_timer = min(existing.tick_timer, existing.tick_interval)
        existing.color = color

    def enemy_has_status(self, enemy: Enemy, key: str) -> bool:
        return any(status.key == key and status.duration > 0 for status in enemy.statuses)

    def update_enemy_statuses(self, enemy: Enemy, dt: float) -> bool:
        remaining: list[ActiveEnemyStatus] = []
        for status in enemy.statuses:
            status.duration = max(0.0, status.duration - dt)
            status.tick_timer -= dt
            while status.duration > 0 and status.tick_timer <= 0:
                enemy.hp -= status.damage
                self.spawn_particles(
                    enemy.pos.copy(),
                    status.color,
                    2,
                    0.36,
                    (0.8, 1.8),
                    (0.06, 0.14),
                )
                self.floaters.append(
                    FloatingText(
                        enemy.pos.copy() + pygame.Vector2(0, -16),
                        str(int(round(status.damage))),
                        status.color,
                        0.28,
                    )
                )
                status.tick_timer += max(0.12, status.tick_interval)
                if enemy.hp <= 0:
                    self.kill_enemy(enemy)
                    enemy.statuses.clear()
                    return True
            if status.duration > 0:
                remaining.append(status)
        enemy.statuses = remaining
        return False

    def apply_player_attack_effects(self, enemy: Enemy) -> None:
        if enemy.hp <= 0:
            return
        for buff in self.player_buffs:
            definition = PLAYER_BUFFS.get(buff.key)
            if definition is None:
                continue
            if (
                definition.poison_on_hit_duration > 0
                and definition.poison_on_hit_damage > 0
                and definition.poison_tick_interval > 0
            ):
                potency = max(0.1, buff.potency)
                self.add_enemy_status(
                    enemy,
                    "poison",
                    definition.poison_on_hit_duration * potency,
                    definition.poison_on_hit_damage * potency,
                    definition.poison_tick_interval,
                    config.POISON_STATUS_COLOR,
                )

    def selected_character_skill_summary(self, character: CharacterOption | None = None) -> str:
        current = self.selected_character if character is None else character
        skill = self.character_skill_data(current.skill_key)
        return f"技能：{skill.description}"

    def selected_character_detail_text(self) -> str:
        return f"{self.selected_character.passive}；{self.selected_character_skill_summary()}"

    def apply_selected_loadout(self) -> None:
        profile = self.character_profile()
        self.player_max_hp += profile.hp_bonus
        self.player_hp = self.player_max_hp
        self.player_max_shield += profile.shield_bonus
        self.player_shield = min(self.player_max_shield, self.player_shield + profile.shield_bonus)
        self.player_speed += profile.speed_bonus
        self.pickup_radius += profile.pickup_radius_bonus
        self.dash_distance += profile.dash_distance_bonus
        self.dash_cooldown *= profile.dash_cooldown_mult
        self.pulse_cooldown *= profile.pulse_cooldown_mult
        self.pulse_push_force += profile.pulse_push_bonus
        self.credits += profile.starting_credits
        if self.selected_character.key == "mamba":
            self.player_revives_remaining = 1
        self.configure_character_skill(profile.skill_key)

        self.weapon_mode = "projectile"
        self.player_beam_width = 10
        self.player_beam_color = config.BULLET_COLOR
        self.player_projectile_speed = float(config.BULLET_SPEED)
        self.player_projectile_ttl = 1.5
        self.player_projectile_radius = config.BULLET_RADIUS
        self.player_projectile_knockback = config.PROJECTILE_BASE_KNOCKBACK
        self.player_rocket_explosion_radius = 0.0
        self.player_rocket_explosion_knockback = 0.0
        self.player_shotgun_pellets = 1
        self.player_shotgun_spread = 0.0
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
            self.player_damage = config.RAIL_BASE_DAMAGE
            self.fire_cooldown = config.RAIL_FIRE_COOLDOWN
            self.player_spread = 0.006
            self.player_crit_chance = 0.24
            self.player_crit_multiplier = 2.30
            self.bullet_pierce += 1
            self.player_projectile_speed = (
                config.BULLET_SPEED * config.RAIL_PROJECTILE_SPEED_SCALE
            )
            self.player_projectile_ttl = 1.8
        elif self.selected_weapon.key == "rocket":
            self.player_damage = config.ROCKET_DAMAGE
            self.fire_cooldown = config.ROCKET_FIRE_COOLDOWN
            self.player_spread = 0.012
            self.player_crit_chance = 0.12
            self.player_crit_multiplier = 2.15
            self.player_projectile_speed = config.BULLET_SPEED * config.ROCKET_PROJECTILE_SPEED_SCALE
            self.player_projectile_ttl = config.ROCKET_PROJECTILE_TTL
            self.player_projectile_radius = config.ROCKET_PROJECTILE_RADIUS
            self.player_projectile_knockback = 0.0
            self.player_rocket_explosion_radius = config.ROCKET_EXPLOSION_RADIUS
            self.player_rocket_explosion_knockback = config.ROCKET_EXPLOSION_KNOCKBACK
        elif self.selected_weapon.key == "shotgun":
            self.player_damage = 7.0
            self.fire_cooldown = 0.54
            self.player_spread = 0.02
            self.player_crit_chance = 0.04
            self.player_crit_multiplier = 1.45
            self.player_projectile_speed = (
                config.BULLET_SPEED * config.SHOTGUN_PELLET_SPEED_SCALE
            )
            self.player_projectile_ttl = config.SHOTGUN_BASE_TTL
            self.player_projectile_knockback = config.SHOTGUN_KNOCKBACK
            self.player_shotgun_pellets = config.SHOTGUN_BASE_PELLETS
            self.player_shotgun_spread = config.SHOTGUN_BASE_SPREAD
        elif self.selected_weapon.key == "laser_burst":
            self.weapon_mode = "laser"
            self.player_damage = 6.0
            self.fire_cooldown = config.LASER_BURST_FIRE_COOLDOWN
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

    def is_laser_weapon(self) -> bool:
        return self.weapon_mode == "laser" or "laser" in self.active_weapon_tags()

    def is_shotgun_weapon(self) -> bool:
        return "shotgun" in self.active_weapon_tags()

    def is_rocket_weapon(self) -> bool:
        return self.selected_weapon.key == "rocket"

    def active_weapon_keys(self) -> tuple[str, ...]:
        return (self.selected_weapon.key,)

    def active_weapon_tags(self) -> set[str]:
        tags: set[str] = set()
        for weapon_key in self.active_weapon_keys():
            tags.update(WEAPON_TAGS.get(weapon_key, ()))
        return tags

    def ricochet_cap(self) -> int:
        return 3 if self.is_laser_weapon() else 1

    def supports_upgrade(self, upgrade_key: str) -> bool:
        active_keys = set(self.active_weapon_keys())
        active_character_key = self.selected_character.key
        active_skill_key = self.active_skill_key
        allowed_weapons = WEAPON_EXCLUSIVE_UPGRADES.get(upgrade_key)
        if allowed_weapons is not None and not active_keys.intersection(
            allowed_weapons
        ):
            return False

        rule = UPGRADE_WEAPON_RULES.get(upgrade_key)
        if rule is None:
            return True

        active_tags = self.active_weapon_tags()
        if rule.required_weapon_keys and not active_keys.intersection(
            rule.required_weapon_keys
        ):
            return False
        if rule.required_weapon_tags and not active_tags.intersection(
            rule.required_weapon_tags
        ):
            return False
        if rule.required_character_keys and active_character_key not in rule.required_character_keys:
            return False
        if rule.required_skill_keys and active_skill_key not in rule.required_skill_keys:
            return False
        return True

    def multishot_cap(self) -> int:
        return 2

    def shotgun_range_cap_reached(self) -> bool:
        return self.player_projectile_ttl >= config.SHOTGUN_RANGE_CAP

    def rocket_blast_cap_reached(self) -> bool:
        return self.player_rocket_explosion_radius >= config.ROCKET_EXPLOSION_RADIUS_CAP - 0.01

    def is_upgrade_available(self, upgrade_key: str) -> bool:
        if not self.supports_upgrade(upgrade_key):
            return False
        return not (
            (upgrade_key == "multishot" and self.multishot >= self.multishot_cap())
            or (upgrade_key == "ricochet" and self.player_bullet_bounces >= self.ricochet_cap())
            or (upgrade_key == "basketball_training" and self.basketball_upgrade_cap_reached())
            or (upgrade_key == "what_can_i_say" and self.mamba_upgrade_cap_reached())
            or (upgrade_key == "accuracy" and self.player_spread <= 0.004)
            or (upgrade_key == "shotgun_range" and (not self.is_shotgun_weapon() or self.shotgun_range_cap_reached()))
            or (upgrade_key == "rocket_blast" and (not self.is_rocket_weapon() or self.rocket_blast_cap_reached()))
            or (upgrade_key == "crit_rate" and self.player_crit_chance >= 0.45)
            or (upgrade_key == "crit_damage" and self.player_crit_multiplier >= 2.85)
            or (
                upgrade_key == "enemy_bullet_slow"
                and self.enemy_bullet_speed_multiplier <= 0.60
            )
            or (upgrade_key == "credit_boost" and self.credit_gain_multiplier >= 2.0)
        )

    def clear_navigation_fields(self) -> None:
        self.navigation_fields.clear()

    def invalidate_navigation_fields(self) -> None:
        room_state = self.current_room_state
        if room_state is None:
            self.clear_navigation_fields()
            return
        room_state.nav_version += 1
        stale_keys = [
            key for key in self.navigation_fields if key[0] == room_state.room_id
        ]
        for key in stale_keys:
            self.navigation_fields.pop(key, None)

    def get_navigation_field(self, radius: int) -> NavigationField | None:
        if self.room_layout is None or self.current_room_state is None:
            return None
        radius_key = max(config.ENEMY_RADIUS, int(radius))
        room_state = self.current_room_state
        cache_key = (room_state.room_id, room_state.nav_version, radius_key)
        field = self.navigation_fields.get(cache_key)
        if field is None:
            field = NavigationField(
                arena=self.arena_rect(),
                obstacle_rects=tuple(rect.copy() for rect in self.obstacle_rects()),
                agent_radius=radius_key,
                step=config.NAV_GRID_STEP,
                padding=config.NAV_GRID_PADDING,
                tight_gap_extra=config.NAV_TIGHT_GAP_EXTRA,
                cross_gap_extra=config.NAV_CROSS_GAP_EXTRA,
                distance_cache_limit=config.NAV_DISTANCE_CACHE_LIMIT,
                waypoint_cache_limit=config.NAV_WAYPOINT_CACHE_LIMIT,
            )
            self.navigation_fields[cache_key] = field
        return field

    def build_floor(self) -> None:
        arena = self.arena_rect()
        base_difficulty = self.base_progress + (self.floor_index - 1) * 3
        self.floor_map = build_floor_map(
            arena, self.floor_index, base_difficulty, self.rng
        )
        self.room_states = {
            room_id: self.make_room_state(room_def)
            for room_id, room_def in self.floor_map.rooms.items()
        }
        self.kunkun_chip_barrage_used = False
        self.vanguard_shockwave_used = False
        self.reset_q_skill_hold_state()
        self.assign_floor_challenge_room()
        self.bullets.clear()
        self.laser_traces.clear()
        self.explosion_waves.clear()
        self.floaters.clear()
        self.gas_clouds.clear()
        self.clear_navigation_fields()
        self.enemy_pause_timer = 0.0
        self.floor_entry_enemy_grace_pending = True
        self.message = f"进入第 {self.floor_index} 层"
        if self.floor_map is None:
            return
        self.enter_room(self.floor_map.start_room_id, None)

    def room_supports_nuke_event(self, layout: RoomLayout) -> bool:
        return layout.grid_size == (1, 1) or layout.centerpiece == "ring"

    def room_supports_turret_event(self, layout: RoomLayout) -> bool:
        return layout.grid_size == (1, 1) or layout.centerpiece == "ring"

    def should_spawn_nuke_event(self, room_def: FloorRoom) -> bool:
        if room_def.room_type not in {"combat", "elite"}:
            return False
        if not self.room_supports_nuke_event(room_def.layout):
            return False
        profile = nuke_event_profile(room_def.difficulty, self.floor_index)
        return self.rng.random() < profile.chance

    def should_spawn_turret_event(self, room_def: FloorRoom) -> bool:
        if room_def.room_type not in {"combat", "elite"}:
            return False
        if not self.room_supports_turret_event(room_def.layout):
            return False
        return self.rng.random() < config.ROOM_EVENT_TURRET_CHANCE

    def assign_floor_challenge_room(self) -> None:
        if (
            self.floor_index % 3 != 0
            or self.rng.random() >= config.CHALLENGE_ROOM_CHANCE
        ):
            return
        boss_room = next(
            (room for room in self.room_states.values() if room.room_type == "boss"),
            None,
        )
        if boss_room is None:
            return
        boss_room.challenge_tag = "high_difficulty"

    def build_nuke_obstacle(
        self, pos: pygame.Vector2, room_index: int
    ) -> RoomObstacle:
        profile = nuke_event_profile(room_index, self.floor_index)
        size = int(
            config.NUKE_OBSTACLE_SIZE
            + min(14, max(0, self.floor_index - 1) * 2)
        )
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(pos.x), int(pos.y))
        return RoomObstacle(
            rect=rect,
            destructible=True,
            max_hp=profile.hp,
            hp=profile.hp,
            tag="nuke",
            fill_color=config.NUKE_FILL_COLOR,
            border_color=config.NUKE_BORDER_COLOR,
        )

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
            state.shop_offers = self.build_shop_offers(
                room_def.layout, room_def.difficulty
            )
        elif room_def.room_type in {"treasure", "boss"}:
            anchors = self.get_room_feature_points(
                room_def.layout, 1, collision_radius=40
            )
            if anchors:
                state.feature_anchor = anchors[0]
        if self.should_spawn_nuke_event(room_def):
            anchors = self.get_room_feature_points(
                room_def.layout,
                1,
                collision_radius=config.NUKE_OBSTACLE_COLLISION_RADIUS,
            )
            if anchors:
                anchor = anchors[0]
                state.room_event = RoomEventState(
                    key="nuke",
                    anchor=anchor.copy(),
                    spawned=True,
                )
                room_def.layout.obstacles.append(
                    self.build_nuke_obstacle(anchor, room_def.difficulty)
                )
        elif self.should_spawn_turret_event(room_def):
            anchors = self.get_room_feature_points(
                room_def.layout,
                1,
                collision_radius=config.BOSS_RADIUS + 20,
            )
            if anchors:
                state.room_event = RoomEventState(
                    key="elite_turret",
                    anchor=anchors[0].copy(),
                )
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
        self.gas_clouds.clear()
        self.refresh_obstacle_state()
        self.room_clear_delay = 0.0
        self.room_transition_cooldown = 0.45
        self.room_index = room_state.difficulty
        if room_state.room_type == "maze":
            room_state.retreat_door = (
                entry_from
                if (
                    entry_from
                    and self.room_layout is not None
                    and entry_from in self.room_layout.screen_doors
                )
                else None
            )
        else:
            room_state.retreat_door = None

        arena = self.arena_rect()
        if (
            entry_from
            and self.room_layout is not None
            and entry_from in self.room_layout.door_entries
        ):
            self.player_pos = self.room_layout.door_entries[entry_from].copy()
        else:
            self.player_pos = self.find_safe_spawn_position(arena)

        if not room_state.visited:
            room_state.visited = True
            self.prepare_room_state(room_state)
        else:
            if (
                room_state.room_type in ("combat", "maze", "elite", "boss")
                and not room_state.resolved
            ):
                room_state.doors_locked = bool(room_state.enemies)
            self.message = f"第 {self.floor_index} 层 · {self.room_display_label(room_state)}"

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
        spawn_min_distance = max(180.0, config.NEW_ROOM_ENEMY_SPAWN_DISTANCE)
        self.enemy_pause_timer = max(self.enemy_pause_timer, config.NEW_ROOM_ENEMY_GRACE)
        if self.floor_entry_enemy_grace_pending:
            spawn_min_distance = max(spawn_min_distance, config.NEW_FLOOR_ENEMY_SPAWN_DISTANCE)
            self.enemy_pause_timer = max(self.enemy_pause_timer, config.NEW_FLOOR_ENEMY_GRACE)
            self.floor_entry_enemy_grace_pending = False
        self.spawn_room_pickups(arena)
        self.populate_room_enemies(room_state, arena, spawn_min_distance)
        self.spawn_room_event_enemy(room_state, arena, spawn_min_distance)
        room_label = self.room_display_label(room_state)
        if self.enemy_pause_timer > 0:
            self.message = f"第 {self.floor_index} 层 · {room_label}（缓冲）"
        else:
            self.message = f"第 {self.floor_index} 层 · {room_label}"

    def spawn_room_event_enemy(
        self, room_state: RoomState, arena: pygame.Rect, min_distance: float
    ) -> None:
        event_state = room_state.room_event
        if (
            event_state is None
            or event_state.completed
            or event_state.key != "elite_turret"
            or event_state.anchor is None
        ):
            return
        turret = self.make_theme_enemy(
            arena,
            "elite_turret",
            min_distance=min_distance,
        )
        turret.pos = event_state.anchor.copy()
        self.clamp_circle_to_arena(turret.pos, turret.radius)
        self.push_circle_out_of_obstacles(turret.pos, turret.radius)
        turret.navigation.force_repath = False
        room_state.enemies.append(turret)
        event_state.spawned = True

    def populate_room_enemies(self, room_state: RoomState, arena: pygame.Rect, min_distance: float = 180.0) -> None:
        room_state.enemies.clear()
        theme = room_state.layout.theme
        shooter_cap = 1 if room_state.difficulty <= 5 else 2
        if theme == "反应堆室":
            shooter_cap += 1
        shooter_count = 0
        if room_state.challenge_tag == "high_difficulty":
            self.populate_high_difficulty_room(
                room_state,
                arena,
                min_distance=min_distance,
                shooter_cap=max(1, shooter_cap),
            )
            return
        if room_state.room_type == "combat":
            count = 4 + room_state.difficulty * 2
            if theme == "开阔车间":
                count += 1
            elif theme == "封锁壁垒":
                count = max(4, count - 1)
            for _ in range(count):
                enemy = self.make_enemy(arena, min_distance=min_distance)
                shooter_count = self.limit_shooter(enemy, shooter_count, shooter_cap)
                room_state.enemies.append(enemy)
            self.inject_theme_enemies(room_state, arena, min_distance=min_distance)
            return

        if room_state.room_type == "maze":
            count = 3 + room_state.difficulty * 2
            shooter_cap = max(1, shooter_cap - 1)
            if theme == "封锁壁垒":
                count = max(4, count - 1)
            for _ in range(count):
                enemy = self.make_enemy(arena, min_distance=min_distance)
                shooter_count = self.limit_shooter(enemy, shooter_count, shooter_cap)
                room_state.enemies.append(enemy)
            self.inject_theme_enemies(room_state, arena, min_distance=min_distance)
            return

        if room_state.room_type == "elite":
            count = 3 + room_state.difficulty
            if theme == "废料堆场":
                count += 1
            for idx in range(count):
                enemy = self.make_enemy(arena, min_distance=min_distance)
                if idx < 2:
                    self.promote_elite_enemy(enemy)
                shooter_count = self.limit_shooter(
                    enemy, shooter_count, max(1, shooter_cap)
                )
                room_state.enemies.append(enemy)
            self.inject_theme_enemies(room_state, arena, min_distance=min_distance)
            return

        if room_state.room_type == "boss":
            room_state.enemies.append(self.make_boss(arena, min_distance=max(220.0, min_distance)))
            add_count = 2 + max(0, room_state.difficulty // 3)
            if theme == "封锁壁垒":
                add_count += 1
            for idx in range(add_count):
                enemy = self.make_enemy(arena, min_distance=min_distance)
                if idx == 0 and enemy.kind == "grunt":
                    self.promote_elite_enemy(enemy)
                shooter_count = self.limit_shooter(
                    enemy, shooter_count, max(1, shooter_cap)
                )
                room_state.enemies.append(enemy)
            self.inject_theme_enemies(room_state, arena, min_distance=min_distance)

    def populate_high_difficulty_room(
        self,
        room_state: RoomState,
        arena: pygame.Rect,
        *,
        min_distance: float,
        shooter_cap: int,
    ) -> None:
        room_state.enemies.append(
            self.make_boss(
                arena,
                min_distance=max(220.0, min_distance),
                variant="challenge",
            )
        )
        add_count = 1 + max(0, room_state.difficulty // 4)
        if room_state.room_type == "elite":
            add_count += 1
        shooter_count = 0
        for idx in range(add_count):
            enemy = self.make_enemy(arena, min_distance=min_distance)
            if idx == 0 and enemy.kind == "grunt":
                self.promote_elite_enemy(enemy)
            shooter_count = self.limit_shooter(
                enemy, shooter_count, max(1, shooter_cap)
            )
            room_state.enemies.append(enemy)
        self.inject_theme_enemies(room_state, arena, min_distance=min_distance)

    def themed_enemy_kind(self, theme: str) -> str | None:
        if theme == "开阔车间":
            return "engineer"
        if theme == "掩体工带":
            return "turret"
        if theme == "废料堆场":
            return "toxic_bloater"
        if theme == "反应堆室":
            return "reactor_bomber"
        return None

    def themed_enemy_count(self, room_state: RoomState) -> int:
        if self.themed_enemy_kind(room_state.layout.theme) is None:
            return 0
        if room_state.layout.theme == "掩体工带":
            return 2 if room_state.room_type == "elite" else 1
        if room_state.room_type == "elite":
            return 2
        if room_state.room_type == "boss":
            return 1
        return 1 if room_state.room_type in {"combat", "maze"} else 0

    def make_theme_enemy(self, arena: pygame.Rect, kind: str, min_distance: float = 180.0) -> Enemy:
        if self.room_layout is not None and self.room_layout.enemy_cells:
            pos = self.random_free_position(
                arena,
                config.ENEMY_RADIUS + 10,
                allowed_cells=self.room_layout.enemy_cells,
                min_distance=min_distance,
            )
        else:
            pos = self.random_free_position(arena, config.ENEMY_RADIUS + 10, min_distance=min_distance)
        hp_scale, damage_scale, speed_bonus = enemy_scaling(self.room_index, self.floor_index)
        base_speed = (config.ENEMY_SPEED + speed_bonus) * config.ENEMY_GLOBAL_SPEED_SCALE
        damage = config.ENEMY_TOUCH_DAMAGE * damage_scale
        xp_reward = 10 + self.room_index // 2 + max(0, self.floor_index - 1)
        if kind == "engineer":
            return Enemy(
                pos=pos,
                hp=42 * hp_scale,
                max_hp=42 * hp_scale,
                speed=base_speed * 0.92,
                radius=config.ENEMY_RADIUS + 1,
                damage=damage * 0.98,
                xp_reward=xp_reward + 5,
                color=config.ENGINEER_ENEMY_COLOR,
                knockback_resist=1.04,
                kind=kind,
                shield_damage_multiplier=config.ENGINEER_SHIELD_DAMAGE_MULT,
            )
        if kind in {"turret", "elite_turret"}:
            elite_turret = kind == "elite_turret"
            hp = 46 * hp_scale
            turret_damage = damage * 0.92
            xp_bonus = 7
            radius = config.ENEMY_RADIUS + 3
            color = config.TURRET_ENEMY_COLOR
            if elite_turret:
                hp *= config.ROOM_EVENT_TURRET_ELITE_HP_MULT
                turret_damage *= config.ROOM_EVENT_TURRET_ELITE_DAMAGE_MULT
                xp_bonus += config.ROOM_EVENT_TURRET_ELITE_XP_BONUS
                radius += config.ROOM_EVENT_TURRET_ELITE_RADIUS_BONUS
                color = config.TURRET_ELITE_COLOR
            cooldown = max(
                0.9 if elite_turret else 1.18,
                enemy_attack_cooldown("shooter", self.room_index, self.floor_index)
                * (0.86 if elite_turret else 1.0),
            )
            return Enemy(
                pos=pos,
                hp=hp,
                max_hp=hp,
                speed=0.0,
                radius=radius,
                damage=turret_damage,
                xp_reward=xp_reward + xp_bonus,
                color=color,
                knockback_resist=2.6 if elite_turret else 2.2,
                kind="turret",
                variant="elite_turret" if elite_turret else "turret",
                shoot_cooldown=cooldown,
                shoot_timer=self.rng.random() * cooldown,
                immobile=True,
            )
        if kind == "toxic_bloater":
            return Enemy(
                pos=pos,
                hp=34 * hp_scale,
                max_hp=34 * hp_scale,
                speed=base_speed * 0.86,
                radius=config.ENEMY_RADIUS + 1,
                damage=damage * 0.92,
                xp_reward=xp_reward + 4,
                color=config.TOXIC_ENEMY_COLOR,
                knockback_resist=0.95,
                kind=kind,
            )
        return Enemy(
            pos=pos,
            hp=40 * hp_scale,
            max_hp=40 * hp_scale,
            speed=base_speed * 0.82,
            radius=config.ENEMY_RADIUS + 2,
            damage=damage * 1.06,
            xp_reward=xp_reward + 5,
            color=config.REACTOR_ENEMY_COLOR,
            knockback_resist=1.08,
            kind=kind,
        )

    def inject_theme_enemies(self, room_state: RoomState, arena: pygame.Rect, min_distance: float = 180.0) -> None:
        special_kind = self.themed_enemy_kind(room_state.layout.theme)
        special_count = self.themed_enemy_count(room_state)
        if special_kind is None or special_count <= 0 or not room_state.enemies:
            return
        preferred = [
            idx
            for idx, enemy in enumerate(room_state.enemies)
            if not enemy.is_boss
            and enemy.kind not in {"elite", "turret", "engineer", "toxic_bloater", "reactor_bomber"}
        ]
        fallback = [
            idx
            for idx, enemy in enumerate(room_state.enemies)
            if not enemy.is_boss and idx not in preferred
        ]
        self.rng.shuffle(preferred)
        self.rng.shuffle(fallback)
        candidate_indices = preferred + fallback
        for idx in candidate_indices[:special_count]:
            anchor = room_state.enemies[idx].pos.copy()
            themed_enemy = self.make_theme_enemy(arena, special_kind, min_distance=min_distance)
            themed_enemy.pos = anchor
            room_state.enemies[idx] = themed_enemy

    def limit_shooter(self, enemy: Enemy, shooter_count: int, shooter_cap: int) -> int:
        if enemy.kind not in {"shooter", "laser", "shotgunner"}:
            return shooter_count
        if shooter_count >= shooter_cap:
            if enemy.kind == "laser":
                enemy.kind = "shooter"
                enemy.color = config.SHOOTER_COLOR
                enemy.speed *= 1.04
                enemy.damage *= 0.82
                enemy.max_hp *= 0.95
                enemy.hp = min(enemy.hp, enemy.max_hp)
                enemy.shoot_cooldown = enemy_attack_cooldown(
                    "shooter", self.room_index, self.floor_index
                )
                enemy.shoot_timer = self.rng.random() * enemy.shoot_cooldown
                enemy.aim_direction = pygame.Vector2()
                return shooter_count
            if enemy.kind == "shotgunner":
                enemy.kind = "charger"
                enemy.color = (255, 150, 150)
                enemy.speed *= 1.18
                enemy.damage *= 1.06
                enemy.shoot_cooldown = 0.0
                enemy.shoot_timer = 0.0
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
        enemy.speed *= 1.14
        enemy.damage *= 1.12
        enemy.radius = max(enemy.radius, config.ENEMY_RADIUS + 2)
        enemy.knockback_resist = 1.0
        enemy.max_hp *= 0.96
        enemy.hp = enemy.max_hp
        enemy.xp_reward += 10
        enemy.shoot_cooldown = enemy_attack_cooldown(
            "elite", self.room_index, self.floor_index
        )
        enemy.shoot_timer = self.rng.random() * enemy.shoot_cooldown
        enemy.action_state = ""
        enemy.action_timer = 0.0
        enemy.special_timer = 0.0
        enemy.alt_special_timer = 0.0

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
            if not self.position_hits_obstacle(pos, config.PLAYER_RADIUS):
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
                self.pickups.append(
                    Pickup(
                        pos,
                        25,
                        config.HEAL_PICKUP_RADIUS,
                        "heal",
                        config.HEAL_COLOR,
                        "血包",
                    )
                )
            elif roll < 0.70:
                self.pickups.append(
                    Pickup(
                        pos,
                        22,
                        config.ITEM_PICKUP_RADIUS,
                        "shield",
                        config.SHIELD_COLOR,
                        "护盾",
                    )
                )
            else:
                self.pickups.append(
                    Pickup(
                        pos,
                        1,
                        config.ITEM_PICKUP_RADIUS,
                        "item",
                        config.ITEM_COLOR,
                        "道具",
                    )
                )

    def random_free_position(
        self,
        arena: pygame.Rect,
        radius: int,
        allowed_cells: tuple[tuple[int, int], ...]
        | list[tuple[int, int]]
        | None = None,
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
                if self.position_hits_obstacle(pos, radius):
                    continue
                return pos
        for _ in range(40):
            pos = pygame.Vector2(
                self.rng.randint(arena.left + radius, arena.right - radius),
                self.rng.randint(arena.top + radius, arena.bottom - radius),
            )
            if pos.distance_to(self.player_pos) < min_distance:
                continue
            if self.position_hits_obstacle(pos, radius):
                continue
            return pos
        fallback = pygame.Vector2(arena.center)
        if self.position_hits_obstacle(fallback, radius):
            fallback = pygame.Vector2(arena.centerx, arena.centery + 140)
        return fallback

    def room_type_label(self, room_type: str) -> str:
        labels = {
            "start": "起始间",
            "combat": "战斗间",
            "maze": "迷宫房",
            "elite": "精英间",
            "shop": "商店房",
            "treasure": "宝箱房",
            "boss": "首领房",
        }
        return labels.get(room_type, "战斗区")

    def room_display_label(self, room: RoomState | None) -> str:
        if room is None:
            return "未进入房间"
        if room.challenge_tag == "high_difficulty":
            return "高难首领房" if room.room_type == "boss" else "高难房"
        return self.room_type_label(room.room_type)

    def room_badge_color(self, room: RoomState | None) -> tuple[int, int, int]:
        if room is None:
            return config.PLAYER_COLOR
        if room.challenge_tag == "high_difficulty":
            return config.CHALLENGE_ROOM_COLOR
        return {
            "maze": config.MAZE_ROOM_COLOR,
            "boss": config.BOSS_COLOR,
            "elite": config.BULLET_ELITE_COLOR,
            "shop": config.CREDIT_COLOR,
            "treasure": config.ITEM_COLOR,
        }.get(room.room_type, config.PLAYER_COLOR)

    def current_arena_border_color(self) -> tuple[int, int, int]:
        room = self.current_room_state
        if room is not None and room.challenge_tag == "high_difficulty":
            return config.CHALLENGE_ROOM_COLOR
        return config.ARENA_BORDER

    def is_safe_feature_position(
        self,
        pos: pygame.Vector2,
        obstacles: list[RoomObstacle],
        radius: int,
    ) -> bool:
        arena = self.arena_rect().inflate(-radius * 2, -radius * 2)
        if not arena.collidepoint(pos.x, pos.y):
            return False
        return not any(
            self.circle_intersects_rect(pos, radius, obstacle.rect)
            for obstacle in obstacles
        )

    def build_feature_anchor_candidates(
        self, layout: RoomLayout
    ) -> list[pygame.Vector2]:
        arena = self.arena_rect()
        chambers = sorted(
            layout.chambers.values(),
            key=lambda chamber: (
                abs(chamber.center.y - arena.centery),
                chamber.center.x,
            ),
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

    def get_room_feature_points(
        self, layout: RoomLayout, count: int, collision_radius: int = 26
    ) -> list[pygame.Vector2]:
        points: list[pygame.Vector2] = []
        for candidate in self.build_feature_anchor_candidates(layout):
            if not self.is_safe_feature_position(
                candidate, layout.obstacles, collision_radius
            ):
                continue
            if any(
                candidate.distance_to(existing) < collision_radius * 2.4
                for existing in points
            ):
                continue
            points.append(candidate)
            if len(points) >= count:
                break

        attempts = 0
        while len(points) < count and attempts < 40:
            attempts += 1
            candidate = layout.sample_point(self.rng, margin=collision_radius + 14)
            if not self.is_safe_feature_position(
                candidate, layout.obstacles, collision_radius
            ):
                continue
            if any(
                candidate.distance_to(existing) < collision_radius * 2.4
                for existing in points
            ):
                continue
            points.append(candidate)

        if len(points) < count:
            fallback = [
                point
                for point in self.build_feature_anchor_candidates(layout)
                if point not in points
            ]
            for candidate in fallback:
                if self.is_safe_feature_position(
                    candidate, layout.obstacles, max(18, collision_radius - 4)
                ):
                    points.append(candidate)
                if len(points) >= count:
                    break

        return points[:count]

    def build_shop_offer_positions(self, layout: RoomLayout, count: int) -> list[pygame.Vector2]:
        arena = self.arena_rect()
        center = pygame.Vector2(arena.center)
        wide = min(240.0, arena.width * 0.23)
        narrow = min(150.0, arena.width * 0.14)
        top_y = arena.centery - 104
        bottom_y = arena.centery + 44
        candidates = [
            pygame.Vector2(center.x - narrow, top_y),
            pygame.Vector2(center.x + narrow, top_y),
            pygame.Vector2(center.x - wide, bottom_y),
            pygame.Vector2(center.x, bottom_y),
            pygame.Vector2(center.x + wide, bottom_y),
        ]
        points: list[pygame.Vector2] = []
        for candidate in candidates:
            if not self.is_safe_feature_position(candidate, layout.obstacles, 58):
                continue
            if any(candidate.distance_to(existing) < 120 for existing in points):
                continue
            points.append(candidate)
            if len(points) >= count:
                return points

        for candidate in self.get_room_feature_points(layout, count, collision_radius=48):
            if any(candidate.distance_to(existing) < 110 for existing in points):
                continue
            points.append(candidate.copy())
            if len(points) >= count:
                break
        return points[:count]

    def weighted_pick_unique(
        self,
        options: Sequence[ChoiceT],
        count: int,
        weight_fn: Callable[[ChoiceT], float],
        category_fn: Callable[[ChoiceT], str] | None = None,
    ) -> list[ChoiceT]:
        remaining = list(options)
        picks: list[ChoiceT] = []
        seen_categories: set[str] = set()
        while remaining and len(picks) < count:
            weights: list[float] = []
            for option in remaining:
                weight = max(0.0, float(weight_fn(option)))
                if category_fn is not None:
                    category = category_fn(option)
                    if category in seen_categories:
                        weight *= 0.7
                weights.append(weight)
            total = sum(weights)
            if total <= 0:
                chosen = self.rng.choice(remaining)
            else:
                chosen = self.rng.choices(remaining, weights=weights, k=1)[0]
            picks.append(chosen)
            if category_fn is not None:
                seen_categories.add(category_fn(chosen))
            remaining.remove(chosen)
        return picks

    def upgrade_bucket(self, upgrade_key: str) -> str:
        if upgrade_key in {"damage", "rapid", "crit_rate", "crit_damage"}:
            return "offense"
        if upgrade_key in {"accuracy", "pierce", "multishot", "ricochet"}:
            return "weapon"
        if upgrade_key in {"shotgun_range", "rocket_blast"}:
            return "weapon_mode"
        if upgrade_key in {"max_hp", "heal", "shield_core"}:
            return "defense"
        if upgrade_key in {"speed", "dash"}:
            return "mobility"
        if upgrade_key in {"pulse", "pulse_radius", "basketball_training", "what_can_i_say"}:
            return "skill"
        return "utility"

    def upgrade_offer_weight(self, upgrade: Upgrade, *, shop_context: bool = False) -> float:
        key = upgrade.key
        hp_ratio = 0.0 if self.player_max_hp <= 0 else self.player_hp / self.player_max_hp
        shield_ratio = (
            0.0 if self.player_max_shield <= 0 else self.player_shield / self.player_max_shield
        )
        weight = 1.0
        if key in {"damage", "rapid"}:
            weight += 1.6
        if key == "crit_rate":
            weight += 1.5 if self.player_crit_chance < 0.2 else 0.7
        elif key == "crit_damage":
            weight += 1.4 if self.player_crit_chance >= 0.16 else 0.6
        elif key == "accuracy":
            weight += 1.7 if self.player_spread > 0.035 else 0.8
        elif key == "multishot":
            weight += 1.5 if self.multishot < self.multishot_cap() else 0.4
        elif key == "pierce":
            weight += 1.1 if self.weapon_mode != "laser" else 0.3
        elif key == "ricochet":
            weight += 1.0 if self.player_bullet_bounces < self.ricochet_cap() else 0.3
        elif key in {"max_hp", "heal"}:
            weight += 2.8 if hp_ratio < 0.55 else 0.5
            if shop_context:
                weight += 0.7
        elif key == "shield_core":
            weight += 1.8 if shield_ratio < 0.45 else 0.7
        elif key in {"speed", "dash"}:
            weight += 1.2 if self.player_speed < config.PLAYER_BASE_SPEED + 40 else 0.6
        elif key == "magnet":
            weight += 0.8 if self.pickup_radius < 96 else 0.25
        elif key == "enemy_bullet_slow":
            weight += 1.0 if self.floor_index >= 4 else 0.45
        elif key == "credit_boost":
            weight += 0.8 if self.floor_index <= 6 else 0.45
        elif key == "shotgun_range":
            weight += 2.5 if self.is_shotgun_weapon() else 0.1
        elif key == "rocket_blast":
            weight += 2.6 if self.is_rocket_weapon() else 0.1
        elif key == "pulse":
            weight += 2.0 if self.active_skill_key == "pulse" else 0.1
        elif key == "pulse_radius":
            weight += 1.7 if self.active_skill_key == "pulse" else 0.1
        elif key == "basketball_training":
            weight += 2.2 if self.active_skill_key == "basketball" else 0.1
        elif key == "what_can_i_say":
            weight += 2.2 if self.active_skill_key == "mamba_smash" else 0.1
        if shop_context and key in {"damage", "rapid", "crit_rate", "crit_damage"}:
            weight += 0.4
        return weight

    def shop_offer_weight(self, offer) -> float:
        if offer.key == "repair":
            hp_ratio = 0.0 if self.player_max_hp <= 0 else self.player_hp / self.player_max_hp
            return 4.2 if hp_ratio < 0.55 and not self.player_healing_blocked() else 0.8
        if offer.key == "shield_charge":
            shield_ratio = (
                0.0
                if self.player_max_shield <= 0
                else self.player_shield / self.player_max_shield
            )
            return 3.0 if shield_ratio < 0.45 else 0.9
        return self.upgrade_offer_weight(
            Upgrade(offer.key, offer.name, offer.description),
            shop_context=True,
        )

    def build_shop_offers(self, layout: RoomLayout, difficulty: int) -> list[ShopOffer]:
        template_by_key = {offer.key: offer for offer in SHOP_OFFER_POOL}
        sustain_keys = ("repair", "shield_charge", "shield_core")
        sustain_pool = [
            template_by_key[key]
            for key in sustain_keys
            if key in template_by_key
            and (key not in UPGRADE_KEYS or self.is_upgrade_available(key))
        ]
        sustain_pick = self.weighted_pick_unique(
            sustain_pool,
            1,
            self.shop_offer_weight,
            lambda offer: "sustain",
        )
        pool = [
            offer
            for offer in SHOP_OFFER_POOL
            if offer not in sustain_pick
            and (offer.key not in UPGRADE_KEYS or self.is_upgrade_available(offer.key))
        ]
        picks = [
            *sustain_pick,
            *self.weighted_pick_unique(
                pool,
                4,
                self.shop_offer_weight,
                lambda offer: self.upgrade_bucket(offer.key),
            ),
        ]
        positions = self.build_shop_offer_positions(layout, len(picks))
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
        filtered = [
            upgrade for upgrade in UPGRADES if self.is_upgrade_available(upgrade.key)
        ]
        if len(filtered) <= count:
            return list(filtered)
        return self.weighted_pick_unique(
            filtered,
            count,
            self.upgrade_offer_weight,
            lambda upgrade: self.upgrade_bucket(upgrade.key),
        )

    def make_enemy(self, arena: pygame.Rect, min_distance: float = 180.0) -> Enemy:
        if self.room_layout is not None and self.room_layout.enemy_cells:
            pos = self.random_free_position(
                arena,
                config.ENEMY_RADIUS + 8,
                allowed_cells=self.room_layout.enemy_cells,
                min_distance=min_distance,
            )
        else:
            pos = self.random_free_position(arena, config.ENEMY_RADIUS + 8, min_distance=min_distance)
        hp_scale, damage_scale, speed_bonus = enemy_scaling(self.room_index, self.floor_index)
        roll = self.rng.random()
        kind = "grunt"
        color = config.ENEMY_COLOR
        speed = (config.ENEMY_SPEED + speed_bonus) * config.ENEMY_GLOBAL_SPEED_SCALE
        damage = config.ENEMY_TOUCH_DAMAGE * damage_scale
        xp_reward = 8 + self.room_index // 2 + max(0, self.floor_index - 1)
        radius = config.ENEMY_RADIUS
        shoot_cooldown = 0.0
        knockback_resist = 1.0
        max_hp = 33 * hp_scale
        laser_roll = (
            0.0 if self.room_index < 5 else (0.07 if self.room_index <= 7 else 0.10)
        )
        shooter_roll = 0.14 if self.room_index <= 5 else 0.20
        shotgunner_roll = (
            0.0 if self.room_index < 3 else (0.08 if self.room_index <= 5 else 0.12)
        )
        if laser_roll > 0 and roll < laser_roll:
            kind = "laser"
            color = config.ENEMY_LASER_COLOR
            speed *= 0.76
            damage *= 0.95
            shoot_cooldown = enemy_attack_cooldown(
                "laser", self.room_index, self.floor_index
            )
            xp_reward += 7
            max_hp *= 1.28
        elif self.room_index >= 2 and roll < laser_roll + shooter_roll:
            kind = "shooter"
            color = config.SHOOTER_COLOR
            speed *= 0.78 if self.room_index <= 5 else 0.84
            damage *= 0.62 if self.room_index <= 5 else 0.80
            shoot_cooldown = enemy_attack_cooldown(
                "shooter", self.room_index, self.floor_index
            )
            xp_reward += 4
            max_hp *= 1.10 if self.room_index <= 5 else 1.18
        elif shotgunner_roll > 0 and roll < laser_roll + shooter_roll + shotgunner_roll:
            kind = "shotgunner"
            color = config.SHOTGUN_ENEMY_COLOR
            speed *= 0.92
            damage *= 0.94
            shoot_cooldown = enemy_attack_cooldown(
                "shotgunner", self.room_index, self.floor_index
            )
            xp_reward += 5
            max_hp *= 1.08
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
            speed *= 1.18
            damage *= 1.12
            radius += 2
            shoot_cooldown = enemy_attack_cooldown(
                "elite", self.room_index, self.floor_index
            )
            xp_reward += 10
            knockback_resist = 1.0
            max_hp *= 0.92
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

    def make_boss(
        self,
        arena: pygame.Rect,
        min_distance: float = 220.0,
        *,
        variant: str = "",
    ) -> Enemy:
        if self.room_layout is not None and self.room_layout.enemy_cells:
            pos = self.random_free_position(
                arena,
                config.BOSS_RADIUS + 10,
                allowed_cells=list(self.room_layout.enemy_cells[:2]) or list(self.room_layout.enemy_cells),
                min_distance=min_distance,
            )
        else:
            pos = pygame.Vector2(arena.centerx, arena.top + 70)
        hp_scale, damage_scale, speed_bonus = enemy_scaling(
            self.room_index, self.floor_index
        )
        max_hp = 300 * hp_scale * boss_floor_hp_multiplier(self.floor_index)
        speed = (config.BOSS_SPEED + speed_bonus * 0.35) * config.ENEMY_GLOBAL_SPEED_SCALE
        damage = config.ENEMY_TOUCH_DAMAGE * 1.2 * damage_scale
        radius = config.BOSS_RADIUS
        xp_reward = 50 + self.room_index * 3
        color = config.BOSS_COLOR
        shoot_timer = 0.7
        special_timer = 1.5
        alt_special_timer = 3.4
        knockback_resist = 2.8
        if variant == "challenge":
            max_hp *= config.CHALLENGE_BOSS_HP_MULT
            speed *= 1.08
            damage *= config.CHALLENGE_BOSS_DAMAGE_MULT
            radius += 4
            xp_reward += 28
            color = config.CHALLENGE_ROOM_COLOR
            shoot_timer = 0.45
            special_timer = 0.0
            alt_special_timer = config.CHALLENGE_BOSS_DASH_COOLDOWN * 0.5
            knockback_resist = 3.2
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
            is_boss=True,
            kind="boss",
            variant=variant,
            shoot_cooldown=enemy_attack_cooldown(
                "boss", self.room_index, self.floor_index
            ),
            shoot_timer=shoot_timer,
            special_timer=special_timer,
            alt_special_timer=alt_special_timer,
            summon_timer=config.CHALLENGE_BOSS_SUMMON_COOLDOWN * 0.6
            if variant == "challenge"
            else 0.0,
        )

    def give_xp(self, amount: int) -> None:
        self.xp += amount
        while self.xp >= self.xp_to_level:
            self.xp -= self.xp_to_level
            self.level += 1
            self.xp_to_level = (
                int(self.xp_to_level * config.XP_TO_LEVEL_MULTIPLIER)
                + config.XP_TO_LEVEL_FLAT
            )
            self.mode = "level_up"
            self.upgrade_choices = self.roll_upgrade_choices()

    def apply_upgrade(self, upgrade: Upgrade) -> str:
        applied_name = upgrade.name
        if upgrade.key == "damage":
            self.player_damage *= config.DAMAGE_UPGRADE_MULTIPLIER
        elif upgrade.key == "rapid":
            self.fire_cooldown = max(
                0.11,
                self.fire_cooldown * config.RAPID_UPGRADE_COOLDOWN_MULTIPLIER,
            )
        elif upgrade.key == "accuracy":
            if self.weapon_mode == "laser":
                self.player_damage *= config.LASER_ACCURACY_DAMAGE_MULTIPLIER
                self.player_beam_width = max(10, self.player_beam_width - 1)
                applied_name = (
                    f"{upgrade.name}（转化为聚焦增益 +"
                    f"{int(round((config.LASER_ACCURACY_DAMAGE_MULTIPLIER - 1.0) * 100))}%）"
                )
            else:
                self.player_spread = max(0.004, self.player_spread * 0.82)
        elif upgrade.key == "crit_rate":
            self.player_crit_chance = min(
                0.45, self.player_crit_chance + config.CRIT_RATE_UPGRADE_STEP
            )
        elif upgrade.key == "crit_damage":
            self.player_crit_multiplier = min(
                2.85, self.player_crit_multiplier + config.CRIT_DAMAGE_UPGRADE_STEP
            )
        elif upgrade.key == "speed":
            self.player_speed += config.SPEED_UPGRADE_BONUS
        elif upgrade.key == "max_hp":
            base_max_hp = self.player_max_hp
            self.player_max_hp += self.scaled_ratio_amount(
                base_max_hp,
                config.MAX_HP_UPGRADE_MULTIPLIER - 1.0,
            )
            self.heal_player(
                self.scaled_ratio_amount(base_max_hp, config.MAX_HP_UPGRADE_HEAL_RATIO)
            )
        elif upgrade.key == "heal":
            self.heal_player(
                self.scaled_ratio_amount(self.player_max_hp, config.HEAL_UPGRADE_RATIO)
            )
        elif upgrade.key == "shield_core":
            base_max_shield = self.player_max_shield
            self.player_max_shield += self.scaled_ratio_amount(
                base_max_shield,
                config.SHIELD_CORE_UPGRADE_MULTIPLIER - 1.0,
            )
            self.restore_player_shield(
                self.scaled_ratio_amount(
                    base_max_shield,
                    config.SHIELD_CORE_UPGRADE_RESTORE_RATIO,
                )
            )
        elif upgrade.key == "pierce":
            if self.weapon_mode == "laser":
                self.player_damage += config.LASER_PIERCE_DAMAGE_BONUS
                applied_name = (
                    f"{upgrade.name}（转化为激光伤害 +"
                    f"{int(config.LASER_PIERCE_DAMAGE_BONUS)}）"
                )
            else:
                self.bullet_pierce += 1
        elif upgrade.key == "multishot":
            if self.weapon_mode == "laser":
                self.player_beam_width += 3
                applied_name = f"{upgrade.name}（转化为激光宽度 +3）"
            elif self.multishot < self.multishot_cap():
                self.multishot += 1
            else:
                self.player_damage += config.MULTISHOT_FALLBACK_DAMAGE_BONUS
                applied_name = (
                    f"{upgrade.name}（转化为火力 +"
                    f"{int(config.MULTISHOT_FALLBACK_DAMAGE_BONUS)}）"
                )
        elif upgrade.key == "shotgun_range":
            if self.is_shotgun_weapon() and not self.shotgun_range_cap_reached():
                self.shotgun_range_bonus += config.SHOTGUN_RANGE_STEP
                self.player_projectile_ttl = min(
                    config.SHOTGUN_RANGE_CAP,
                    self.player_projectile_ttl + config.SHOTGUN_RANGE_STEP,
                )
                self.player_shotgun_spread = max(
                    0.08, self.player_shotgun_spread - 0.02
                )
            else:
                applied_name = f"{upgrade.name}（当前武器不可用）"
        elif upgrade.key == "rocket_blast":
            if self.is_rocket_weapon() and not self.rocket_blast_cap_reached():
                self.player_rocket_explosion_radius = min(
                    config.ROCKET_EXPLOSION_RADIUS_CAP,
                    self.player_rocket_explosion_radius + config.ROCKET_EXPLOSION_RADIUS_STEP,
                )
            else:
                applied_name = f"{upgrade.name}（当前武器不可用）"
        elif upgrade.key == "basketball_training":
            if self.active_skill_key == "basketball" and not self.basketball_upgrade_cap_reached():
                self.basketball_upgrade_level += 1
                self.basketball_radius += config.BASKETBALL_UPGRADE_RADIUS_STEP
                self.basketball_speed_scale *= config.BASKETBALL_UPGRADE_SPEED_MULTIPLIER
            else:
                applied_name = f"{upgrade.name}（当前技能不可用）"
        elif upgrade.key == "what_can_i_say":
            if self.active_skill_key == "mamba_smash" and not self.mamba_upgrade_cap_reached():
                self.mamba_upgrade_level += 1
                self.mamba_skill_stun_duration += config.MAMBA_UPGRADE_STUN_STEP
                self.mamba_skill_half_angle += config.MAMBA_UPGRADE_HALF_ANGLE_STEP
            else:
                applied_name = f"{upgrade.name}（当前技能不可用）"
        elif upgrade.key == "magnet":
            self.pickup_radius += 16
        elif upgrade.key == "pulse":
            if self.active_skill_key == "pulse":
                self.pulse_effect_duration += config.PULSE_UPGRADE_DURATION_STEP
                self.pulse_cooldown = max(4.8, self.pulse_cooldown * 0.94)
            else:
                applied_name = f"{upgrade.name}（当前技能不可用）"
        elif upgrade.key == "dash":
            self.dash_cooldown = max(1.0, self.dash_cooldown * 0.93)
            self.player_speed += 8
        elif upgrade.key == "enemy_bullet_slow":
            self.enemy_bullet_speed_multiplier = max(
                0.60, self.enemy_bullet_speed_multiplier * 0.88
            )
        elif upgrade.key == "credit_boost":
            self.credit_gain_multiplier = min(
                2.0,
                self.credit_gain_multiplier + config.CREDIT_BOOST_UPGRADE_STEP,
            )
        elif upgrade.key == "ricochet":
            if self.player_bullet_bounces < self.ricochet_cap():
                self.player_bullet_bounces += 1
            else:
                applied_name = f"{upgrade.name}（已达上限）"
        elif upgrade.key == "pulse_radius":
            if self.active_skill_key == "pulse":
                self.pulse_radius += 22
            else:
                applied_name = f"{upgrade.name}（当前技能不可用）"
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
            self.heal_player(40)
        elif option.key == "overclock":
            self.player_damage += 4
            self.skill_timer = 0.0
        elif option.key == "charge":
            self.dash_timer = 0.0
            self.skill_timer = 0.0
        self.floaters.append(FloatingText(self.player_pos.copy(), option.name, config.PLAYER_COLOR, 0.8))
        self.mode = "playing"
        self.message = f"已获得 {option.name}"

    def get_choice_rects(self) -> list[pygame.Rect]:
        card_width = 248
        card_height = 188
        gap = 24
        total_width = card_width * 3 + gap * 2
        start_x = (config.WIDTH - total_width) // 2
        top = 222
        return [pygame.Rect(start_x + idx * (card_width + gap), top, card_width, card_height) for idx in range(3)]

    def add_screen_shake(self, strength: float, duration: float) -> None:
        if strength <= 0 or duration <= 0:
            return
        self.screen_shake_strength = max(self.screen_shake_strength, strength)
        self.screen_shake_timer = max(self.screen_shake_timer, duration)
        self.screen_shake_total = max(self.screen_shake_total, duration)

    def add_screen_flash(
        self,
        duration: float,
        color: tuple[int, int, int],
        alpha: int,
    ) -> None:
        if duration <= 0 or alpha <= 0:
            return
        self.screen_flash_timer = max(self.screen_flash_timer, duration)
        self.screen_flash_total = max(self.screen_flash_total, duration)
        self.screen_flash_color = color
        self.screen_flash_alpha = max(self.screen_flash_alpha, alpha)

    def update_screen_shake(self, dt: float) -> None:
        if self.screen_shake_timer <= 0:
            self.screen_shake_timer = 0.0
            self.screen_shake_total = 0.0
            self.screen_shake_strength = 0.0
            return
        self.screen_shake_timer = max(0.0, self.screen_shake_timer - dt)
        if self.screen_shake_timer <= 0:
            self.screen_shake_timer = 0.0
            self.screen_shake_total = 0.0
            self.screen_shake_strength = 0.0

    def update_screen_flash(self, dt: float) -> None:
        if self.screen_flash_timer <= 0:
            self.screen_flash_timer = 0.0
            self.screen_flash_total = 0.0
            self.screen_flash_alpha = 0
            return
        self.screen_flash_timer = max(0.0, self.screen_flash_timer - dt)
        if self.screen_flash_timer <= 0:
            self.screen_flash_timer = 0.0
            self.screen_flash_total = 0.0
            self.screen_flash_alpha = 0

    def get_stage_rects(self) -> list[pygame.Rect]:
        return [pygame.Rect(44, 136 + idx * 54, 338, 44) for idx in range(len(STAGES))]

    def get_character_rects(self) -> list[pygame.Rect]:
        return [
            pygame.Rect(44, 320 + idx * 48, 338, 38) for idx in range(len(CHARACTERS))
        ]

    def get_weapon_rects(self) -> list[pygame.Rect]:
        return [pygame.Rect(44, 474 + idx * 44, 338, 36) for idx in range(len(WEAPONS))]

    def get_title_info_panel(self) -> pygame.Rect:
        return pygame.Rect(410, 124, 834, 548)

    def get_title_start_button(self) -> pygame.Rect:
        return pygame.Rect(992, 592, 216, 46)

    def title_detail_sections(self) -> tuple[tuple[str, str, str], ...]:
        return (
            ("\u4efb\u52a1\u7b80\u4ecb", self.selected_stage.name, self.selected_stage.description),
            ("\u5f53\u524d\u673a\u4f53", self.selected_character.name, self.selected_character_detail_text()),
            ("\u5f53\u524d\u6b66\u5668", self.selected_weapon.name, self.selected_weapon.passive),
        )

    def apply_obstacle_damage(self, obstacle: RoomObstacle, damage: float) -> bool:
        if not obstacle.destructible:
            return False
        actual_damage = max(6.0, damage)
        destroyed = obstacle.damage(actual_damage)
        self.floaters.append(
            FloatingText(
                pygame.Vector2(obstacle.rect.center),
                f"{int(actual_damage)}",
                config.ITEM_COLOR,
                0.35,
            )
        )
        if not destroyed:
            return False

        impact_pos = pygame.Vector2(obstacle.rect.center)
        if obstacle in self.obstacles:
            self.obstacles.remove(obstacle)
        self.floaters.append(
            FloatingText(impact_pos, "掩体破坏", config.ITEM_COLOR, 0.55)
        )
        debris_color = (
            obstacle.border_color
            if getattr(obstacle, "border_color", None) is not None
            else config.ITEM_COLOR
        )
        dust_color = (
            obstacle.fill_color
            if getattr(obstacle, "fill_color", None) is not None
            else config.OBSTACLE_BORDER
        )
        self.spawn_particles(
            impact_pos, debris_color, 14, 1.35, (2.0, 5.4), (0.22, 0.55)
        )
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
        self.refresh_obstacle_state()
        self.invalidate_navigation_fields()
        return True

    def spawn_explosion_wave(
        self,
        pos: pygame.Vector2,
        radius: float,
        color: tuple[int, int, int],
        ttl: float = 0.42,
    ) -> None:
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
        affect_player: bool = True,
        affect_enemies: bool = True,
        enemy_knockback: float = 0.0,
        wave_ttl: float = 0.42,
        player_attack: bool = False,
    ) -> None:
        self.spawn_explosion_wave(center, radius, color, ttl=wave_ttl)
        if affect_enemies:
            for enemy in self.enemies[:]:
                distance = enemy.pos.distance_to(center)
                if distance > radius + enemy.radius:
                    continue
                falloff = max(0.46, 1.0 - distance / max(1.0, radius + enemy.radius))
                dealt = damage * falloff
                enemy.hp -= dealt
                if player_attack and enemy.hp > 0:
                    self.apply_player_attack_effects(enemy)
                if enemy_knockback > 0:
                    push_dir = enemy.pos - center
                    if push_dir.length_squared() <= 0:
                        push_dir = pygame.Vector2(self.rng.uniform(-1.0, 1.0), self.rng.uniform(-1.0, 1.0))
                    if push_dir.length_squared() > 0:
                        push = push_dir.normalize() * (enemy_knockback * falloff / enemy.knockback_resist)
                        self.apply_enemy_knockback(enemy, push)
                self.floaters.append(FloatingText(enemy.pos.copy(), str(int(dealt)), color, 0.35))
                if enemy.hp <= 0:
                    self.kill_enemy(enemy)

        player_distance = self.player_pos.distance_to(center)
        if affect_player and player_distance <= radius + config.PLAYER_RADIUS and self.iframes <= 0:
            falloff = max(0.46, 1.0 - player_distance / max(1.0, radius + config.PLAYER_RADIUS))
            self.damage_player(damage * falloff, color, 0.22)

        obstacle_damage = max(12.0, damage * 1.75)
        for obstacle in self.obstacles[:]:
            if obstacle is source or not obstacle.destructible:
                continue
            if not self.circle_intersects_rect(
                center, int(radius), obstacle.rect.inflate(8, 8)
            ):
                continue
            obstacle_center = pygame.Vector2(obstacle.rect.center)
            falloff = max(
                0.55,
                1.0
                - obstacle_center.distance_to(center)
                / max(
                    1.0, radius + max(obstacle.rect.width, obstacle.rect.height) * 0.45
                ),
            )
            self.apply_obstacle_damage(obstacle, obstacle_damage * falloff)

    def nuke_blast_radius(self, center: pygame.Vector2) -> float:
        arena = self.arena_rect()
        corners = (
            pygame.Vector2(arena.topleft),
            pygame.Vector2(arena.topright),
            pygame.Vector2(arena.bottomleft),
            pygame.Vector2(arena.bottomright),
        )
        return max(center.distance_to(corner) for corner in corners) + 24.0

    def spawn_nuke_gas_clouds(
        self, center: pygame.Vector2, cloud_count: int
    ) -> None:
        for idx in range(max(2, cloud_count)):
            angle = self.rng.uniform(0.0, math.tau)
            distance = self.rng.uniform(0.0, 48.0 + idx * 22.0)
            pos = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
            self.clamp_circle_to_arena(pos, 18)
            target_radius = self.rng.uniform(62.0, 136.0)
            ttl = self.rng.uniform(4.6, 7.4)
            damage = self.rng.uniform(4.2, 7.0)
            self.gas_clouds.append(
                self.make_gas_cloud(
                    pos,
                    target_radius,
                    ttl,
                    damage,
                    start_ratio=0.16,
                    growth_time=0.76,
                    activation_delay=0.46,
                )
            )

    def detonate_nuke(self, obstacle: RoomObstacle, impact_pos: pygame.Vector2) -> None:
        profile = nuke_event_profile(self.room_index, self.floor_index)
        blast_radius = self.nuke_blast_radius(impact_pos)
        self.spawn_particles(
            impact_pos.copy(),
            config.NUKE_BORDER_COLOR,
            34,
            1.9,
            (2.2, 7.0),
            (0.18, 0.54),
        )
        self.spawn_particles(
            impact_pos.copy(),
            config.NUKE_CORE_COLOR,
            18,
            1.2,
            (1.8, 5.2),
            (0.14, 0.38),
        )
        self.floaters.append(
            FloatingText(impact_pos.copy(), "核爆", config.NUKE_BORDER_COLOR, 0.8)
        )
        self.apply_explosion_damage(
            impact_pos,
            blast_radius,
            profile.enemy_damage,
            config.NUKE_BORDER_COLOR,
            source=obstacle,
            affect_player=False,
            enemy_knockback=96.0,
            wave_ttl=0.62,
        )
        if self.iframes <= 0:
            player_distance = self.player_pos.distance_to(impact_pos)
            if player_distance <= blast_radius + config.PLAYER_RADIUS:
                falloff = max(
                    0.46,
                    1.0
                    - player_distance
                    / max(1.0, blast_radius + config.PLAYER_RADIUS),
                )
                self.damage_player(
                    profile.player_damage * falloff,
                    config.NUKE_BORDER_COLOR,
                    0.30,
                )
        self.spawn_nuke_gas_clouds(impact_pos, profile.cloud_count)
        self.add_player_buff("radiation", config.RADIATION_BUFF_DURATION)
        self.add_screen_shake(
            config.NUKE_SCREEN_SHAKE, config.NUKE_SCREEN_SHAKE_DURATION
        )
        self.add_screen_flash(
            config.NUKE_FLASH_DURATION,
            (255, 255, 255),
            config.NUKE_FLASH_ALPHA,
        )
        if self.current_room_state is not None and self.current_room_state.room_event is not None:
            self.current_room_state.room_event.completed = True
        self.message = "核弹引爆，区域被辐射污染"

    def handle_destroyed_obstacle(
        self, obstacle: RoomObstacle, impact_pos: pygame.Vector2
    ) -> None:
        theme = (
            self.current_room_state.layout.theme
            if self.current_room_state is not None
            else ""
        )
        tag = getattr(obstacle, "tag", "normal")
        if tag == "normal":
            if theme == "反应堆室":
                tag = "reactor"
            elif theme == "废料堆场":
                tag = "toxic"
        if tag == "reactor" or (
            tag == "normal" and theme == "\u53cd\u5e94\u5806\u5ba4"
        ):
            profile = hazard_profile("reactor", obstacle.rect)
            blast_radius = profile.radius
            blast_damage = profile.damage
            self.spawn_particles(
                impact_pos,
                config.BULLET_SHOCK_COLOR,
                int(18 + blast_radius / 18),
                1.6,
                (2.5, 6.2),
                (0.22, 0.52),
            )
            self.floaters.append(
                FloatingText(
                    impact_pos.copy(),
                    f"反应爆裂 {int(blast_radius)}",
                    config.BULLET_SHOCK_COLOR,
                    0.6,
                )
            )
            self.apply_explosion_damage(
                impact_pos,
                blast_radius,
                blast_damage,
                config.BULLET_SHOCK_COLOR,
                source=obstacle,
            )
        elif tag == "nuke":
            self.detonate_nuke(obstacle, impact_pos)
        elif tag == "bullet":
            self.spawn_bullet_barrel_burst(impact_pos, obstacle.rect)
        elif tag == "toxic" or (
            tag == "normal" and theme == "\u5e9f\u6599\u5806\u573a"
        ):
            profile = hazard_profile("toxic", obstacle.rect)
            self.gas_clouds.append(
                self.make_gas_cloud(
                    impact_pos.copy(),
                    profile.radius,
                    profile.ttl,
                    profile.damage,
                    growth_time=0.56,
                    activation_delay=0.34,
                )
            )
            self.spawn_particles(
                impact_pos,
                (120, 210, 110),
                int(12 + profile.radius / 20),
                0.84,
                (2.5, 5.0),
                (0.4, 0.9),
            )
            self.floaters.append(
                FloatingText(
                    impact_pos.copy(),
                    f"毒气泄露 {int(profile.radius)}",
                    (148, 220, 118),
                    0.6,
                )
            )

    def get_center_action_buttons(self, count: int) -> list[pygame.Rect]:
        total_width = count * 170 + (count - 1) * 24
        start_x = (config.WIDTH - total_width) // 2
        return [pygame.Rect(start_x + idx * 194, 430, 170, 52) for idx in range(count)]

    def handle_choice_click(
        self,
        mouse_pos: tuple[int, int],
        choices: Sequence[ChoiceT],
        callback: Callable[[ChoiceT], object],
    ) -> bool:
        for rect, choice in zip(self.get_choice_rects(), choices):
            if rect.collidepoint(mouse_pos):
                callback(choice)
                self.play_sound("ui_click")
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
        return pygame.Rect(922, 626, 120, 40)

    def get_title_panel_start_button(self) -> pygame.Rect:
        return pygame.Rect(1056, 626, 150, 40)

    def get_title_panel_viewport_rect(self) -> pygame.Rect:
        return pygame.Rect(54, 188, 1152, 392)

    def title_panel_uses_scroll(self, panel: str | None = None) -> bool:
        panel_key = self.title_panel if panel is None else panel
        return panel_key in {"character", "weapon"}

    def title_panel_card_height(self, panel: str | None = None) -> int:
        panel_key = self.title_panel if panel is None else panel
        if panel_key == "weapon":
            return 104
        if panel_key == "character":
            return 112
        return 82

    def title_panel_gap(self, panel: str | None = None) -> int:
        return 12 if self.title_panel_uses_scroll(panel) else 10

    def title_panel_content_height(self, count: int, panel: str | None = None) -> int:
        if count <= 0:
            return 0
        return count * self.title_panel_card_height(panel) + (
            count - 1
        ) * self.title_panel_gap(panel)

    def max_title_panel_scroll(
        self, panel: str | None = None, count: int | None = None
    ) -> float:
        panel_key = self.title_panel if panel is None else panel
        if count is None:
            count = (
                len(self.current_title_options())
                if panel_key == self.title_panel
                else 0
            )
        viewport = self.get_title_panel_viewport_rect()
        return max(
            0.0,
            float(self.title_panel_content_height(count, panel_key) - viewport.height),
        )

    def clamp_title_panel_scroll(
        self, value: float, panel: str | None = None, count: int | None = None
    ) -> float:
        return max(0.0, min(self.max_title_panel_scroll(panel, count), float(value)))

    def reset_title_panel_scroll(self) -> None:
        self.title_panel_scroll = 0.0
        self.title_panel_scroll_target = 0.0

    def update_title_panel_scroll(self, dt: float) -> None:
        if not self.title_panel_uses_scroll():
            self.title_panel_scroll = self.clamp_title_panel_scroll(
                self.title_panel_scroll, self.title_panel
            )
            self.title_panel_scroll_target = self.title_panel_scroll
            return
        blend = min(1.0, dt * config.TITLE_PANEL_SCROLL_LERP)
        self.title_panel_scroll += (
            self.title_panel_scroll_target - self.title_panel_scroll
        ) * blend
        if abs(self.title_panel_scroll_target - self.title_panel_scroll) <= 0.5:
            self.title_panel_scroll = self.title_panel_scroll_target

    def scroll_title_panel(self, delta: float) -> None:
        if self.title_panel == "main":
            return
        count = len(self.current_title_options())
        panel = self.title_panel
        next_value = self.clamp_title_panel_scroll(
            self.title_panel_scroll_target + delta, panel, count
        )
        self.title_panel_scroll_target = next_value
        if not self.title_panel_uses_scroll(panel):
            self.title_panel_scroll = next_value

    def get_title_panel_option_rects(self, count: int) -> list[pygame.Rect]:
        if count <= 0:
            return []
        viewport = self.get_title_panel_viewport_rect()
        inner_left = viewport.left + 8
        inner_width = viewport.width - 28
        top = viewport.top - int(round(self.title_panel_scroll))
        height = self.title_panel_card_height()
        gap = self.title_panel_gap()
        return [
            pygame.Rect(inner_left, top + idx * (height + gap), inner_width, height)
            for idx in range(count)
        ]

    def current_title_options(
        self,
    ) -> list[StageOption | CharacterOption | WeaponOption]:
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
            pygame.K_6: 5,
            pygame.K_KP6: 5,
        }
        return mapping.get(key)

    def open_title_panel(self, panel: str) -> None:
        self.title_panel = panel
        self.reset_title_panel_scroll()
        title, _ = TITLE_PANEL_INFO.get(panel, TITLE_PANEL_INFO["main"])
        self.message = title

    def title_panel_option_index_at(self, mouse_pos: tuple[int, int]) -> int | None:
        viewport = self.get_title_panel_viewport_rect()
        if not viewport.collidepoint(mouse_pos):
            return None
        for idx, rect in enumerate(
            self.get_title_panel_option_rects(len(self.current_title_options()))
        ):
            if rect.collidepoint(mouse_pos):
                return idx
        return None

    def handle_title_click(self, mouse_pos: tuple[int, int]) -> bool:
        if self.title_panel == "main":
            for key, rect in self.get_title_menu_buttons().items():
                if rect.collidepoint(mouse_pos):
                    self.open_title_panel(key)
                    self.play_sound("ui_click")
                    return True
            if self.get_title_start_button().collidepoint(mouse_pos):
                self.start_run(self.selected_stage.start_room)
                self.play_sound("ui_click")
                return True
        else:
            if self.get_title_panel_back_button().collidepoint(mouse_pos):
                self.open_title_panel("main")
                self.play_sound("ui_click")
                return True
            if self.get_title_panel_start_button().collidepoint(mouse_pos):
                self.start_run(self.selected_stage.start_room)
                self.play_sound("ui_click")
                return True
            idx = self.title_panel_option_index_at(mouse_pos)
            if idx is not None:
                self.select_title_option(idx)
                self.open_title_panel("main")
                self.play_sound("ui_click")
                return True
        return False

    def handle_pause_click(self, mouse_pos: tuple[int, int]) -> bool:
        buttons = self.get_center_action_buttons(3)
        if buttons[0].collidepoint(mouse_pos):
            self.mode = "playing"
            self.play_sound("ui_click")
            return True
        if buttons[1].collidepoint(mouse_pos):
            self.start_run(self.selected_stage.start_room)
            self.play_sound("ui_click")
            return True
        if buttons[2].collidepoint(mouse_pos):
            self.open_title_panel("main")
            self.mode = "title"
            self.play_sound("ui_click")
            return True
        return False

    def handle_dead_click(self, mouse_pos: tuple[int, int]) -> bool:
        buttons = self.get_center_action_buttons(2)
        if buttons[0].collidepoint(mouse_pos):
            self.start_run(self.selected_stage.start_room)
            self.play_sound("ui_click")
            return True
        if buttons[1].collidepoint(mouse_pos):
            self.open_title_panel("main")
            self.mode = "title"
            self.play_sound("ui_click")
            return True
        return False

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and self.mode == "title"
                and event.button in (4, 5)
            ):
                direction = -1 if event.button == 4 else 1
                self.scroll_title_panel(direction * config.TITLE_PANEL_SCROLL_STEP)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.mode == "level_up":
                    self.handle_choice_click(
                        event.pos, self.upgrade_choices, self.apply_upgrade
                    )
                elif self.mode == "reward_room":
                    self.handle_choice_click(
                        event.pos, self.reward_choices, self.claim_reward
                    )
                elif self.mode == "supply_room":
                    self.handle_choice_click(
                        event.pos, self.supply_choices, self.claim_supply
                    )
                elif self.mode == "title":
                    self.handle_title_click(event.pos)
                elif self.mode == "paused":
                    self.handle_pause_click(event.pos)
                elif self.mode == "dead":
                    self.handle_dead_click(event.pos)
            elif event.type == pygame.MOUSEWHEEL and self.mode == "title":
                self.scroll_title_panel(-event.y * config.TITLE_PANEL_SCROLL_STEP)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_q and self.mode == "playing":
                    self.release_q_skill_hold()
                elif event.key == pygame.K_q:
                    self.reset_q_skill_hold_state()
            elif event.type == pygame.KEYDOWN:
                if self.mode == "floor_confirm":
                    if event.key == pygame.K_ESCAPE:
                        self.mode = "playing"
                        self.message = "已取消前往下一层"
                    elif event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                        self.advance_floor()
                    continue
                if self.mode == "floor_transition":
                    continue
                if event.key == pygame.K_ESCAPE:
                    if self.mode == "title" and self.title_panel != "main":
                        self.open_title_panel("main")
                    elif self.mode == "playing":
                        self.mode = "paused"
                    elif self.mode == "paused":
                        self.mode = "playing"
                elif self.mode == "title" and event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.start_run(self.selected_stage.start_room)
                elif (
                    self.mode == "title"
                    and self.title_panel == "main"
                    and event.key in (pygame.K_1, pygame.K_KP1)
                ):
                    self.open_title_panel("stage")
                elif (
                    self.mode == "title"
                    and self.title_panel == "main"
                    and event.key in (pygame.K_2, pygame.K_KP2)
                ):
                    self.open_title_panel("character")
                elif (
                    self.mode == "title"
                    and self.title_panel == "main"
                    and event.key in (pygame.K_3, pygame.K_KP3)
                ):
                    self.open_title_panel("weapon")
                elif (
                    self.mode == "title"
                    and self.title_panel != "main"
                    and event.key in (pygame.K_UP, pygame.K_w)
                ):
                    self.scroll_title_panel(-config.TITLE_PANEL_SCROLL_STEP)
                elif (
                    self.mode == "title"
                    and self.title_panel != "main"
                    and event.key in (pygame.K_DOWN, pygame.K_s)
                ):
                    self.scroll_title_panel(config.TITLE_PANEL_SCROLL_STEP)
                elif (
                    self.mode == "title"
                    and self.title_panel != "main"
                    and event.key == pygame.K_PAGEUP
                ):
                    self.scroll_title_panel(-config.TITLE_PANEL_SCROLL_STEP * 2)
                elif (
                    self.mode == "title"
                    and self.title_panel != "main"
                    and event.key == pygame.K_PAGEDOWN
                ):
                    self.scroll_title_panel(config.TITLE_PANEL_SCROLL_STEP * 2)
                elif self.mode == "title" and self.title_panel != "main":
                    idx = self.hotkey_to_index(event.key)
                    if idx is not None and idx < len(self.current_title_options()):
                        self.select_title_option(idx)
                        self.open_title_panel("main")
                elif self.mode == "dead" and event.key == pygame.K_r:
                    self.start_run(self.selected_stage.start_room)
                elif self.mode == "dead" and event.key == pygame.K_m:
                    self.open_title_panel("main")
                    self.mode = "title"
                elif self.mode == "paused" and event.key == pygame.K_r:
                    self.start_run(self.selected_stage.start_room)
                elif self.mode == "paused" and event.key == pygame.K_m:
                    self.open_title_panel("main")
                    self.mode = "title"
                elif self.mode == "playing" and event.key == pygame.K_SPACE:
                    self.try_dash()
                elif self.mode == "playing" and event.key == pygame.K_q:
                    if not self.begin_q_skill_hold():
                        self.try_use_active_skill()
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
        if self.player_actions_locked():
            return
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
            if self.shop_purchase_limit_reached(room):
                self.message = config.SHOP_PURCHASE_LIMIT_MESSAGE
                return
            if offer.key in UPGRADE_KEYS and not self.is_upgrade_available(offer.key):
                self.message = f"{offer.name} 当前已达上限"
                return
            if self.credits < offer.cost:
                self.message = f"晶片不足：{offer.cost}"
                return
            self.credits -= offer.cost
            offer.sold = True
            self.apply_shop_offer(offer)
            if offer.sold:
                room.shop_purchases += 1
            self.play_sound("ui_click")
            return
        if room.room_type == "treasure" and not room.chest_opened:
            chest_pos = self.get_room_feature_anchor(room)
            if self.player_pos.distance_to(chest_pos) <= 70:
                self.reward_source = "treasure"
                self.reward_choices = self.roll_upgrade_choices()
                self.mode = "reward_room"
                self.play_sound("ui_click")
                return
        if room.room_type == "boss" and room.exit_active:
            portal_pos = self.get_room_feature_anchor(room)
            if self.player_pos.distance_to(portal_pos) <= 76:
                self.mode = "floor_confirm"
                self.message = f"确认进入第 {self.floor_index + 1} 层"
                self.play_sound("ui_click")

    def get_nearby_shop_offer(self) -> ShopOffer | None:
        room = self.current_room_state
        if room is None or room.room_type != "shop":
            return None
        for offer in room.shop_offers:
            if self.player_pos.distance_to(offer.pos) <= 72:
                return offer
        return None

    def remaining_shop_purchases(self, room: RoomState | None = None) -> int:
        current_room = self.current_room_state if room is None else room
        if current_room is None or current_room.room_type != "shop":
            return 0
        return max(0, config.SHOP_PURCHASE_LIMIT - current_room.shop_purchases)

    def shop_purchase_limit_reached(self, room: RoomState | None = None) -> bool:
        current_room = self.current_room_state if room is None else room
        return (
            current_room is not None
            and current_room.room_type == "shop"
            and current_room.shop_purchases >= config.SHOP_PURCHASE_LIMIT
        )

    def apply_shop_offer(self, offer: ShopOffer) -> None:
        if offer.key in UPGRADE_KEYS:
            if not self.is_upgrade_available(offer.key):
                self.message = f"{offer.name} 当前已达上限"
                offer.sold = False
                return
            applied_name = self.apply_upgrade(
                Upgrade(offer.key, offer.name, offer.description)
            )
            self.message = f"已购买 {applied_name}"
            return
        elif offer.key == "repair":
            if self.player_healing_blocked():
                offer.sold = False
                self.credits += offer.cost
                self.show_heal_blocked_feedback()
                return
            self.heal_player(40)
        elif offer.key == "shield_charge":
            self.restore_player_shield(30)
        self.message = f"已购买 {offer.name}"

    def resolve_current_room(self) -> None:
        room = self.current_room_state
        if room is None or room.resolved:
            return
        room.resolved = True
        if room.room_event is not None:
            room.room_event.completed = True
        room.doors_locked = False
        self.clear_room_bound_projectiles()
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
            self.pickups.append(
                Pickup(
                    anchor + pygame.Vector2(-18, 0),
                    24,
                    config.ITEM_PICKUP_RADIUS,
                    "shield",
                    config.SHIELD_COLOR,
                    "护盾",
                )
            )
            self.pickups.append(
                Pickup(
                    anchor + pygame.Vector2(18, 0),
                    reward_credit_drop(self.floor_index, "elite"),
                    config.ITEM_PICKUP_RADIUS,
                    "credit",
                    config.CREDIT_COLOR,
                    "晶片",
                )
            )
        elif reward_type == "boss":
            self.pickups.append(
                Pickup(
                    anchor + pygame.Vector2(-24, 0),
                    34,
                    config.ITEM_PICKUP_RADIUS,
                    "shield",
                    config.SHIELD_COLOR,
                    "护盾",
                )
            )
            self.pickups.append(
                Pickup(
                    anchor + pygame.Vector2(24, 0),
                    reward_credit_drop(self.floor_index, "boss"),
                    config.ITEM_PICKUP_RADIUS,
                    "credit",
                    config.CREDIT_COLOR,
                    "晶片",
                )
            )
            self.pickups.append(
                Pickup(
                    anchor + pygame.Vector2(0, -18),
                    1,
                    config.ITEM_PICKUP_RADIUS,
                    "item",
                    config.ITEM_COLOR,
                    "道具",
                )
            )

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
                if self.shop_purchase_limit_reached(room):
                    return config.SHOP_SOLD_OUT_LABEL
                if offer.key in UPGRADE_KEYS and not self.is_upgrade_available(
                    offer.key
                ):
                    return f"{offer.name}（已达上限）"
                return (
                    f"E 购买 {offer.name}（{offer.cost}） · "
                    f"剩余 {self.remaining_shop_purchases(room)} 次"
                )
        elif room.room_type == "treasure" and not room.chest_opened:
            if self.player_pos.distance_to(self.get_room_feature_anchor(room)) <= 70:
                return "E 开启宝箱"
        elif room.room_type == "boss" and room.exit_active:
            if self.player_pos.distance_to(self.get_room_feature_anchor(room)) <= 76:
                return "E 进入下层"
        return ""

    def is_door_locked(self, room: RoomState, direction: str) -> bool:
        if not room.doors_locked:
            return False
        return not (
            room.room_type == "maze"
            and not room.resolved
            and room.retreat_door == direction
        )

    def check_door_transition(self) -> None:
        room = self.current_room_state
        if (
            room is None
            or self.room_layout is None
            or self.room_transition_cooldown > 0
        ):
            return
        for direction, door_rect in self.room_layout.screen_doors.items():
            if self.is_door_locked(room, direction):
                continue
            if not door_rect.collidepoint(self.player_pos.x, self.player_pos.y):
                continue
            next_room_id = room.neighbors.get(direction)
            if next_room_id is None:
                continue
            self.enter_room(next_room_id, OPPOSITE_DIRECTIONS[direction])
            return

    def advance_floor(self) -> None:
        self.play_sound("switch")
        self.mode = "floor_transition"
        self.floor_transition_target = self.floor_index + 1
        self.floor_transition_total = config.FLOOR_TRANSITION_DURATION
        self.floor_transition_timer = config.FLOOR_TRANSITION_DURATION
        self.floor_transition_switched = False
        self.bullets.clear()
        self.laser_traces.clear()
        self.explosion_waves.clear()
        self.floaters.clear()
        self.message = f"正在下潜至第 {self.floor_transition_target} 层"

    def finish_floor_advance(self) -> None:
        self.floor_index = self.floor_transition_target
        self.kunkun_chip_barrage_used = False
        self.vanguard_shockwave_used = False
        self.message = f"进入第 {self.floor_index} 层"
        self.build_floor()

    def update_floor_transition(self, dt: float) -> None:
        if self.floor_transition_timer <= 0:
            self.mode = "playing"
            return
        self.floor_transition_timer = max(0.0, self.floor_transition_timer - dt)
        if (
            not self.floor_transition_switched
            and self.floor_transition_timer <= self.floor_transition_total * 0.5
        ):
            self.floor_transition_switched = True
            self.finish_floor_advance()
        if self.floor_transition_timer <= 0:
            self.mode = "playing"

    def update(self, dt: float) -> None:
        self.update_screen_shake(dt)
        self.update_screen_flash(dt)
        if self.mode == "floor_transition":
            self.reset_q_skill_hold_state()
            self.update_floor_transition(dt)
            return
        if self.mode == "title":
            self.reset_q_skill_hold_state()
            self.update_title_panel_scroll(dt)
            return
        if self.mode != "playing":
            self.reset_q_skill_hold_state()
            return
        self.iframes = max(0.0, self.iframes - dt)
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.skill_timer = max(0.0, self.skill_timer - dt)
        self.room_transition_cooldown = max(0.0, self.room_transition_cooldown - dt)
        self.enemy_pause_timer = max(0.0, self.enemy_pause_timer - dt)
        self.update_player_buffs(dt)
        self.update_player(dt)
        self.update_skill_input_state(dt)
        self.update_active_skill_effects(dt)
        self.update_bullets(dt)
        if self.enemy_pause_timer <= 0:
            self.update_enemies(dt)
        self.update_pickups(dt)
        self.update_gas_clouds(dt)
        self.update_explosion_waves(dt)
        self.update_particles(dt)
        self.update_laser_traces(dt)
        self.update_floaters(dt)
        if (
            self.current_room_state is not None
            and self.current_room_state.room_type in ("combat", "maze", "elite", "boss")
            and self.current_room_state.doors_locked
            and not self.enemies
        ):
            self.clear_room_bound_projectiles()
            self.room_clear_delay += dt
            if self.room_clear_delay >= config.ROOM_CLEAR_FORCE_COLLECT_DELAY:
                self.absorb_all_pickups()
            if (
                self.room_clear_delay >= config.ROOM_CLEAR_NEXT_ROOM_DELAY
                and not self.pickups
            ):
                self.resolve_current_room()
        else:
            self.room_clear_delay = 0.0
        self.check_door_transition()

    def update_player(self, dt: float) -> None:
        if self.player_actions_locked():
            self.move_circle_with_collisions(
                self.player_pos, config.PLAYER_RADIUS, pygame.Vector2()
            )
            return
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            float(keys[pygame.K_d]) - float(keys[pygame.K_a]),
            float(keys[pygame.K_s]) - float(keys[pygame.K_w]),
        )
        move_speed = self.player_speed
        if self.skill_cast_key == "mamba_smash" and self.skill_cast_timer > 0:
            move_speed *= config.MAMBA_SKILL_STARTUP_MOVE_MULT
        if move.length_squared() > 0:
            move = move.normalize()
            self.last_move = move.copy()
            self.move_circle_with_collisions(
                self.player_pos, config.PLAYER_RADIUS, move * move_speed * dt
            )
        else:
            self.move_circle_with_collisions(
                self.player_pos, config.PLAYER_RADIUS, pygame.Vector2()
            )

        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        pressed = pygame.mouse.get_pressed(num_buttons=3)[0]
        if self.skill_cast_key is None and pressed and self.fire_timer <= 0:
            aim = self.current_fire_direction(mouse_pos)
            if aim.length_squared() > 0:
                self.spawn_burst(aim)
                self.fire_timer = self.fire_cooldown
        elif not pygame.mouse.get_pressed(num_buttons=3)[2]:
            self.auto_aim_target = pygame.Vector2()

    def try_dash(self) -> None:
        if self.dash_timer > 0 or self.player_actions_locked():
            return
        direction = (
            self.last_move
            if self.last_move.length_squared() > 0
            else pygame.Vector2(1, 0)
        )
        self.move_circle_with_collisions(
            self.player_pos,
            config.PLAYER_RADIUS,
            direction.normalize() * self.dash_distance,
        )
        self.iframes = max(self.iframes, 0.3)
        self.dash_timer = self.dash_cooldown
        self.floaters.append(
            FloatingText(self.player_pos.copy(), "冲刺", config.PLAYER_COLOR, 0.35)
        )

    def try_use_active_skill(self) -> None:
        if self.skill_timer > 0 or self.player_actions_locked():
            return
        handler = self.active_skill_handler()
        if handler is not None:
            handler()
            return
        self.message = f"{self.active_skill_name} \u6682\u4e0d\u53ef\u7528"

    def update_skill_input_state(self, dt: float) -> None:
        if not self.q_skill_hold_active:
            return
        if not self.can_begin_q_hold():
            self.reset_q_skill_hold_state()
            return
        self.q_skill_hold_timer += dt

    def current_skill_aim_direction(self) -> pygame.Vector2:
        aim = pygame.Vector2(pygame.mouse.get_pos()) - self.player_pos
        if aim.length_squared() <= 0:
            aim = (
                self.last_move
                if self.last_move.length_squared() > 0
                else pygame.Vector2(1, 0)
            )
        return aim.normalize() if aim.length_squared() > 0 else pygame.Vector2(1, 0)

    def weapon_supports_auto_aim(self) -> bool:
        return self.selected_weapon.key in {"rail", "rocket", "laser_lance"}

    def find_auto_aim_enemy(self, cursor_pos: pygame.Vector2) -> Enemy | None:
        if not self.weapon_supports_auto_aim() or not self.enemies:
            return None
        cursor_dir = cursor_pos - self.player_pos
        best_enemy: Enemy | None = None
        best_score = float("inf")
        for enemy in self.enemies:
            to_enemy = enemy.pos - self.player_pos
            player_distance = to_enemy.length()
            if player_distance <= 0 or player_distance > config.AUTO_AIM_PLAYER_RADIUS:
                continue
            if not self.has_line_of_sight(
                self.player_pos, enemy.pos, max(5, self.player_projectile_radius)
            ):
                continue
            cursor_distance = enemy.pos.distance_to(cursor_pos)
            if cursor_distance > config.AUTO_AIM_CURSOR_RADIUS:
                continue
            angle_penalty = 0.0
            if cursor_dir.length_squared() > 0:
                angle = cursor_dir.angle_to(to_enemy)
                if abs(math.radians(angle)) > config.AUTO_AIM_ANGLE:
                    continue
                angle_penalty = abs(angle) * 0.45
            score = cursor_distance * 0.72 + player_distance * 0.28 + angle_penalty
            if score < best_score:
                best_score = score
                best_enemy = enemy
        return best_enemy

    def current_fire_direction(
        self, cursor_pos: pygame.Vector2 | None = None
    ) -> pygame.Vector2:
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos()) if cursor_pos is None else cursor_pos
        pressed = pygame.mouse.get_pressed(num_buttons=3)
        auto_target = self.find_auto_aim_enemy(mouse_pos) if pressed[2] else None
        if auto_target is not None:
            self.auto_aim_target = auto_target.pos.copy()
            aim = auto_target.pos - self.player_pos
        else:
            self.auto_aim_target = pygame.Vector2()
            aim = mouse_pos - self.player_pos
        if aim.length_squared() <= 0:
            aim = self.last_move if self.last_move.length_squared() > 0 else pygame.Vector2(1, 0)
        return aim.normalize() if aim.length_squared() > 0 else pygame.Vector2(1, 0)

    def clear_enemy_bullets_in_radius(
        self, center: pygame.Vector2, radius: float
    ) -> int:
        cleared = 0
        remaining: list[Bullet] = []
        for bullet in self.bullets:
            if bullet.friendly or bullet.hits_all:
                remaining.append(bullet)
                continue
            if bullet.pos.distance_to(center) > radius + bullet.radius:
                remaining.append(bullet)
                continue
            cleared += 1
            self.spawn_particles(
                bullet.pos.copy(),
                config.BULLET_SHOCK_COLOR,
                4,
                0.34,
                (1.0, 2.4),
                (0.06, 0.16),
            )
        self.bullets = remaining
        return cleared

    def pulse_effect_progress(self) -> float:
        if self.pulse_effect_total <= 0:
            return 0.0
        return max(
            0.0,
            min(
                1.0,
                1.0 - self.pulse_effect_timer / max(0.01, self.pulse_effect_total),
            ),
        )

    def pulse_effect_radius(self) -> float:
        progress = self.pulse_effect_progress()
        eased = 1.0 - (1.0 - progress) ** 2.35
        return config.PULSE_EFFECT_INNER_RADIUS + (
            self.pulse_radius - config.PULSE_EFFECT_INNER_RADIUS
        ) * eased

    def try_pulse(self) -> None:
        if self.skill_timer > 0:
            return
        self.skill_timer = self.active_skill_cooldown()
        self.pulse_effect_total = self.pulse_effect_duration
        self.pulse_effect_timer = self.pulse_effect_total
        cleared = self.clear_enemy_bullets_in_radius(self.player_pos, self.pulse_radius)
        pushed = 0
        for enemy in self.enemies[:]:
            dist = enemy.pos.distance_to(self.player_pos)
            if dist <= self.pulse_radius + enemy.radius:
                knock = enemy.pos - self.player_pos
                if knock.length_squared() <= 0:
                    knock = pygame.Vector2(
                        self.rng.uniform(-1.0, 1.0), self.rng.uniform(-1.0, 1.0)
                    )
                if knock.length_squared() > 0:
                    if self.apply_enemy_knockback(
                        enemy,
                        knock.normalize()
                        * self.pulse_push_force
                        / max(0.35, enemy.knockback_resist),
                    ):
                        pushed += 1
        self.spawn_particles(
            self.player_pos.copy(),
            config.BULLET_SHOCK_COLOR,
            16,
            1.05,
            (1.6, 4.2),
            (0.10, 0.24),
        )
        self.floaters.append(
            FloatingText(
                self.player_pos.copy(),
                " · ".join(
                    part
                    for part in (
                        f"清弹 {cleared}" if cleared else "",
                        f"推开 {pushed}" if pushed else "",
                    )
                    if part
                )
                or "脉冲释放",
                config.BULLET_SHOCK_COLOR,
                0.6,
            )
        )

    def full_screen_effect_radius(self) -> float:
        arena = self.arena_rect()
        return pygame.Vector2(arena.center).distance_to(pygame.Vector2(arena.topleft)) + 24

    def enemy_knockback_taken_multiplier(self, enemy: Enemy) -> float:
        if enemy.kind == "turret":
            return 0.0
        if enemy.is_boss:
            return config.BOSS_KNOCKBACK_TAKEN_MULTIPLIER
        return 1.0

    def apply_enemy_knockback(self, enemy: Enemy, delta: pygame.Vector2) -> bool:
        if delta.length_squared() <= 0:
            return False
        taken_multiplier = self.enemy_knockback_taken_multiplier(enemy)
        if taken_multiplier <= 0:
            return False
        self.move_circle_with_collisions(
            enemy.pos,
            enemy.radius,
            delta * taken_multiplier,
        )
        return True

    def effective_enemy_stun_duration(self, enemy: Enemy, duration: float) -> float:
        if duration <= 0:
            return 0.0
        if enemy.is_boss:
            duration *= config.BOSS_STUN_TAKEN_MULTIPLIER
        return duration

    def apply_enemy_stun(self, enemy: Enemy, duration: float) -> float:
        actual_duration = self.effective_enemy_stun_duration(enemy, duration)
        if actual_duration <= 0:
            return 0.0
        enemy.stun_timer = max(enemy.stun_timer, actual_duration)
        enemy.action_state = ""
        enemy.action_timer = 0.0
        enemy.aim_direction = pygame.Vector2()
        enemy.navigation.last_desired_move = pygame.Vector2()
        enemy.navigation.force_repath = True
        enemy.navigation.repath_timer = 0.0
        return actual_duration

    def try_vanguard_shockwave(self) -> bool:
        if not self.vanguard_shockwave_available():
            return False
        if self.skill_timer > 0 or self.player_actions_locked():
            return False
        if self.vanguard_shockwave_used:
            self.message = "本层全屏震撼已释放"
            return False
        if self.credits < config.VANGUARD_SHOCKWAVE_COST:
            self.message = f"晶片不足 {config.VANGUARD_SHOCKWAVE_COST}"
            return False
        self.credits -= config.VANGUARD_SHOCKWAVE_COST
        self.vanguard_shockwave_used = True
        self.skill_timer = self.active_skill_cooldown()
        radius = self.full_screen_effect_radius()
        cleared = self.clear_enemy_bullets_in_radius(self.player_pos, radius)
        stunned = 0
        for enemy in self.enemies[:]:
            enemy.hp -= config.VANGUARD_SHOCKWAVE_DAMAGE
            self.apply_enemy_stun(enemy, config.VANGUARD_SHOCKWAVE_STUN)
            stunned += 1
            self.floaters.append(
                FloatingText(
                    enemy.pos.copy(),
                    str(int(config.VANGUARD_SHOCKWAVE_DAMAGE)),
                    config.BULLET_SHOCK_COLOR,
                    0.4,
                )
            )
            if enemy.hp <= 0:
                self.kill_enemy(enemy)
        self.pulse_effect_total = max(self.pulse_effect_duration, 0.32)
        self.pulse_effect_timer = self.pulse_effect_total
        self.spawn_explosion_wave(
            self.player_pos.copy(), radius * 0.82, config.BULLET_SHOCK_COLOR, ttl=0.34
        )
        self.spawn_particles(
            self.player_pos.copy(),
            config.BULLET_SHOCK_COLOR,
            30,
            1.28,
            (2.2, 6.0),
            (0.12, 0.32),
        )
        self.add_screen_shake(
            config.VANGUARD_SHOCKWAVE_SHAKE,
            config.VANGUARD_SHOCKWAVE_SHAKE_DURATION,
        )
        self.add_screen_flash(
            config.VANGUARD_SHOCKWAVE_FLASH_DURATION,
            config.BULLET_SHOCK_COLOR,
            config.VANGUARD_SHOCKWAVE_FLASH,
        )
        self.floaters.append(
            FloatingText(
                self.player_pos.copy(),
                f"全屏震撼 · 清弹 {cleared} · 震晕 {stunned}",
                config.BULLET_SHOCK_COLOR,
                0.9,
            )
        )
        return True

    def spawn_basketball_projectile(self, direction: pygame.Vector2) -> None:
        if direction.length_squared() <= 0:
            return
        direction = direction.normalize()
        spawn_pos = self.player_pos.copy() + direction * (
            config.PLAYER_RADIUS + self.basketball_radius + 2
        )
        self.spawn_projectile(
            spawn_pos,
            direction,
            self.basketball_damage * self.player_damage_multiplier(),
            speed=self.basketball_projectile_speed(),
            ttl=config.BASKETBALL_TTL,
            radius=self.basketball_radius,
            pierce=0,
            bounces_left=-1,
            friendly=True,
            color=config.BASKETBALL_COLOR,
            knockback=config.BASKETBALL_KNOCKBACK,
            style="basketball",
            trail_color=config.BASKETBALL_TRAIL_COLOR,
            trail_interval=config.BASKETBALL_TRAIL_INTERVAL,
            expires_on_room_clear=True,
        )

    def try_basketball_skill(self) -> None:
        if self.skill_timer > 0:
            return
        direction = self.current_skill_aim_direction()
        self.skill_timer = self.active_skill_cooldown()
        spawn_pos = self.player_pos.copy() + direction.normalize() * (
            config.PLAYER_RADIUS + self.basketball_radius + 2
        )
        self.spawn_basketball_projectile(direction)
        self.spawn_particles(
            spawn_pos.copy(),
            config.BASKETBALL_COLOR,
            8,
            0.92,
            (1.6, 3.8),
            (0.12, 0.24),
        )
        self.floaters.append(
            FloatingText(self.player_pos.copy(), "\u7bee\u7403\u51fa\u624b", config.BASKETBALL_COLOR, 0.45)
        )

    def try_kunkun_chip_barrage(self) -> bool:
        if (
            self.selected_character.key != "kunkun"
            or self.active_skill_key != "basketball"
        ):
            return False
        if self.skill_timer > 0 or self.player_actions_locked():
            return False
        if self.kunkun_chip_barrage_used:
            self.message = "\u672c\u5c42\u6676\u7247\u9f50\u5c04\u5df2\u53d1\u52a8"
            return False
        if self.credits < config.KUNKUN_BARRAGE_COST:
            self.message = f"\u6676\u7247\u4e0d\u8db3 {config.KUNKUN_BARRAGE_COST}"
            return False
        self.credits -= config.KUNKUN_BARRAGE_COST
        self.kunkun_chip_barrage_used = True
        self.skill_timer = self.active_skill_cooldown()
        directions = (
            pygame.Vector2(1, 0),
            pygame.Vector2(-1, 0),
            pygame.Vector2(0, 1),
            pygame.Vector2(0, -1),
            pygame.Vector2(1, 1),
            pygame.Vector2(1, -1),
            pygame.Vector2(-1, 1),
            pygame.Vector2(-1, -1),
        )
        for direction in directions:
            self.spawn_basketball_projectile(direction)
        self.spawn_particles(
            self.player_pos.copy(),
            config.BASKETBALL_COLOR,
            18,
            1.12,
            (1.8, 4.4),
            (0.12, 0.28),
        )
        self.floaters.append(
            FloatingText(self.player_pos.copy(), "\u6676\u7247\u9f50\u5c04", config.BASKETBALL_COLOR, 0.7)
        )
        return True

    def try_mamba_smash(self) -> None:
        if self.skill_timer > 0 or self.skill_cast_key is not None:
            return
        direction = self.current_skill_aim_direction()
        self.skill_timer = self.active_skill_cooldown()
        self.skill_cast_key = "mamba_smash"
        self.skill_cast_direction = direction.copy()
        self.skill_cast_total = config.MAMBA_SKILL_STARTUP
        self.skill_cast_timer = self.skill_cast_total
        self.mamba_impact_timer = 0.0
        self.fire_timer = max(self.fire_timer, config.MAMBA_SKILL_STARTUP)
        windup_pos = self.player_pos.copy() + direction * (config.PLAYER_RADIUS + 12)
        self.spawn_particles(
            windup_pos,
            config.MAMBA_GLOW_COLOR,
            10,
            0.9,
            (1.4, 3.8),
            (0.10, 0.22),
        )
        self.spawn_particles(
            self.player_pos.copy(),
            config.MAMBA_TRIM_COLOR,
            6,
            0.72,
            (1.0, 2.4),
            (0.08, 0.18),
        )
        self.floaters.append(
            FloatingText(
                self.player_pos.copy() + pygame.Vector2(0, -22),
                "曼巴起势",
                config.MAMBA_JERSEY_COLOR,
                0.24,
            )
        )

    def update_active_skill_effects(self, dt: float) -> None:
        if self.pulse_effect_timer > 0:
            self.pulse_effect_timer = max(0.0, self.pulse_effect_timer - dt)
            self.clear_enemy_bullets_in_radius(
                self.player_pos, self.pulse_effect_radius()
            )
        self.mamba_impact_timer = max(0.0, self.mamba_impact_timer - dt)
        if self.skill_cast_key is None:
            self.skill_cast_timer = 0.0
            return
        self.skill_cast_timer = max(0.0, self.skill_cast_timer - dt)
        if self.skill_cast_timer > 0:
            return
        cast_key = self.skill_cast_key
        self.skill_cast_key = None
        if cast_key == "mamba_smash":
            self.execute_mamba_smash()
        self.skill_cast_direction = pygame.Vector2()
        self.skill_cast_total = 0.0

    def damage_obstacles_in_cone(
        self,
        origin: pygame.Vector2,
        direction: pygame.Vector2,
        range_limit: float,
        half_angle: float,
        damage: float,
        color: tuple[int, int, int],
    ) -> int:
        cone_cos = math.cos(half_angle)
        hits = 0
        for obstacle in self.obstacles[:]:
            if not obstacle.destructible:
                continue
            target = pygame.Vector2(obstacle.rect.center)
            offset = target - origin
            size_bonus = max(obstacle.rect.width, obstacle.rect.height) * 0.45
            distance = offset.length()
            if distance > range_limit + size_bonus:
                continue
            if (
                offset.length_squared() > 0
                and direction.dot(offset.normalize()) < cone_cos
            ):
                continue
            dealt = max(18.0, damage)
            destroyed = self.apply_obstacle_damage(obstacle, dealt)
            hits += 1
            self.spawn_particles(
                target.copy(),
                color,
                5 if destroyed else 3,
                0.78,
                (1.0, 2.8),
                (0.08, 0.18),
            )
        return hits

    def execute_mamba_smash(self) -> None:
        direction = (
            self.skill_cast_direction.normalize()
            if self.skill_cast_direction.length_squared() > 0
            else self.current_skill_aim_direction()
        )
        self.move_circle_with_collisions(
            self.player_pos,
            config.PLAYER_RADIUS,
            direction * config.MAMBA_SKILL_LUNGE_DISTANCE,
        )
        impact_center = self.player_pos.copy() + direction * (config.MAMBA_SKILL_RANGE * 0.62)
        cone_cos = math.cos(self.mamba_skill_half_angle)
        hits = 0
        obstacle_hits = self.damage_obstacles_in_cone(
            self.player_pos,
            direction,
            config.MAMBA_SKILL_RANGE,
            self.mamba_skill_half_angle + 0.10,
            self.mamba_skill_damage * 1.1,
            config.MAMBA_IMPACT_COLOR,
        )
        for enemy in self.enemies[:]:
            offset = enemy.pos - self.player_pos
            distance = offset.length()
            if distance > config.MAMBA_SKILL_RANGE + enemy.radius:
                continue
            if offset.length_squared() > 0 and direction.dot(offset.normalize()) < cone_cos:
                continue
            hits += 1
            enemy.hp -= self.mamba_skill_damage
            if enemy.hp > 0:
                self.apply_player_attack_effects(enemy)
            push_dir = offset if offset.length_squared() > 0 else direction
            if push_dir.length_squared() > 0:
                push_dir = push_dir.normalize() + direction * 0.22
            if push_dir.length_squared() <= 0:
                push_dir = direction.copy()
            push = push_dir.normalize() * (
                config.MAMBA_SKILL_KNOCKBACK / max(0.55, enemy.knockback_resist)
            )
            self.apply_enemy_knockback(enemy, push)
            stun_duration = self.mamba_skill_stun_duration / max(
                1.0, enemy.knockback_resist * 0.92
            )
            actual_stun = self.apply_enemy_stun(enemy, stun_duration)
            enemy.shoot_timer = max(enemy.shoot_timer, min(0.28, actual_stun))
            self.floaters.append(
                FloatingText(
                    enemy.pos.copy(),
                    f"{int(self.mamba_skill_damage)}",
                    config.MAMBA_IMPACT_COLOR,
                    0.48,
                )
            )
            self.spawn_particles(
                enemy.pos.copy(),
                config.MAMBA_IMPACT_COLOR,
                9,
                1.18,
                (1.6, 4.8),
                (0.10, 0.24),
            )
            self.spawn_particles(
                enemy.pos.copy(),
                config.MAMBA_TRIM_COLOR,
                6,
                0.82,
                (1.1, 3.2),
                (0.08, 0.18),
            )
            if enemy.hp <= 0:
                self.kill_enemy(enemy)
        self.mamba_impact_center = impact_center
        self.mamba_impact_direction = direction.copy()
        self.mamba_impact_total = config.MAMBA_SKILL_IMPACT_TTL
        self.mamba_impact_timer = self.mamba_impact_total
        self.spawn_explosion_wave(
            impact_center,
            config.MAMBA_SKILL_IMPACT_RADIUS,
            config.MAMBA_IMPACT_COLOR,
            ttl=0.22,
        )
        self.spawn_explosion_wave(
            self.player_pos.copy() + direction * 74,
            config.MAMBA_SKILL_IMPACT_RADIUS * 0.66,
            config.MAMBA_GLOW_COLOR,
            ttl=0.16,
        )
        self.spawn_particles(
            impact_center.copy(),
            config.MAMBA_IMPACT_COLOR,
            18,
            1.85,
            (2.0, 5.4),
            (0.12, 0.30),
        )
        self.spawn_particles(
            impact_center.copy(),
            config.MAMBA_JERSEY_COLOR,
            12,
            1.36,
            (1.4, 4.0),
            (0.10, 0.24),
        )
        self.play_sound("boom")
        self.add_screen_shake(
            config.MAMBA_SKILL_SHAKE, config.MAMBA_SKILL_SHAKE_DURATION
        )
        total_hits = hits + obstacle_hits
        floater_text = f"曼巴重击 {total_hits}" if total_hits else "重击落空"
        floater_color = config.MAMBA_GLOW_COLOR if total_hits else config.MUTED_TEXT
        self.floaters.append(
            FloatingText(
                self.player_pos.copy() + direction * 34,
                floater_text,
                floater_color,
                0.58,
            )
        )

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
            end, normal = self.trace_beam_segment(
                current_start, beam_dir, radius, remaining_length
            )
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

    def reflect_direction(
        self, direction: pygame.Vector2, normal: pygame.Vector2
    ) -> pygame.Vector2:
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
            candidates.append(
                ((rect.right - origin.x) / direction.x, pygame.Vector2(-1, 0))
            )
        elif direction.x < -epsilon:
            candidates.append(
                ((rect.left - origin.x) / direction.x, pygame.Vector2(1, 0))
            )
        if direction.y > epsilon:
            candidates.append(
                ((rect.bottom - origin.y) / direction.y, pygame.Vector2(0, -1))
            )
        elif direction.y < -epsilon:
            candidates.append(
                ((rect.top - origin.y) / direction.y, pygame.Vector2(0, 1))
            )
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
                    hit_normal = (
                        pygame.Vector2(-1, 0) if t1 < t2 else pygame.Vector2(1, 0)
                    )
                else:
                    hit_normal = (
                        pygame.Vector2(0, -1) if t1 < t2 else pygame.Vector2(0, 1)
                    )
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
        return (
            self.point_to_segment_distance_squared(center, start, end)
            <= radius * radius
        )

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
        base_damage *= self.player_damage_multiplier()
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
        return (
            adjusted.normalize()
            if adjusted.length_squared() > 0
            else pygame.Vector2(1, 0)
        )

    def spawn_projectile(
        self,
        origin: pygame.Vector2,
        direction: pygame.Vector2,
        damage: float,
        *,
        speed: float,
        ttl: float,
        radius: int,
        friendly: bool,
        color: tuple[int, int, int],
        pierce: int = 0,
        bounces_left: int = 0,
        crit: bool = False,
        hits_all: bool = False,
        decay_visual: bool = False,
        knockback: float = config.PROJECTILE_BASE_KNOCKBACK,
        style: str = "bullet",
        explosion_radius: float = 0.0,
        explosion_color: tuple[int, int, int] | None = None,
        explosion_knockback: float = 0.0,
        trail_color: tuple[int, int, int] | None = None,
        trail_interval: float = 0.0,
        expires_on_room_clear: bool = False,
        homing_strength: float = 0.0,
        homing_radius: float = 0.0,
        affect_enemies: bool = True,
    ) -> None:
        if direction.length_squared() <= 0:
            return
        self.bullets.append(
            Bullet(
                pos=origin.copy(),
                velocity=direction.normalize() * speed,
                damage=damage,
                radius=radius,
                knockback=knockback,
                ttl=ttl,
                max_ttl=ttl,
                pierce=pierce,
                bounces_left=bounces_left,
                friendly=friendly,
                color=color,
                crit=crit,
                hits_all=hits_all,
                decay_visual=decay_visual,
                style=style,
                explosion_radius=explosion_radius,
                explosion_color=color if explosion_color is None else explosion_color,
                explosion_knockback=explosion_knockback,
                trail_color=trail_color,
                trail_interval=trail_interval,
                trail_timer=trail_interval,
                expires_on_room_clear=expires_on_room_clear,
                homing_strength=homing_strength,
                homing_radius=homing_radius,
                affect_enemies=affect_enemies,
            )
        )

    def clear_room_bound_projectiles(self) -> None:
        if not self.bullets:
            return
        remaining: list[Bullet] = []
        for bullet in self.bullets:
            if not bullet.expires_on_room_clear:
                remaining.append(bullet)
                continue
            self.spawn_particles(bullet.pos.copy(), bullet.color, 5, 0.44, (1.4, 2.8), (0.08, 0.18))
        self.bullets = remaining

    def bullet_can_bounce(self, bullet: Bullet) -> bool:
        return bullet.friendly and (bullet.style == "basketball" or bullet.bounces_left > 0)

    def update_bullet_trail(self, bullet: Bullet, dt: float) -> None:
        if bullet.trail_color is None or bullet.trail_interval <= 0:
            return
        bullet.trail_timer -= dt
        while bullet.trail_timer <= 0:
            if bullet.style == "rocket":
                self.spawn_particles(bullet.pos.copy(), bullet.trail_color, 2, 0.52, (1.2, 2.8), (0.16, 0.28))
            else:
                self.spawn_particles(bullet.pos.copy(), bullet.trail_color, 1, 0.42, (1.1, 2.2), (0.10, 0.20))
            bullet.trail_timer += bullet.trail_interval

    def bounce_bullet_from_enemy(
        self,
        bullet: Bullet,
        enemy_pos: pygame.Vector2,
        enemy_radius: int,
        normal: pygame.Vector2 | None = None,
    ) -> None:
        bounce_normal = pygame.Vector2() if normal is None else normal.copy()
        if bounce_normal.length_squared() <= 0:
            bounce_normal = bullet.pos - enemy_pos
        if bounce_normal.length_squared() <= 0:
            bounce_normal = -bullet.velocity if bullet.velocity.length_squared() > 0 else pygame.Vector2(1, 0)
        bounce_normal = bounce_normal.normalize()
        reflected = self.reflect_direction(bullet.velocity, bounce_normal)
        if reflected.length_squared() <= 0:
            reflected = bounce_normal
        speed = bullet.velocity.length()
        if speed <= 0:
            speed = self.basketball_projectile_speed()
        bullet.velocity = reflected * speed
        bullet.pos = enemy_pos + bounce_normal * (enemy_radius + bullet.radius + 2)
        self.clamp_circle_to_arena(bullet.pos, bullet.radius)
        self.register_bullet_bounce(bullet)

    def explode_rocket(self, bullet: Bullet, impact_pos: pygame.Vector2 | None = None) -> None:
        center = bullet.pos.copy() if impact_pos is None else impact_pos.copy()
        self.clamp_circle_to_arena(center, max(2, bullet.radius))
        burst_color = config.CRIT_COLOR if bullet.crit else (bullet.explosion_color or config.ROCKET_EXPLOSION_COLOR)
        self.spawn_particles(center.copy(), burst_color, 24, 1.75, (2.4, 6.6), (0.18, 0.54))
        self.spawn_particles(center.copy(), config.ROCKET_SHOCKWAVE_COLOR, 12, 1.15, (1.8, 4.2), (0.14, 0.36))
        self.spawn_particles(center.copy(), config.ROCKET_SMOKE_COLOR, 10, 0.82, (2.6, 5.4), (0.24, 0.58))
        self.spawn_explosion_wave(center, bullet.explosion_radius * 0.62, config.ROCKET_SHOCKWAVE_COLOR, ttl=0.20)
        self.apply_explosion_damage(
            center,
            bullet.explosion_radius,
            bullet.damage,
            burst_color,
            affect_player=False,
            enemy_knockback=bullet.explosion_knockback,
            wave_ttl=0.34,
            player_attack=bullet.friendly,
            affect_enemies=bullet.affect_enemies,
        )
        self.add_screen_shake(config.ROCKET_SCREEN_SHAKE, config.ROCKET_SCREEN_SHAKE_DURATION)

    def extra_multishot_angles(self) -> list[float]:
        if self.selected_weapon.key == "rail":
            angles: list[float] = []
            for idx in range(self.multishot):
                base = 0.10 + idx * 0.05
                angles.extend([-base, base])
            return angles
        angles: list[float] = []
        for idx in range(self.multishot):
            lane = idx // 2
            base = 0.22 + lane * 0.06
            side = 1 if idx % 2 == 0 else -1
            angles.append(side * base)
        return angles

    def current_multishot_lane_count(self) -> int:
        return len(self.extra_multishot_angles())

    def player_projectile_angles(self) -> list[float]:
        if not self.is_shotgun_weapon():
            if self.selected_weapon.key != "rail" and self.multishot > 0:
                total_projectiles = 1 + self.multishot
                spacing = 0.22
                center_index = (total_projectiles - 1) / 2
                return [
                    (idx - center_index) * spacing
                    for idx in range(total_projectiles)
                ]
            return [0.0, *self.extra_multishot_angles()]
        pellets = self.player_shotgun_pellets
        if pellets <= 1:
            base_angles = [0.0]
        else:
            base_angles = []
            for idx in range(pellets):
                sample = -1.0 + 2.0 * idx / max(1, pellets - 1)
                curved = math.copysign(
                    abs(sample) ** config.SHOTGUN_CLUSTER_EXPONENT, sample
                )
                base_angles.append(curved * self.player_shotgun_spread)
        return [*base_angles, *self.extra_multishot_angles()]

    def shotgun_pellet_velocity_profile(self, angle: float) -> tuple[float, float]:
        spread_ratio = min(
            1.0, abs(angle) / max(0.001, self.player_shotgun_spread or 0.001)
        )
        center_bonus = (1.0 - spread_ratio) * config.SHOTGUN_PELLET_CENTER_SPEED_BONUS
        speed_scale = 1.0 + center_bonus + self.rng.uniform(
            -config.SHOTGUN_PELLET_SPEED_VARIANCE,
            config.SHOTGUN_PELLET_SPEED_VARIANCE,
        )
        ttl_scale = 1.0 + self.rng.uniform(
            -config.SHOTGUN_PELLET_TTL_VARIANCE,
            config.SHOTGUN_PELLET_TTL_VARIANCE,
        )
        ttl_scale += center_bonus * 0.25
        return max(0.72, speed_scale), max(0.78, ttl_scale)

    def spawn_bullet_barrel_burst(
        self, origin: pygame.Vector2, rect: pygame.Rect
    ) -> None:
        size = max(rect.width, rect.height)
        bullet_count = 8 if size <= 24 else 12 if size <= 34 else 16
        bullet_damage = (
            8.0 + size * 0.18 + self.floor_index * 0.55
        ) * config.BULLET_BARREL_DAMAGE_MULTIPLIER
        bullet_speed = config.BULLET_SPEED * (0.58 + min(0.22, size / 180))
        bullet_ttl = 1.2 + min(0.55, size / 110)
        for idx in range(bullet_count):
            angle = (math.tau / bullet_count) * idx + self.rng.uniform(-0.06, 0.06)
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            self.spawn_projectile(
                origin,
                direction,
                bullet_damage,
                speed=bullet_speed,
                ttl=bullet_ttl,
                radius=config.BULLET_RADIUS + 1,
                friendly=False,
                color=config.BULLET_BARREL_COLOR,
                hits_all=True,
            )
        self.spawn_particles(
            origin.copy(),
            config.BULLET_BARREL_COLOR,
            18,
            1.25,
            (1.5, 4.2),
            (0.14, 0.34),
        )
        self.floaters.append(
            FloatingText(
                origin.copy(),
                f"弹幕炸裂 x{bullet_count}",
                config.BULLET_BARREL_COLOR,
                0.55,
            )
        )

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
        points, impact_points = self.trace_beam(
            origin, direction, radius, bounces_left=bounces_left
        )
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
        self.spawn_particles(
            origin.copy(), color, 6 if friendly else 4, 0.82, (1.4, 3.2), (0.08, 0.18)
        )
        for impact in impact_points:
            self.spawn_particles(
                impact.copy(),
                config.LASER_TRACE_CORE,
                7,
                1.18,
                (1.6, 3.8),
                (0.12, 0.24),
            )

        if friendly:
            beam_hits = 0
            push_dir = direction.normalize()
            damaged_obstacles: set[int] = set()
            damaged_enemies: set[int] = set()
            for start, end in zip(points, points[1:]):
                for obstacle in self.obstacles[:]:
                    if not obstacle.destructible or id(obstacle) in damaged_obstacles:
                        continue
                    if not self.segment_hits_rect(
                        start, end, obstacle.rect, max(5, int(width * 0.5))
                    ):
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
                    if enemy.hp > 0:
                        self.apply_player_attack_effects(enemy)
                    self.apply_enemy_knockback(
                        enemy,
                        push_dir * 16 / enemy.knockback_resist,
                    )
                    floater_color = config.CRIT_COLOR if crit else color
                    floater_text = (
                        f"暴击 {int(hit_damage)}" if crit else str(int(hit_damage))
                    )
                    self.floaters.append(
                        FloatingText(
                            enemy.pos.copy(), floater_text, floater_color, 0.42
                        )
                    )
                    if enemy.hp <= 0:
                        self.kill_enemy(enemy)
            if beam_hits:
                self.floaters.append(
                    FloatingText(
                        origin.copy() + pygame.Vector2(0, -22),
                        f"激光命中 {beam_hits}",
                        color,
                        0.35,
                    )
                )
        else:
            hit_radius = config.PLAYER_RADIUS + width * 0.25
            for start, end in zip(points, points[1:]):
                if (
                    self.segment_hits_circle(start, end, self.player_pos, hit_radius)
                    and self.iframes <= 0
                ):
                    self.damage_player(damage, color, 0.38)
                    break

    def spawn_burst(self, direction: pygame.Vector2) -> None:
        if self.selected_weapon.key == "laser_lance":
            self.play_sound("prism_lance_fire")
        elif self.selected_weapon.key == "laser_burst":
            self.play_sound("pulse_laser_fire")
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
                self.move_circle_with_collisions(
                    self.player_pos, config.PLAYER_RADIUS, recoil
                )
                self.spawn_particles(
                    self.player_pos.copy(),
                    self.player_beam_color,
                    5,
                    0.74,
                    (1.5, 3.2),
                    (0.08, 0.18),
                )
            return
        if self.is_rocket_weapon():
            fired = self.apply_projectile_offset(direction)
            muzzle = self.player_pos.copy() + fired * 18
            damage, crit = self.roll_player_hit(self.player_damage)
            self.spawn_projectile(
                muzzle,
                fired,
                damage,
                speed=self.player_projectile_speed,
                ttl=self.player_projectile_ttl,
                radius=self.player_projectile_radius,
                pierce=0,
                bounces_left=0,
                friendly=True,
                color=config.ROCKET_COLOR,
                crit=crit,
                knockback=0.0,
                style="rocket",
                explosion_radius=self.player_rocket_explosion_radius,
                explosion_color=config.ROCKET_EXPLOSION_COLOR,
                explosion_knockback=self.player_rocket_explosion_knockback,
                trail_color=config.ROCKET_SMOKE_COLOR,
                trail_interval=config.ROCKET_TRAIL_INTERVAL,
            )
            self.spawn_particles(muzzle.copy(), config.ROCKET_EXPLOSION_COLOR, 9, 1.35, (2.2, 5.0), (0.12, 0.30))
            self.spawn_particles(muzzle.copy() - fired * 6, config.ROCKET_SMOKE_COLOR, 6, 0.72, (1.8, 4.0), (0.18, 0.34))
            recoil = fired * -10
            self.move_circle_with_collisions(self.player_pos, config.PLAYER_RADIUS, recoil)
            self.shot_serial += 1
            return
        shotgun_weapon = self.is_shotgun_weapon()
        projectile_color = (
            config.SHOTGUN_PELLET_COLOR if shotgun_weapon else config.BULLET_COLOR
        )
        if shotgun_weapon:
            muzzle = self.player_pos.copy() + direction * 18
            self.spawn_particles(
                muzzle.copy(),
                config.SHOTGUN_PELLET_COLOR,
                8,
                0.92,
                (1.4, 3.6),
                (0.06, 0.18),
            )
            self.spawn_particles(
                muzzle.copy() - direction * 4,
                config.SHOTGUN_COLOR,
                5,
                0.76,
                (1.0, 2.8),
                (0.08, 0.18),
            )
            self.add_screen_shake(1.3, 0.05)
        for angle in self.player_projectile_angles():
            fired = self.apply_projectile_offset(direction.rotate_rad(angle))
            lateral = pygame.Vector2(-fired.y, fired.x)
            spawn_offset = lateral * self.rng.uniform(
                -self.player_spread * 180, self.player_spread * 180
            )
            damage, crit = self.roll_player_hit(self.player_damage)
            projectile_speed = self.player_projectile_speed
            projectile_ttl = self.player_projectile_ttl
            projectile_style = "bullet"
            trail_color = None
            trail_interval = 0.0
            decay_visual = False
            if self.selected_weapon.key == "rail":
                projectile_style = "rail"
            if shotgun_weapon:
                speed_scale, ttl_scale = self.shotgun_pellet_velocity_profile(angle)
                projectile_speed *= speed_scale
                projectile_ttl *= ttl_scale
                projectile_style = "shotgun_pellet"
                trail_color = config.SHOTGUN_TRAIL_COLOR
                trail_interval = config.SHOTGUN_TRAIL_INTERVAL
                decay_visual = True
            self.spawn_projectile(
                self.player_pos.copy() + spawn_offset,
                fired,
                damage,
                speed=projectile_speed,
                ttl=projectile_ttl,
                radius=self.player_projectile_radius,
                pierce=self.bullet_pierce,
                bounces_left=self.player_bullet_bounces,
                friendly=True,
                color=projectile_color,
                crit=crit,
                knockback=self.player_projectile_knockback,
                style=projectile_style,
                decay_visual=decay_visual,
                trail_color=trail_color,
                trail_interval=trail_interval,
            )
        self.shot_serial += 1

    def register_bullet_bounce(self, bullet: Bullet) -> None:
        if bullet.style == "basketball":
            base_speed = self.basketball_projectile_speed()
            current_speed = bullet.velocity.length()
            target_speed = base_speed if current_speed <= 0 else min(base_speed, current_speed) * config.BASKETBALL_BOUNCE_PUSH
            if bullet.velocity.length_squared() > 0:
                bullet.velocity.scale_to_length(max(base_speed * 0.82, target_speed))
            self.spawn_particles(bullet.pos.copy(), bullet.color, 5, 0.62, (1.3, 2.6), (0.08, 0.18))
            return
        bullet.bounces_left -= 1
        bullet.damage *= 0.92
        self.spawn_particles(
            bullet.pos.copy(), bullet.color, 4, 0.55, (1.2, 2.2), (0.08, 0.16)
        )

    def try_bounce_from_arena(self, bullet: Bullet, arena: pygame.Rect) -> bool:
        if not self.bullet_can_bounce(bullet):
            return False
        bounced = False
        if (
            bullet.pos.x - bullet.radius <= arena.left
            or bullet.pos.x + bullet.radius >= arena.right
        ):
            bullet.velocity.x *= -1
            bullet.pos.x = max(
                arena.left + bullet.radius + 1,
                min(arena.right - bullet.radius - 1, bullet.pos.x),
            )
            bounced = True
        if (
            bullet.pos.y - bullet.radius <= arena.top
            or bullet.pos.y + bullet.radius >= arena.bottom
        ):
            bullet.velocity.y *= -1
            bullet.pos.y = max(
                arena.top + bullet.radius + 1,
                min(arena.bottom - bullet.radius - 1, bullet.pos.y),
            )
            bounced = True
        if bounced:
            self.register_bullet_bounce(bullet)
        return bounced

    def try_bounce_from_obstacle(self, bullet: Bullet, obstacle: RoomObstacle, previous_pos: pygame.Vector2) -> bool:
        if not self.bullet_can_bounce(bullet):
            return False
        rect = obstacle.rect
        horizontal_hit = (
            previous_pos.x + bullet.radius <= rect.left
            or previous_pos.x - bullet.radius >= rect.right
        )
        vertical_hit = (
            previous_pos.y + bullet.radius <= rect.top
            or previous_pos.y - bullet.radius >= rect.bottom
        )

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
            bullet.pos.x = (
                rect.left - bullet.radius - 1
                if previous_pos.x < rect.left
                else rect.right + bullet.radius + 1
            )
        if vertical_hit:
            bullet.velocity.y *= -1
            bullet.pos.y = (
                rect.top - bullet.radius - 1
                if previous_pos.y < rect.top
                else rect.bottom + bullet.radius + 1
            )
        self.register_bullet_bounce(bullet)
        return True

    def projectile_hits_obstacle(
        self, bullet: Bullet, obstacle: RoomObstacle, previous_pos: pygame.Vector2
    ) -> bool:
        return self.circle_intersects_rect(
            bullet.pos, bullet.radius, obstacle.rect
        ) or self.segment_hits_rect(
            previous_pos,
            bullet.pos,
            obstacle.rect,
            bullet.radius,
        )

    def update_homing_projectile(self, bullet: Bullet, dt: float) -> None:
        if (
            bullet.homing_strength <= 0
            or bullet.homing_radius <= 0
            or bullet.friendly
            or bullet.velocity.length_squared() <= 0
        ):
            return
        to_player = self.player_pos - bullet.pos
        if to_player.length_squared() <= 0 or to_player.length() > bullet.homing_radius:
            return
        speed = bullet.velocity.length()
        blend = min(1.0, bullet.homing_strength * dt)
        bullet.velocity = bullet.velocity.lerp(to_player.normalize() * speed, blend)

    def update_bullets(self, dt: float) -> None:
        arena = self.arena_rect()
        remaining: list[Bullet] = []
        for bullet in self.bullets:
            previous_pos = bullet.pos.copy()
            self.update_homing_projectile(bullet, dt)
            bullet.pos += bullet.velocity * dt
            bullet.ttl -= dt
            self.update_bullet_trail(bullet, dt)
            if bullet.ttl <= 0:
                if bullet.style == "rocket":
                    self.explode_rocket(bullet)
                continue
            if self.try_bounce_from_arena(bullet, arena):
                remaining.append(bullet)
                continue
            if not arena.collidepoint(bullet.pos.x, bullet.pos.y):
                if bullet.style == "rocket":
                    impact = bullet.pos.copy()
                    self.clamp_circle_to_arena(impact, bullet.radius)
                    self.explode_rocket(bullet, impact)
                continue
            hit = False
            for obstacle in self.obstacles[:]:
                if not self.projectile_hits_obstacle(bullet, obstacle, previous_pos):
                    continue
                if bullet.style == "rocket":
                    self.explode_rocket(bullet, bullet.pos)
                    hit = True
                    break
                hit = True
                if bullet.style == "basketball":
                    if (bullet.friendly or bullet.hits_all) and obstacle.destructible:
                        self.apply_obstacle_damage(obstacle, bullet.damage * 0.9)
                    if self.try_bounce_from_obstacle(bullet, obstacle, previous_pos):
                        hit = False
                elif (bullet.friendly or bullet.hits_all) and obstacle.destructible:
                    destroyed = self.apply_obstacle_damage(obstacle, bullet.damage * 0.9)
                    if not destroyed and bullet.pierce > 0:
                        bullet.pierce -= 1
                        hit = False
                    elif not destroyed and self.try_bounce_from_obstacle(
                        bullet, obstacle, previous_pos
                    ):
                        hit = False
                elif self.try_bounce_from_obstacle(bullet, obstacle, previous_pos):
                    hit = False
                break
            if hit:
                continue
            if bullet.friendly or bullet.hits_all:
                for enemy in self.enemies[:]:
                    if bullet.pos.distance_to(enemy.pos) > bullet.radius + enemy.radius:
                        continue
                    if bullet.style == "rocket":
                        self.explode_rocket(bullet, enemy.pos)
                        hit = True
                        break
                    impact_pos = enemy.pos.copy()
                    impact_radius = enemy.radius
                    impact_normal = bullet.pos - impact_pos
                    enemy.hp -= bullet.damage
                    if enemy.hp > 0:
                        self.apply_player_attack_effects(enemy)
                    if bullet.velocity.length_squared() > 0 and bullet.knockback > 0:
                        push = bullet.velocity.normalize() * bullet.knockback / enemy.knockback_resist
                        self.apply_enemy_knockback(enemy, push)
                    color = config.CRIT_COLOR if bullet.crit else (255, 220, 180)
                    text = f"\u66b4\u51fb {int(bullet.damage)}" if bullet.crit else str(int(bullet.damage))
                    self.floaters.append(FloatingText(enemy.pos.copy(), text, color, 0.45))
                    if bullet.style == "basketball":
                        self.bounce_bullet_from_enemy(bullet, impact_pos, impact_radius, impact_normal)
                    if enemy.hp <= 0:
                        self.kill_enemy(enemy)
                    if bullet.style == "basketball":
                        hit = False
                    elif bullet.pierce > 0:
                        bullet.pierce -= 1
                    else:
                        hit = True
                    break
            if not hit and (not bullet.friendly or bullet.hits_all):
                if (
                    bullet.pos.distance_to(self.player_pos)
                    <= bullet.radius + config.PLAYER_RADIUS
                    and self.iframes <= 0
                ):
                    self.damage_player(bullet.damage, (255, 130, 180), 0.35)
                    hit = True
            if not hit:
                remaining.append(bullet)
        self.bullets = remaining

    def enemy_hazard_rect(self, enemy: Enemy) -> pygame.Rect:
        size = max(34, enemy.radius * 3)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (round(enemy.pos.x), round(enemy.pos.y))
        return rect

    def handle_special_enemy_death(self, enemy: Enemy) -> None:
        if enemy.kind == "toxic_bloater":
            profile = hazard_profile("toxic", self.enemy_hazard_rect(enemy))
            self.gas_clouds.append(
                self.make_gas_cloud(
                    enemy.pos.copy(),
                    profile.radius,
                    profile.ttl,
                    profile.damage,
                    growth_time=0.60,
                    activation_delay=0.38,
                )
            )
            self.spawn_particles(
                enemy.pos.copy(),
                config.TOXIC_ENEMY_COLOR,
                int(12 + profile.radius / 22),
                0.92,
                (2.4, 5.0),
                (0.35, 0.8),
            )
            self.floaters.append(
                FloatingText(
                    enemy.pos.copy(), "毒雾扩散", config.TOXIC_ENEMY_COLOR, 0.65
                )
            )
        elif enemy.kind == "reactor_bomber":
            profile = hazard_profile("reactor", self.enemy_hazard_rect(enemy))
            blast_radius = profile.radius * 0.78
            blast_damage = profile.damage * 0.92
            self.spawn_particles(
                enemy.pos.copy(),
                config.REACTOR_ENEMY_COLOR,
                int(16 + blast_radius / 20),
                1.2,
                (2.4, 5.8),
                (0.16, 0.42),
            )
            self.floaters.append(
                FloatingText(
                    enemy.pos.copy(), "反应爆破", config.REACTOR_ENEMY_COLOR, 0.65
                )
            )
            self.apply_explosion_damage(
                enemy.pos.copy(), blast_radius, blast_damage, config.REACTOR_ENEMY_COLOR
            )

    def kill_enemy(self, enemy: Enemy) -> None:
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        self.handle_special_enemy_death(enemy)
        self.pickups.append(
            Pickup(
                enemy.pos.copy(),
                enemy.xp_reward,
                config.XP_PICKUP_RADIUS,
                "xp",
                config.XP_COLOR,
                "经验",
            )
        )
        credit_amount = enemy_credit_drop(self.room_index, self.floor_index, enemy.kind)
        self.pickups.append(
            Pickup(
                enemy.pos.copy() + pygame.Vector2(0, 12),
                credit_amount,
                config.ITEM_PICKUP_RADIUS,
                "credit",
                config.CREDIT_COLOR,
                "晶片",
            )
        )
        extra_roll = self.rng.random()
        if extra_roll < 0.10:
            self.pickups.append(
                Pickup(
                    enemy.pos.copy() + pygame.Vector2(12, -8),
                    18,
                    config.HEAL_PICKUP_RADIUS,
                    "heal",
                    config.HEAL_COLOR,
                    "血包",
                )
            )
        elif extra_roll < 0.18:
            self.pickups.append(
                Pickup(
                    enemy.pos.copy() + pygame.Vector2(12, -8),
                    24,
                    config.ITEM_PICKUP_RADIUS,
                    "shield",
                    config.SHIELD_COLOR,
                    "护盾",
                )
            )
        elif extra_roll < 0.26:
            self.pickups.append(
                Pickup(
                    enemy.pos.copy() + pygame.Vector2(-12, 8),
                    1,
                    config.ITEM_PICKUP_RADIUS,
                    "item",
                    config.ITEM_COLOR,
                    "道具",
                )
            )
        self.floaters.append(
            FloatingText(
                enemy.pos.copy(), f"+{enemy.xp_reward} 经验", config.XP_COLOR, 0.7
            )
        )
        self.spawn_particles(
            enemy.pos.copy(),
            enemy.color,
            12 if enemy.kind != "boss" else 22,
            1.35,
            (2.0, 5.8),
            (0.22, 0.6),
        )
        self.spawn_particles(
            enemy.pos.copy(),
            (255, 244, 220),
            5 if enemy.kind != "boss" else 10,
            0.9,
            (1.4, 3.2),
            (0.16, 0.36),
        )
        if enemy.kind in ("elite", "boss"):
            self.spawn_particles(
                enemy.pos.copy(), config.CREDIT_COLOR, 8, 1.08, (2.0, 4.8), (0.22, 0.5)
            )
        self.kills += 1

    def get_enemy_projectile_damage(self, enemy: Enemy) -> float:
        if enemy.kind == "shooter":
            return max(7.0, enemy.damage * 0.72)
        if enemy.kind == "turret":
            if enemy.variant == "elite_turret":
                return max(16.0, enemy.damage * 1.08)
            return max(10.0, enemy.damage * 0.84)
        if enemy.kind == "shotgunner":
            return max(5.0, enemy.damage * 0.48)
        if enemy.kind == "elite":
            return max(13.0, enemy.damage * 1.10)
        if enemy.kind == "boss":
            return max(14.0, enemy.damage * 1.02)
        return max(10.0, enemy.damage * 0.86)

    def enemy_uses_laser_attack(self, enemy: Enemy) -> bool:
        return enemy.kind == "laser" or (
            enemy.kind == "boss" and enemy.variant == "challenge"
        )

    def challenge_boss_laser_lock_active(self, enemy: Enemy) -> bool:
        if enemy.kind != "boss" or enemy.variant != "challenge":
            return False
        _, lock_window = self.get_enemy_laser_timing(enemy)
        return (
            enemy.aim_direction.length_squared() > 0
            and enemy.shoot_timer <= lock_window
        )

    def should_advance_enemy_shoot_timer(self, enemy: Enemy) -> bool:
        if enemy.shoot_cooldown <= 0:
            return False
        if enemy.kind == "boss" and enemy.variant == "challenge":
            return not enemy.action_state and enemy.stun_timer <= 0
        return True

    def get_enemy_laser_timing(self, enemy: Enemy) -> tuple[float, float]:
        telegraph_window = 0.95 if enemy.is_boss else 0.78
        lock_window = 0.34 if enemy.is_boss else 0.24
        if enemy.variant == "challenge":
            telegraph_window = 0.88
            lock_window = 0.30
        return telegraph_window, lock_window

    def get_enemy_laser_damage(self, enemy: Enemy) -> float:
        if enemy.variant == "challenge":
            return max(22.0, enemy.damage * 1.14)
        if enemy.is_boss:
            return max(18.0, enemy.damage * 1.05)
        return max(12.0, enemy.damage * 0.92)

    def get_enemy_laser_width(self, enemy: Enemy) -> int:
        if enemy.variant == "challenge":
            return 18
        return 16 if enemy.is_boss else 12

    def boss_name(self, enemy: Enemy) -> str:
        return "歼灭主宰" if enemy.variant == "challenge" else "钢铁领主"

    def charger_dash_available(self) -> bool:
        return self.floor_index >= config.CHARGER_TRUE_DASH_FLOOR

    def current_boss_stomp_radius(self, enemy: Enemy) -> float:
        radius = float(config.BOSS_STOMP_RADIUS)
        if enemy.phase >= 2:
            radius *= config.BOSS_PHASE_TWO_STOMP_RADIUS_MULT
        return radius

    def current_challenge_boss_dash_distance(self, enemy: Enemy) -> float:
        distance = config.CHALLENGE_BOSS_DASH_SPEED * config.CHALLENGE_BOSS_DASH_DURATION
        if enemy.phase >= 2:
            distance *= config.CHALLENGE_BOSS_PHASE_TWO_DASH_RANGE_MULT
        return distance

    def activate_boss_phase_two(self, enemy: Enemy) -> None:
        if enemy.kind != "boss" or enemy.phase >= 2:
            return
        if enemy.hp > enemy.max_hp * config.BOSS_PHASE_TWO_RATIO:
            return
        enemy.phase = 2
        if enemy.variant == "challenge":
            enemy.speed *= config.CHALLENGE_BOSS_PHASE_TWO_SPEED_MULT
            enemy.summon_timer = min(enemy.summon_timer, 0.8)
        else:
            enemy.speed *= config.BOSS_PHASE_TWO_SPEED_MULT
        enemy.action_state = ""
        enemy.action_timer = 0.0
        enemy.aim_direction = pygame.Vector2()
        self.prepare_boss_navigation_recovery(enemy, aggressive=True)
        self.floaters.append(
            FloatingText(
                enemy.pos.copy() + pygame.Vector2(0, -56),
                "二阶段",
                config.BOSS_BAR_PHASE,
                0.95,
            )
        )

    def start_charger_dash(self, enemy: Enemy, direction: pygame.Vector2) -> bool:
        if (
            enemy.kind != "charger"
            or not self.charger_dash_available()
            or enemy.special_timer > 0
            or direction.length_squared() <= 0
        ):
            return False
        enemy.action_state = "charge_dash"
        enemy.action_timer = config.CHARGER_DASH_DURATION
        enemy.special_timer = config.CHARGER_DASH_COOLDOWN
        enemy.aim_direction = direction.normalize()
        enemy.navigation.force_repath = True
        enemy.navigation.repath_timer = 0.0
        return True

    def advance_charger_dash(self, enemy: Enemy, dt: float) -> bool:
        if enemy.kind != "charger" or enemy.action_state != "charge_dash":
            return False
        enemy.action_timer = max(0.0, enemy.action_timer - dt)
        direction = enemy.aim_direction
        if direction.length_squared() <= 0:
            direction = self.player_pos - enemy.pos
        if direction.length_squared() > 0:
            desired_delta = direction.normalize() * config.CHARGER_DASH_SPEED * dt
            actual_move = self.move_circle_with_collisions(
                enemy.pos, enemy.radius, desired_delta
            )
            if (
                desired_delta.length_squared() > 0
                and actual_move.length_squared()
                <= desired_delta.length_squared() * config.ENEMY_BLOCKED_MOVE_RATIO
            ):
                enemy.action_timer = 0.0
        if enemy.pos.distance_to(self.player_pos) <= enemy.radius + config.PLAYER_RADIUS + 4:
            if self.iframes <= 0:
                self.damage_player(enemy.damage * 1.05, (255, 130, 130), 0.4)
            enemy.action_timer = 0.0
        if enemy.action_timer > 0:
            return True
        enemy.action_state = ""
        enemy.aim_direction = pygame.Vector2()
        enemy.navigation.pending_unstuck = True
        enemy.navigation.force_repath = True
        enemy.navigation.repath_timer = 0.0
        return True

    def start_enemy_action(
        self, enemy: Enemy, action_state: str, duration: float
    ) -> None:
        enemy.action_state = action_state
        enemy.action_timer = duration
        delta = self.player_pos - enemy.pos
        if delta.length_squared() > 0:
            enemy.aim_direction = delta.normalize()

    def prepare_boss_navigation_recovery(
        self,
        enemy: Enemy,
        *,
        aggressive: bool = False,
    ) -> None:
        nav = enemy.navigation
        nav.force_repath = True
        nav.repath_timer = 0.0
        nav.commit_timer = 0.0
        nav.blocked_timer = 0.0
        nav.sample_origin = enemy.pos.copy()
        nav.sample_timer = config.ENEMY_STUCK_SAMPLE_WINDOW
        if aggressive:
            nav.pending_unstuck = True
            nav.obstacle_mode_timer = max(
                nav.obstacle_mode_timer, config.ENEMY_OBSTACLE_MODE_TIME
            )
            nav.unstuck_side *= -1

    def start_challenge_boss_dash(
        self, enemy: Enemy, direction: pygame.Vector2
    ) -> None:
        enemy.action_state = "dash_charge"
        enemy.action_timer = config.CHALLENGE_BOSS_DASH_WINDUP
        enemy.alt_special_timer = config.CHALLENGE_BOSS_DASH_COOLDOWN
        if direction.length_squared() > 0:
            enemy.aim_direction = direction.normalize()
        enemy.shoot_timer = max(
            enemy.shoot_timer,
            config.CHALLENGE_BOSS_DASH_WINDUP + config.CHALLENGE_BOSS_DASH_DURATION,
        )
        self.floaters.append(
            FloatingText(
                enemy.pos.copy() + pygame.Vector2(0, -42),
                "冲刺",
                config.CHALLENGE_ROOM_COLOR,
                0.6,
            )
        )

    def finish_challenge_boss_dash(self, enemy: Enemy) -> None:
        self.execute_boss_stomp(enemy)
        enemy.action_state = ""
        enemy.action_timer = 0.0
        enemy.aim_direction = pygame.Vector2()
        self.prepare_boss_navigation_recovery(enemy, aggressive=True)

    def advance_challenge_boss_dash(self, enemy: Enemy, dt: float) -> bool:
        enemy.action_timer = max(0.0, enemy.action_timer - dt)
        direction = enemy.aim_direction
        if direction.length_squared() <= 0:
            direction = self.player_pos - enemy.pos
        if direction.length_squared() > 0:
            desired_delta = (
                direction.normalize()
                * (
                    self.current_challenge_boss_dash_distance(enemy)
                    / max(0.01, config.CHALLENGE_BOSS_DASH_DURATION)
                )
                * dt
            )
            actual_move = self.move_circle_with_collisions(
                enemy.pos,
                enemy.radius,
                desired_delta,
            )
            if (
                desired_delta.length_squared() > 0
                and actual_move.length_squared()
                <= desired_delta.length_squared() * config.ENEMY_BLOCKED_MOVE_RATIO
            ):
                self.finish_challenge_boss_dash(enemy)
                return True
        if enemy.pos.distance_to(self.player_pos) <= enemy.radius + config.PLAYER_RADIUS + 4:
            if self.iframes <= 0:
                self.damage_player(
                    max(
                        24.0,
                        enemy.damage * config.CHALLENGE_BOSS_DASH_DAMAGE_MULT,
                    ),
                    config.CHALLENGE_ROOM_COLOR,
                    0.55,
                )
                self.try_apply_player_stun(config.CHALLENGE_BOSS_DASH_STUN)
                if direction.length_squared() > 0:
                    self.move_circle_with_collisions(
                        self.player_pos,
                        config.PLAYER_RADIUS,
                        direction.normalize() * config.CHALLENGE_BOSS_DASH_PUSH,
                    )
            self.finish_challenge_boss_dash(enemy)
            return True
        if enemy.action_timer <= 0:
            self.finish_challenge_boss_dash(enemy)
            return True
        return True

    def update_boss_action(self, enemy: Enemy, dt: float) -> bool:
        if enemy.kind != "boss" or not enemy.action_state:
            return False
        if enemy.variant == "challenge" and enemy.action_state == "dash":
            return self.advance_challenge_boss_dash(enemy, dt)
        enemy.action_timer = max(0.0, enemy.action_timer - dt)
        if enemy.action_timer > 0:
            return True
        if enemy.variant == "challenge" and enemy.action_state == "dash_charge":
            enemy.action_state = "dash"
            enemy.action_timer = config.CHALLENGE_BOSS_DASH_DURATION
            self.prepare_boss_navigation_recovery(enemy)
            return True
        if enemy.action_state == "stomp":
            self.execute_boss_stomp(enemy)
        elif enemy.action_state == "nova":
            self.execute_boss_nova(enemy)
        elif enemy.action_state == "summon":
            self.execute_challenge_boss_summon(enemy)
        enemy.action_state = ""
        enemy.action_timer = 0.0
        enemy.aim_direction = pygame.Vector2()
        self.prepare_boss_navigation_recovery(enemy)
        return True

    def execute_boss_stomp(self, enemy: Enemy) -> None:
        radius = self.current_boss_stomp_radius(enemy)
        damage = max(22.0, enemy.damage * config.BOSS_STOMP_DAMAGE_MULTIPLIER)
        stomp_color = self.boss_stomp_effect_color(enemy)
        self.spawn_explosion_wave(enemy.pos, radius, stomp_color, ttl=0.52)
        self.spawn_particles(
            enemy.pos.copy(),
            stomp_color,
            24,
            1.8,
            (2.4, 6.4),
            (0.18, 0.42),
        )
        self.floaters.append(
            FloatingText(
                enemy.pos.copy() + pygame.Vector2(0, -38),
                "撼地",
                stomp_color,
                0.7,
            )
        )
        if (
            self.player_pos.distance_to(enemy.pos) <= radius + config.PLAYER_RADIUS
            and self.iframes <= 0
        ):
            self.damage_player(damage, stomp_color, 0.48)
            knock = self.player_pos - enemy.pos
            if knock.length_squared() > 0:
                self.move_circle_with_collisions(
                    self.player_pos,
                    config.PLAYER_RADIUS,
                    knock.normalize() * config.BOSS_STOMP_PUSH,
                )

    def execute_boss_nova(self, enemy: Enemy) -> None:
        bullet_damage = max(11.0, enemy.damage * config.BOSS_NOVA_DAMAGE_MULTIPLIER)
        bullet_speed = config.BULLET_SPEED * 0.48 * self.enemy_bullet_speed_multiplier
        bullet_color = (
            config.CHALLENGE_ROOM_COLOR
            if enemy.variant == "challenge"
            else config.BULLET_ELITE_COLOR
        )
        for idx in range(config.BOSS_NOVA_BULLETS):
            angle = math.tau * idx / config.BOSS_NOVA_BULLETS + self.rng.uniform(
                -0.04, 0.04
            )
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            self.bullets.append(
                Bullet(
                    pos=enemy.pos.copy(),
                    velocity=direction * bullet_speed,
                    damage=bullet_damage,
                    radius=config.BULLET_RADIUS + 1,
                    knockback=config.PROJECTILE_BASE_KNOCKBACK,
                    ttl=2.25,
                    pierce=0,
                    friendly=False,
                    color=bullet_color,
                )
            )
        if enemy.aim_direction.length_squared() > 0:
            self.enemy_shoot(
                enemy,
                enemy.aim_direction,
                bullet_damage * 0.92,
                bullet_color,
                spread=0.12,
            )
        self.spawn_particles(
            enemy.pos.copy(),
            bullet_color,
            18,
            1.35,
            (1.8, 4.8),
            (0.16, 0.34),
        )
        self.floaters.append(
            FloatingText(
                enemy.pos.copy() + pygame.Vector2(0, -38),
                "震荡齐射",
                bullet_color,
                0.7,
            )
        )



    def execute_challenge_boss_summon(self, enemy: Enemy) -> None:
        if self.current_room_state is None:
            return
        active_minions = sum(
            1
            for candidate in self.enemies
            if candidate is not enemy and not candidate.is_boss
        )
        summon_count = min(
            config.CHALLENGE_BOSS_SUMMON_COUNT,
            max(0, config.CHALLENGE_BOSS_SUMMON_CAP - active_minions),
        )
        if summon_count <= 0:
            enemy.summon_timer = config.CHALLENGE_BOSS_SUMMON_COOLDOWN * 0.5
            return
        arena = self.arena_rect()
        for idx in range(summon_count):
            summon = self.make_enemy(
                arena,
                min_distance=max(80.0, enemy.radius * 1.5),
            )
            offset = pygame.Vector2(1, 0).rotate(idx * 40 - 20 * (summon_count - 1)) * (
                enemy.radius + 36
            )
            summon.pos = enemy.pos + offset
            self.clamp_circle_to_arena(summon.pos, summon.radius)
            self.push_circle_out_of_obstacles(summon.pos, summon.radius)
            summon.navigation.force_repath = True
            summon.navigation.repath_timer = 0.0
            self.enemies.append(summon)
            self.floaters.append(
                FloatingText(
                    summon.pos.copy() + pygame.Vector2(0, -18),
                    "??",
                    config.CHALLENGE_ROOM_COLOR,
                    0.55,
                )
            )
        enemy.summon_timer = config.CHALLENGE_BOSS_SUMMON_COOLDOWN

    def fire_phase_two_boss_rocket(
        self, enemy: Enemy, direction: pygame.Vector2
    ) -> bool:
        if direction.length_squared() <= 0:
            return False
        fired = direction.normalize()
        self.spawn_projectile(
            enemy.pos + fired * (enemy.radius + 6),
            fired,
            max(16.0, enemy.damage * config.BOSS_PHASE_TWO_ROCKET_DAMAGE_MULT),
            speed=config.BULLET_SPEED
            * config.BOSS_PHASE_TWO_ROCKET_SPEED_SCALE
            * self.enemy_bullet_speed_multiplier,
            ttl=1.9,
            radius=config.ROCKET_PROJECTILE_RADIUS,
            friendly=False,
            color=config.ROCKET_COLOR,
            knockback=0.0,
            style="rocket",
            explosion_radius=config.BOSS_PHASE_TWO_ROCKET_RADIUS,
            explosion_color=config.ROCKET_EXPLOSION_COLOR,
            explosion_knockback=config.BOSS_PHASE_TWO_ROCKET_KNOCKBACK,
            trail_color=config.ROCKET_SMOKE_COLOR,
            trail_interval=config.ROCKET_TRAIL_INTERVAL,
            affect_enemies=False,
        )
        self.floaters.append(
            FloatingText(
                enemy.pos.copy() + pygame.Vector2(0, -34),
                "火箭弹",
                config.ROCKET_EXPLOSION_COLOR,
                0.45,
            )
        )
        return True

    def start_elite_burst(self, enemy: Enemy, direction: pygame.Vector2) -> None:
        enemy.action_state = "elite_burst"
        enemy.action_timer = float(config.ELITE_BURST_SIZE)
        enemy.alt_special_timer = 0.0
        if direction.length_squared() > 0:
            enemy.aim_direction = direction.normalize()

    def advance_enemy_navigation_state(self, enemy: Enemy, dt: float) -> None:
        nav = enemy.navigation
        nav.commit_timer = max(0.0, nav.commit_timer - dt)
        nav.repath_timer = max(0.0, nav.repath_timer - dt)
        nav.los_timer = max(0.0, nav.los_timer - dt)
        nav.obstacle_mode_timer = max(0.0, nav.obstacle_mode_timer - dt)
        nav.sample_timer -= dt
        if nav.sample_origin.length_squared() <= 0:
            nav.sample_origin = enemy.pos.copy()
            nav.sample_timer = config.ENEMY_STUCK_SAMPLE_WINDOW
            return
        if nav.sample_timer > 0:
            return

        moved = enemy.pos.distance_to(nav.sample_origin)
        threshold = max(
            14.0,
            enemy.speed
            * config.ENEMY_STUCK_SAMPLE_WINDOW
            * config.ENEMY_STUCK_PROGRESS_RATIO,
        )
        if (
            nav.last_desired_move.length_squared()
            > config.ENEMY_NAV_MIN_MOVE * config.ENEMY_NAV_MIN_MOVE
            and moved < threshold
        ):
            nav.force_repath = True
            nav.repath_timer = 0.0
            nav.pending_unstuck = True
            nav.obstacle_mode_timer = max(
                nav.obstacle_mode_timer, config.ENEMY_OBSTACLE_MODE_TIME
            )
            nav.obstacle_failures += 1
            nav.unstuck_side *= -1
        else:
            nav.obstacle_failures = max(0, nav.obstacle_failures - 1)
        nav.sample_origin = enemy.pos.copy()
        nav.sample_timer = config.ENEMY_STUCK_SAMPLE_WINDOW

    def segment_rect_hit_distance_sq(
        self,
        start: pygame.Vector2,
        end: pygame.Vector2,
        rect: pygame.Rect,
        padding: int = 0,
    ) -> float | None:
        target = rect.inflate(padding * 2, padding * 2)
        clipped = target.clipline(
            (round(start.x), round(start.y)),
            (round(end.x), round(end.y)),
        )
        if not clipped:
            return None
        hit_a = pygame.Vector2(clipped[0])
        hit_b = pygame.Vector2(clipped[1])
        return min(
            start.distance_squared_to(hit_a),
            start.distance_squared_to(hit_b),
        )

    def find_line_of_sight_blocker(
        self, start: pygame.Vector2, end: pygame.Vector2, radius: int = 4
    ) -> RoomObstacle | None:
        best_obstacle: RoomObstacle | None = None
        best_distance = float("inf")
        for obstacle in self.query_obstacles_in_segment(start, end, radius):
            hit_distance = self.segment_rect_hit_distance_sq(
                start, end, obstacle.rect, padding=radius
            )
            if hit_distance is None or hit_distance >= best_distance:
                continue
            best_distance = hit_distance
            best_obstacle = obstacle
        return best_obstacle

    def should_use_obstacle_anchor(self, obstacle: RoomObstacle | None) -> bool:
        if obstacle is None:
            return False
        if getattr(obstacle, "tag", "normal") != "wall":
            return True
        return obstacle.rect.width < 160 or obstacle.rect.height < 160

    def choose_obstacle_anchor(
        self,
        enemy: Enemy,
        obstacle: RoomObstacle | None,
        goal: pygame.Vector2 | None = None,
    ) -> pygame.Vector2 | None:
        if obstacle is None:
            return None
        chase_goal = self.player_pos if goal is None else goal
        offset = max(10.0, config.ENEMY_OBSTACLE_ANCHOR_OFFSET)
        clearance = int(enemy.radius + offset)
        expanded = obstacle.rect.inflate(clearance * 2, clearance * 2)
        arena = self.arena_rect().inflate(-enemy.radius * 2, -enemy.radius * 2)
        mid_x = max(expanded.left, min(chase_goal.x, expanded.right))
        mid_y = max(expanded.top, min(chase_goal.y, expanded.bottom))
        left_x = expanded.left - offset
        right_x = expanded.right + offset
        top_y = expanded.top - offset
        bottom_y = expanded.bottom + offset
        candidates = [
            pygame.Vector2(left_x, top_y),
            pygame.Vector2(right_x, top_y),
            pygame.Vector2(left_x, bottom_y),
            pygame.Vector2(right_x, bottom_y),
            pygame.Vector2(left_x, mid_y),
            pygame.Vector2(right_x, mid_y),
            pygame.Vector2(mid_x, top_y),
            pygame.Vector2(mid_x, bottom_y),
        ]
        axis_delta = chase_goal - enemy.pos
        prefer_vertical = abs(axis_delta.x) >= abs(axis_delta.y)
        best: pygame.Vector2 | None = None
        best_score = float("inf")
        los_radius = max(6, enemy.radius // 2)
        for candidate in candidates:
            if not arena.collidepoint(candidate.x, candidate.y):
                continue
            if self.position_hits_obstacle(candidate, enemy.radius):
                continue
            candidate_side_x = candidate.x - obstacle.rect.centerx
            candidate_side_y = candidate.y - obstacle.rect.centery
            enemy_side_x = enemy.pos.x - obstacle.rect.centerx
            enemy_side_y = enemy.pos.y - obstacle.rect.centery
            goal_side_x = chase_goal.x - obstacle.rect.centerx
            goal_side_y = chase_goal.y - obstacle.rect.centery
            side_sign = (
                -1
                if (
                    candidate.y < obstacle.rect.centery
                    if prefer_vertical
                    else candidate.x < obstacle.rect.centerx
                )
                else 1
            )
            score = (
                candidate.distance_squared_to(chase_goal)
                + candidate.distance_squared_to(enemy.pos) * 0.35
            )
            if enemy_side_x * goal_side_x < 0 and candidate_side_x * goal_side_x <= 0:
                score += 5200
            if enemy_side_y * goal_side_y < 0 and candidate_side_y * goal_side_y <= 0:
                score += 5200
            if side_sign != enemy.navigation.unstuck_side:
                score += 4500
            if (
                enemy.navigation.obstacle_anchor.length_squared() > 0
                and candidate.distance_squared_to(enemy.navigation.obstacle_anchor)
                < 28 * 28
            ):
                score -= 1200
            candidate_blocker = self.find_line_of_sight_blocker(
                enemy.pos, candidate, los_radius
            )
            if candidate_blocker is not None:
                score += 16000
                if candidate_blocker is not obstacle:
                    score += 8000
            if (
                self.find_line_of_sight_blocker(candidate, chase_goal, los_radius)
                is None
            ):
                score -= 18000
            if score < best_score:
                best = candidate.copy()
                best_score = score
        return best

    def choose_route_anchor(
        self,
        enemy: Enemy,
        blocker: RoomObstacle | None,
        goal: pygame.Vector2,
    ) -> pygame.Vector2 | None:
        anchor = self.choose_obstacle_anchor(enemy, blocker, goal)
        if anchor is None:
            return None
        enemy.navigation.obstacle_anchor = anchor.copy()
        enemy.navigation.commit_timer = max(
            enemy.navigation.commit_timer, config.ENEMY_NAV_COMMIT_TIME
        )
        return anchor

    def build_enemy_unstuck_delta(
        self, enemy: Enemy, nav_target: pygame.Vector2
    ) -> pygame.Vector2:
        nav = enemy.navigation
        if not nav.pending_unstuck:
            return pygame.Vector2()
        nav.pending_unstuck = False
        base = nav_target - enemy.pos
        if base.length_squared() <= 0:
            base = self.player_pos - enemy.pos
        if base.length_squared() <= 0:
            base = pygame.Vector2(1, 0)
        base = base.normalize()
        lateral = pygame.Vector2(-base.y, base.x)
        lateral *= -1 if nav.unstuck_side < 0 else 1
        candidates = (
            lateral * config.ENEMY_UNSTUCK_SIDE_STEP
            - base * config.ENEMY_UNSTUCK_BACKSTEP,
            -lateral * config.ENEMY_UNSTUCK_SIDE_STEP * 0.82
            - base * (config.ENEMY_UNSTUCK_BACKSTEP * 0.75),
            -base * (config.ENEMY_UNSTUCK_BACKSTEP * 1.2),
        )
        best_delta = pygame.Vector2()
        best_score = float("-inf")
        for candidate in candidates:
            trial = enemy.pos.copy()
            moved = self.move_circle_with_collisions(trial, enemy.radius, candidate)
            if moved.length_squared() <= 4:
                continue
            score = (
                moved.length_squared()
                - trial.distance_squared_to(nav_target) * 0.12
                - abs(candidate.length() - moved.length()) * 8.0
            )
            if score > best_score:
                best_score = score
                best_delta = moved
        nav.commit_timer = max(nav.commit_timer, config.ENEMY_UNSTUCK_COMMIT_TIME)
        return best_delta

    def update_enemy_block_state(
        self,
        enemy: Enemy,
        desired_move: pygame.Vector2,
        actual_move: pygame.Vector2,
        plan: EnemyNavigationPlan,
        dt: float,
    ) -> None:
        nav = enemy.navigation
        nav.last_desired_move = desired_move.copy()
        nav.last_actual_move = actual_move.copy()
        if (
            desired_move.length_squared()
            <= config.ENEMY_NAV_MIN_MOVE * config.ENEMY_NAV_MIN_MOVE
        ):
            nav.blocked_timer = max(0.0, nav.blocked_timer - dt)
            return

        desired_length = desired_move.length()
        actual_length = actual_move.length()
        if actual_length <= desired_length * config.ENEMY_BLOCKED_MOVE_RATIO:
            nav.blocked_timer += dt
            if nav.blocked_timer >= config.ENEMY_BLOCKED_TIME:
                nav.force_repath = True
                nav.repath_timer = 0.0
                nav.commit_timer = min(nav.commit_timer, config.ENEMY_NAV_COMMIT_TIME * 0.4)
                nav.obstacle_mode_timer = max(
                    nav.obstacle_mode_timer, config.ENEMY_OBSTACLE_MODE_TIME
                )
                nav.obstacle_failures += 1
                if (
                    nav.blocked_timer >= config.ENEMY_BLOCKED_TIME * 1.5
                    or plan.mode == "anchor"
                ):
                    nav.pending_unstuck = True
                    nav.unstuck_side *= -1
            return

        nav.blocked_timer = max(0.0, nav.blocked_timer - dt * 2.0)
        if actual_length >= desired_length * 0.55:
            nav.obstacle_failures = max(0, nav.obstacle_failures - 1)

    def get_enemy_navigation_plan(self, enemy: Enemy) -> EnemyNavigationPlan:
        nav = enemy.navigation
        los_radius = max(6, enemy.radius // 2)
        reached_target = (
            nav.committed_target.length_squared() > 0
            and enemy.pos.distance_squared_to(nav.committed_target)
            <= config.ENEMY_TARGET_REACHED_RADIUS
            * config.ENEMY_TARGET_REACHED_RADIUS
        )
        needs_refresh = nav.force_repath or nav.commit_timer <= 0 or reached_target
        if nav.repath_timer <= 0 and (not nav.has_los or nav.route_mode != "direct"):
            needs_refresh = True

        blocker: RoomObstacle | None = None
        if nav.los_timer <= 0 or needs_refresh:
            blocker = self.find_line_of_sight_blocker(
                enemy.pos, self.player_pos, los_radius
            )
            nav.has_los = blocker is None
            nav.los_timer = config.ENEMY_NAV_LOS_INTERVAL

        if not needs_refresh and nav.committed_target.length_squared() > 0:
            return EnemyNavigationPlan(
                target=nav.committed_target.copy(),
                has_los=nav.has_los,
                direct_engage=nav.route_mode == "direct" and nav.has_los,
                mode=nav.route_mode,
                blocker=blocker,
            )

        target = self.player_pos.copy()
        mode = "direct"
        direct_engage = nav.has_los
        if blocker is None and not nav.has_los:
            blocker = self.find_line_of_sight_blocker(
                enemy.pos, self.player_pos, los_radius
            )

        if not nav.has_los:
            route_target, direct_engage = self.get_enemy_navigation_target(
                enemy.pos, enemy.radius
            )
            target = route_target
            mode = "direct" if direct_engage else "field"

            route_blocker = None
            anchor: pygame.Vector2 | None = None
            should_try_anchor = (
                blocker is not None
                and (nav.obstacle_mode_timer > 0 or nav.obstacle_failures > 0)
            )
            if should_try_anchor and target.distance_squared_to(self.player_pos) > 16:
                route_blocker = self.find_line_of_sight_blocker(
                    enemy.pos, target, los_radius
                )
            elif should_try_anchor:
                route_blocker = blocker

            if route_blocker is not None:
                anchor = self.choose_route_anchor(enemy, route_blocker, self.player_pos)
            if anchor is not None:
                target = anchor
                blocker = route_blocker
                mode = "anchor"
                direct_engage = False

        nav.committed_target = target.copy()
        nav.commit_timer = config.ENEMY_NAV_COMMIT_TIME
        nav.repath_timer = (
            0.0 if nav.force_repath else config.ENEMY_NAV_REPATH_INTERVAL
        )
        nav.force_repath = False
        nav.route_mode = mode
        return EnemyNavigationPlan(
            target=target.copy(),
            has_los=nav.has_los,
            direct_engage=direct_engage,
            mode=mode,
            blocker=blocker,
        )

    def build_shooter_move_delta(
        self,
        enemy: Enemy,
        delta_to_player: pygame.Vector2,
        nav_direction: pygame.Vector2,
        engage: bool,
        dt: float,
    ) -> pygame.Vector2:
        move_delta = pygame.Vector2()
        if engage and delta_to_player.length_squared() > 0:
            player_direction = delta_to_player.normalize()
            distance = delta_to_player.length()
            if distance > 320:
                move_delta += player_direction * enemy.speed * dt
            elif distance < 240:
                move_delta -= player_direction * enemy.speed * 0.75 * dt
            move_delta += (
                pygame.Vector2(-player_direction.y, player_direction.x) * 18 * dt
            )
            if enemy.shoot_timer <= 0:
                self.enemy_shoot(
                    enemy,
                    player_direction,
                    self.get_enemy_projectile_damage(enemy),
                    config.BULLET_ENEMY_COLOR,
                )
                enemy.shoot_timer = enemy.shoot_cooldown
            return move_delta
        return nav_direction * enemy.speed * 0.9 * dt

    def build_laser_move_delta(
        self,
        enemy: Enemy,
        delta_to_player: pygame.Vector2,
        nav_direction: pygame.Vector2,
        engage: bool,
        dt: float,
    ) -> pygame.Vector2:
        move_delta = pygame.Vector2()
        telegraph_window, lock_window = self.get_enemy_laser_timing(enemy)
        tracking = 0 < enemy.shoot_timer <= telegraph_window
        locked = 0 < enemy.shoot_timer <= lock_window
        if delta_to_player.length_squared() > 0 and tracking and not locked:
            enemy.aim_direction = delta_to_player.normalize()
        elif (
            enemy.aim_direction.length_squared() <= 0
            and delta_to_player.length_squared() > 0
        ):
            enemy.aim_direction = delta_to_player.normalize()

        if engage and delta_to_player.length_squared() > 0:
            player_direction = delta_to_player.normalize()
            distance = delta_to_player.length()
            if enemy.shoot_timer > telegraph_window:
                if distance > 340:
                    move_delta += player_direction * enemy.speed * dt
                elif distance < 230:
                    move_delta -= player_direction * enemy.speed * 0.85 * dt
                move_delta += (
                    pygame.Vector2(-player_direction.y, player_direction.x) * 14 * dt
                )
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
        return move_delta

    def build_shotgunner_move_delta(
        self,
        enemy: Enemy,
        delta_to_player: pygame.Vector2,
        nav_direction: pygame.Vector2,
        engage: bool,
        dt: float,
    ) -> pygame.Vector2:
        move_delta = pygame.Vector2()
        if engage and delta_to_player.length_squared() > 0:
            player_direction = delta_to_player.normalize()
            distance = delta_to_player.length()
            if distance > 220:
                move_delta += player_direction * enemy.speed * 1.06 * dt
            elif distance < 112:
                move_delta -= player_direction * enemy.speed * 0.58 * dt
            move_delta += (
                pygame.Vector2(-player_direction.y, player_direction.x) * 12 * dt
            )
            if enemy.shoot_timer <= 0 and distance <= 260:
                self.enemy_shoot(
                    enemy,
                    player_direction,
                    self.get_enemy_projectile_damage(enemy),
                    config.SHOTGUN_PELLET_COLOR,
                    angles=[
                        -config.SHOTGUNNER_PELLET_SPREAD,
                        -0.16,
                        0.0,
                        0.16,
                        config.SHOTGUNNER_PELLET_SPREAD,
                    ],
                    speed_scale=config.SHOTGUNNER_PELLET_SPEED_SCALE,
                    ttl=config.SHOTGUNNER_PELLET_TTL,
                    radius=config.BULLET_RADIUS,
                    decay_visual=True,
                )
                enemy.shoot_timer = enemy.shoot_cooldown
            return move_delta
        return nav_direction * enemy.speed * 0.94 * dt

    def fire_turret_rocket(self, enemy: Enemy, direction: pygame.Vector2) -> bool:
        if direction.length_squared() <= 0:
            return False
        fired = direction.normalize()
        self.spawn_projectile(
            enemy.pos + fired * (enemy.radius + 6),
            fired,
            self.get_enemy_projectile_damage(enemy) * config.TURRET_ROCKET_DAMAGE_MULT,
            speed=config.BULLET_SPEED
            * config.TURRET_ROCKET_SPEED_SCALE
            * self.enemy_bullet_speed_multiplier,
            ttl=1.8,
            radius=config.ROCKET_PROJECTILE_RADIUS,
            friendly=False,
            color=config.ROCKET_COLOR,
            knockback=0.0,
            style="rocket",
            explosion_radius=config.ROCKET_EXPLOSION_RADIUS * 0.72,
            explosion_color=config.ROCKET_EXPLOSION_COLOR,
            explosion_knockback=config.ROCKET_EXPLOSION_KNOCKBACK * 0.72,
            trail_color=config.ROCKET_SMOKE_COLOR,
            trail_interval=config.ROCKET_TRAIL_INTERVAL,
            homing_strength=config.TURRET_ROCKET_HOMING_STRENGTH,
            homing_radius=config.TURRET_ROCKET_HOMING_RADIUS,
            affect_enemies=False,
        )
        return True

    def build_turret_move_delta(
        self,
        enemy: Enemy,
        delta_to_player: pygame.Vector2,
        engage: bool,
        dt: float,
    ) -> pygame.Vector2:
        _ = dt
        move_delta = pygame.Vector2()
        if delta_to_player.length_squared() <= 0:
            return move_delta
        desired = delta_to_player.normalize()
        if enemy.aim_direction.length_squared() <= 0:
            enemy.aim_direction = desired
        else:
            blend = min(1.0, config.TURRET_ROTATION_LERP * max(1 / config.FPS, dt))
            enemy.aim_direction = enemy.aim_direction.lerp(desired, blend)
        if not engage or enemy.shoot_timer > 0:
            return move_delta
        if enemy.variant == "elite_turret":
            self.fire_turret_rocket(enemy, enemy.aim_direction)
        else:
            self.enemy_shoot(
                enemy,
                enemy.aim_direction,
                self.get_enemy_projectile_damage(enemy),
                config.BULLET_ENEMY_COLOR,
                spread=0.08,
            )
        enemy.shoot_timer = enemy.shoot_cooldown
        return move_delta

    def build_elite_move_delta(
        self,
        enemy: Enemy,
        delta_to_player: pygame.Vector2,
        nav_direction: pygame.Vector2,
        engage: bool,
        dt: float,
    ) -> pygame.Vector2:
        move_delta = pygame.Vector2()
        if engage and delta_to_player.length_squared() > 0:
            player_direction = delta_to_player.normalize()
            distance = delta_to_player.length()
            enemy.aim_direction = player_direction
            lateral = pygame.Vector2(-player_direction.y, player_direction.x)
            if enemy.action_state == "elite_burst":
                move_delta += lateral * 20 * dt
                if distance > 280:
                    move_delta += player_direction * enemy.speed * 0.16 * dt
                elif distance < 150:
                    move_delta -= player_direction * enemy.speed * 0.24 * dt
                if enemy.alt_special_timer <= 0 and enemy.action_timer > 0:
                    jittered = enemy.aim_direction.rotate_rad(
                        self.rng.uniform(-0.035, 0.035)
                    )
                    self.enemy_shoot(
                        enemy,
                        jittered,
                        self.get_enemy_projectile_damage(enemy),
                        config.BULLET_ELITE_COLOR,
                    )
                    enemy.action_timer -= 1
                    enemy.alt_special_timer = config.ELITE_BURST_INTERVAL
                if enemy.action_timer <= 0:
                    enemy.action_state = ""
                    enemy.action_timer = 0.0
                    enemy.shoot_timer = enemy.shoot_cooldown
                return move_delta

            if distance > 270:
                move_delta += player_direction * enemy.speed * 1.04 * dt
            elif distance < 180:
                move_delta -= player_direction * enemy.speed * 0.18 * dt
            move_delta += lateral * 10 * dt
            if enemy.shoot_timer <= 0:
                self.start_elite_burst(enemy, player_direction)
            return move_delta

        if enemy.action_state == "elite_burst":
            enemy.action_state = ""
            enemy.action_timer = 0.0
        return nav_direction * enemy.speed * 0.96 * dt

    def build_pursuit_move_delta(
        self,
        enemy: Enemy,
        delta_to_player: pygame.Vector2,
        nav_direction: pygame.Vector2,
        plan: EnemyNavigationPlan,
        dt: float,
    ) -> tuple[pygame.Vector2, bool]:
        move_delta = pygame.Vector2()
        if (
            enemy.kind == "charger"
            and self.charger_dash_available()
            and delta_to_player.length_squared() > 0
            and delta_to_player.length() <= config.CHARGER_DASH_TRIGGER_RANGE
            and self.start_charger_dash(enemy, delta_to_player.normalize())
        ):
            return move_delta, True
        if enemy.kind == "boss" and delta_to_player.length_squared() > 0:
            distance = delta_to_player.length()
            if enemy.variant == "challenge":
                telegraph_window, lock_window = self.get_enemy_laser_timing(enemy)
                tracking = 0 < enemy.shoot_timer <= telegraph_window
                locked = 0 < enemy.shoot_timer <= lock_window
                if tracking and not locked:
                    enemy.aim_direction = delta_to_player.normalize()
                elif enemy.aim_direction.length_squared() <= 0:
                    enemy.aim_direction = delta_to_player.normalize()
                laser_lock_active = (
                    plan.has_los and self.challenge_boss_laser_lock_active(enemy)
                )
                if (
                    enemy.phase >= 2
                    and enemy.summon_timer <= 0
                    and enemy.action_state == ""
                    and not laser_lock_active
                ):
                    self.start_enemy_action(
                        enemy,
                        "summon",
                        config.CHALLENGE_BOSS_SUMMON_TELEGRAPH,
                    )
                    enemy.summon_timer = config.CHALLENGE_BOSS_SUMMON_COOLDOWN
                    return move_delta, True
                if (
                    plan.has_los
                    and distance
                    <= (
                        config.CHALLENGE_BOSS_DASH_TRIGGER_RANGE
                        * (
                            config.CHALLENGE_BOSS_PHASE_TWO_DASH_RANGE_MULT
                            if enemy.phase >= 2
                            else 1.0
                        )
                    )
                    and enemy.alt_special_timer <= 0
                    and not laser_lock_active
                ):
                    self.start_challenge_boss_dash(enemy, delta_to_player.normalize())
                    return move_delta, True
                if (
                    plan.has_los
                    and config.BOSS_NOVA_MIN_RANGE <= distance <= config.BOSS_NOVA_MAX_RANGE
                    and enemy.special_timer <= 0
                    and not laser_lock_active
                ):
                    self.start_enemy_action(enemy, "nova", config.BOSS_NOVA_TELEGRAPH)
                    enemy.special_timer = config.BOSS_NOVA_COOLDOWN
                    enemy.shoot_timer = max(
                        enemy.shoot_timer,
                        config.BOSS_NOVA_TELEGRAPH + 0.24,
                    )
                    return move_delta, True
            else:
                if (
                    plan.has_los
                    and distance <= config.BOSS_STOMP_TRIGGER_RANGE
                    and enemy.special_timer <= 0
                ):
                    self.start_enemy_action(enemy, "stomp", config.BOSS_STOMP_TELEGRAPH)
                    enemy.special_timer = config.BOSS_STOMP_COOLDOWN
                    enemy.shoot_timer = max(
                        enemy.shoot_timer, config.BOSS_STOMP_TELEGRAPH + 0.18
                    )
                    return move_delta, True
                if (
                    plan.has_los
                    and config.BOSS_NOVA_MIN_RANGE <= distance <= config.BOSS_NOVA_MAX_RANGE
                    and enemy.alt_special_timer <= 0
                ):
                    self.start_enemy_action(enemy, "nova", config.BOSS_NOVA_TELEGRAPH)
                    enemy.alt_special_timer = config.BOSS_NOVA_COOLDOWN
                    enemy.shoot_timer = max(
                        enemy.shoot_timer,
                        config.BOSS_NOVA_TELEGRAPH + 0.24,
                    )
                    return move_delta, True

        speed_scale = 1.18 if enemy.kind == "charger" else 1.0
        pursue_direction = (
            delta_to_player.normalize()
            if plan.direct_engage and delta_to_player.length_squared() > 0
            else nav_direction
        )
        if (
            enemy.kind == "boss"
            and plan.has_los
            and delta_to_player.length_squared() > 0
            and delta_to_player.length() < 150
        ):
            move_delta -= delta_to_player.normalize() * enemy.speed * 0.12 * dt
        move_delta += pursue_direction * enemy.speed * speed_scale * dt

        if (
            enemy.kind == "boss"
            and enemy.variant == "challenge"
            and enemy.shoot_timer <= 0
            and plan.has_los
            and enemy.aim_direction.length_squared() > 0
        ):
            self.fire_laser(
                enemy.pos.copy(),
                enemy.aim_direction,
                self.get_enemy_laser_damage(enemy),
                self.get_enemy_laser_width(enemy),
                config.ENEMY_LASER_COLOR,
                friendly=False,
                trace_ttl=0.22,
            )
            enemy.shoot_timer = enemy.shoot_cooldown
            enemy.aim_direction = pygame.Vector2()
        elif (
            enemy.kind == "boss"
            and enemy.shoot_timer <= 0
            and plan.has_los
            and delta_to_player.length_squared() > 0
        ):
            fired_rocket = (
                enemy.phase >= 2
                and enemy.variant != "challenge"
                and self.rng.random() < config.BOSS_PHASE_TWO_ROCKET_CHANCE
                and self.fire_phase_two_boss_rocket(enemy, delta_to_player.normalize())
            )
            if not fired_rocket:
                self.enemy_shoot(
                    enemy,
                    delta_to_player.normalize(),
                    self.get_enemy_projectile_damage(enemy),
                    config.BULLET_ELITE_COLOR,
                    spread=0.14,
                )
            enemy.shoot_timer = enemy.shoot_cooldown
        return move_delta, False

    def build_enemy_move_delta(
        self, enemy: Enemy, plan: EnemyNavigationPlan, dt: float
    ) -> tuple[pygame.Vector2, bool]:
        delta_to_player = self.player_pos - enemy.pos
        delta_to_nav = plan.target - enemy.pos
        if delta_to_nav.length_squared() <= 0:
            return pygame.Vector2(), False
        nav_direction = delta_to_nav.normalize()
        engage = plan.direct_engage or plan.has_los
        if enemy.kind == "shooter":
            return (
                self.build_shooter_move_delta(
                    enemy, delta_to_player, nav_direction, engage, dt
                ),
                False,
            )
        if enemy.kind == "laser":
            return (
                self.build_laser_move_delta(
                    enemy, delta_to_player, nav_direction, engage, dt
                ),
                False,
            )
        if enemy.kind == "shotgunner":
            return (
                self.build_shotgunner_move_delta(
                    enemy, delta_to_player, nav_direction, engage, dt
                ),
                False,
            )
        if enemy.kind == "turret":
            return (
                self.build_turret_move_delta(enemy, delta_to_player, engage, dt),
                False,
            )
        if enemy.kind == "elite":
            return (
                self.build_elite_move_delta(
                    enemy, delta_to_player, nav_direction, engage, dt
                ),
                False,
            )
        return self.build_pursuit_move_delta(
            enemy, delta_to_player, nav_direction, plan, dt
        )

    def update_enemy(self, enemy: Enemy, dt: float) -> None:
        if self.update_enemy_statuses(enemy, dt):
            return
        enemy.stun_timer = max(0.0, enemy.stun_timer - dt)
        if self.should_advance_enemy_shoot_timer(enemy):
            enemy.shoot_timer -= dt
        enemy.special_timer = max(0.0, enemy.special_timer - dt)
        enemy.alt_special_timer = max(0.0, enemy.alt_special_timer - dt)
        enemy.summon_timer = max(0.0, enemy.summon_timer - dt)
        if enemy.stun_timer > 0:
            enemy.action_state = ""
            enemy.action_timer = 0.0
            enemy.aim_direction = pygame.Vector2()
            enemy.navigation.last_desired_move = pygame.Vector2()
            enemy.navigation.sample_origin = enemy.pos.copy()
            enemy.navigation.sample_timer = config.ENEMY_STUCK_SAMPLE_WINDOW
            return
        if enemy.kind == "boss":
            self.activate_boss_phase_two(enemy)
        if self.advance_charger_dash(enemy, dt):
            enemy.navigation.last_desired_move = pygame.Vector2()
            enemy.navigation.sample_origin = enemy.pos.copy()
            enemy.navigation.sample_timer = config.ENEMY_STUCK_SAMPLE_WINDOW
            return
        if self.update_boss_action(enemy, dt):
            enemy.navigation.last_desired_move = pygame.Vector2()
            enemy.navigation.sample_origin = enemy.pos.copy()
            enemy.navigation.sample_timer = config.ENEMY_STUCK_SAMPLE_WINDOW
            return

        self.advance_enemy_navigation_state(enemy, dt)
        plan = self.get_enemy_navigation_plan(enemy)
        move_delta, stop_update = self.build_enemy_move_delta(enemy, plan, dt)
        if stop_update:
            enemy.navigation.last_desired_move = pygame.Vector2()
            return
        if enemy.immobile:
            enemy.navigation.last_desired_move = pygame.Vector2()
            enemy.navigation.last_actual_move = pygame.Vector2()
            return

        move_delta = self.blend_enemy_steering(enemy, move_delta, plan.target)
        move_delta += self.build_enemy_unstuck_delta(enemy, plan.target)
        actual_move = self.move_enemy_with_navigation(enemy, move_delta, plan.target, dt)
        self.update_enemy_block_state(enemy, move_delta, actual_move, plan, dt)
        if enemy.pos.distance_to(self.player_pos) <= enemy.radius + config.PLAYER_RADIUS:
            if self.iframes <= 0:
                self.damage_player(
                    enemy.damage,
                    (255, 130, 130),
                    0.45,
                    shield_multiplier=enemy.shield_damage_multiplier,
                )

    def update_enemies(self, dt: float) -> None:
        self.refresh_enemy_spatial_index()
        for enemy in self.enemies[:]:
            self.update_enemy(enemy, dt)
    def enemy_shoot(
        self,
        enemy: Enemy,
        direction: pygame.Vector2,
        damage: float,
        color: tuple[int, int, int],
        spread: float = 0.0,
        *,
        angles: list[float] | tuple[float, ...] | None = None,
        speed_scale: float = 0.62,
        ttl: float = 2.0,
        radius: int | None = None,
        decay_visual: bool = False,
    ) -> None:
        shot_angles = (
            list(angles)
            if angles is not None
            else ([0.0] if spread <= 0 else [-spread, 0.0, spread])
        )
        bullet_radius = config.BULLET_RADIUS + 1 if radius is None else radius
        for angle in shot_angles:
            fired = direction.rotate_rad(angle)
            self.spawn_projectile(
                enemy.pos.copy(),
                fired,
                damage,
                speed=config.BULLET_SPEED
                * speed_scale
                * self.enemy_bullet_speed_multiplier,
                ttl=ttl,
                radius=bullet_radius,
                pierce=0,
                friendly=False,
                color=color,
                decay_visual=decay_visual,
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
                    speed = (
                        config.AUTO_ABSORB_BASE_SPEED
                        + pickup.absorb_timer * config.AUTO_ABSORB_ACCEL
                    )
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
                        pickup.pos += delta.normalize() * min(
                            magnet_speed * dt, distance
                        )
            if (
                pickup.pos.distance_to(self.player_pos)
                <= pickup.radius + config.PLAYER_RADIUS
            ):
                collected.append(pickup)
                self.collect_pickup(pickup)
        for pickup in collected:
            if pickup in self.pickups:
                self.pickups.remove(pickup)

    def collect_pickup(self, pickup: Pickup) -> None:
        if pickup.kind == "xp":
            self.give_xp(pickup.amount)
            self.floaters.append(
                FloatingText(
                    self.player_pos.copy(),
                    f"+{pickup.amount} 经验",
                    config.XP_COLOR,
                    0.45,
                )
            )
        else:
            self.apply_pickup_effect(pickup)

    def apply_pickup_effect(self, pickup: Pickup) -> None:
        if pickup.kind == "heal":
            self.heal_player(pickup.amount)
        elif pickup.kind == "shield":
            self.restore_player_shield(pickup.amount)
        elif pickup.kind == "credit":
            before_tiers = self.kunkun_chip_bonus_tiers()
            gained = max(1, int(round(pickup.amount * self.credit_gain_multiplier)))
            self.credits += gained
            self.floaters.append(
                FloatingText(
                    self.player_pos.copy(), f"+{gained} 晶片", config.CREDIT_COLOR, 0.6
                )
            )
            after_tiers = self.kunkun_chip_bonus_tiers()
            if after_tiers > before_tiers:
                bonus_pct = int(after_tiers * config.KUNKUN_CHIP_DAMAGE_STEP * 100)
                self.floaters.append(
                    FloatingText(
                        self.player_pos.copy() + pygame.Vector2(0, -18),
                        f"晶片火力 +{bonus_pct}%",
                        config.BASKETBALL_COLOR,
                        0.72,
                    )
                )
        elif pickup.kind == "item":
            effect = self.rng.choice(("damage", "speed", "cooldown", "shield"))
            if effect == "damage":
                self.player_damage += 2
                text = "道具：火力 +2"
            elif effect == "speed":
                self.player_speed += 8
                text = "道具：移速 +8"
            elif effect == "shield":
                self.player_shield = min(
                    self.player_max_shield, self.player_shield + 12
                )
                text = "道具：护盾 +12"
            else:
                self.fire_cooldown = max(0.11, self.fire_cooldown * 0.98)
                text = "道具：射速提升"
            self.floaters.append(
                FloatingText(self.player_pos.copy(), text, config.ITEM_COLOR, 0.8)
            )

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
        pygame.draw.rect(
            self.screen,
            self.current_arena_border_color(),
            arena,
            width=3,
            border_radius=12,
        )

        if self.room_layout is not None:
            for chamber in self.room_layout.chambers.values():
                pygame.draw.rect(
                    self.screen,
                    config.CHAMBER_OUTLINE,
                    chamber.rect,
                    1,
                    border_radius=12,
                )
            for door in self.room_layout.doorways:
                pygame.draw.rect(
                    self.screen,
                    config.DOOR_GLOW,
                    door.inflate(14, 14),
                    border_radius=10,
                )
                pygame.draw.rect(self.screen, config.DOOR_FILL, door, border_radius=8)
            self.draw_screen_doors()

        for cloud in self.gas_clouds:
            growth_ratio = (
                1.0
                if cloud.target_radius <= 0
                else max(0.18, min(1.0, cloud.radius / cloud.target_radius))
            )
            frame = self.effect_frame(self.gas_cloud_frames, growth_ratio)
            scale = max(0.35, cloud.radius / 84.0)
            self.blit_effect_frame(frame, cloud.pos, scale=scale)

        for obstacle in self.obstacles:
            rect = obstacle.rect
            self.draw_obstacle_sprite(obstacle)
            if obstacle.destructible and obstacle.max_hp > 0:
                ratio = max(0.0, obstacle.hp / obstacle.max_hp)
                bar = pygame.Rect(rect.left, rect.bottom + 4, rect.width, 5)
                pygame.draw.rect(self.screen, (48, 28, 20), bar, border_radius=3)
                pygame.draw.rect(
                    self.screen,
                    config.ITEM_COLOR,
                    (bar.left, bar.top, bar.width * ratio, bar.height),
                    border_radius=3,
                )

        self.draw_explosion_waves()
        self.draw_room_specials()
        self.draw_enemy_telegraphs()

        for pickup in self.pickups:
            visual_pos = pickup.pos.copy()
            if not pickup.absorbing:
                visual_pos.y += math.sin(pickup.hover_phase * 3.2) * 2.5
            if pickup.absorbing:
                pygame.draw.line(
                    self.screen, pickup.color, visual_pos, self.player_pos, 2
                )
                pygame.draw.circle(
                    self.screen, pickup.color, visual_pos, pickup.radius + 5, 1
                )
            pygame.draw.circle(self.screen, pickup.color, visual_pos, pickup.radius)
            pygame.draw.circle(
                self.screen, (255, 255, 255), visual_pos, pickup.radius, 2
            )

        for bullet in self.bullets:
            radius = bullet.radius
            if bullet.decay_visual and bullet.max_ttl > 0:
                life = max(0.0, min(1.0, bullet.ttl / bullet.max_ttl))
                radius = max(1, int(round(bullet.radius * (0.28 + 0.72 * life))))
            self.draw_bullet_sprite_instance(bullet, radius)

        for enemy in self.enemies:
            self.draw_enemy_sprite(enemy)
            hp_ratio = max(0.0, enemy.hp / enemy.max_hp)
            if not enemy.is_boss:
                width = enemy.radius * 2
                top = enemy.pos.y - enemy.radius - 10
                pygame.draw.rect(
                    self.screen,
                    (40, 30, 30),
                    (enemy.pos.x - enemy.radius, top, width, 5),
                    border_radius=3,
                )
                pygame.draw.rect(
                    self.screen,
                    (255, 100, 100),
                    (enemy.pos.x - enemy.radius, top, width * hp_ratio, 5),
                    border_radius=3,
                )
            if enemy.stun_timer > 0:
                self.draw_enemy_stun_marker(enemy)
            if self.enemy_has_status(enemy, "poison"):
                self.draw_enemy_poison_marker(enemy)

        self.draw_pulse_skill_effects()
        self.draw_mamba_skill_effects()
        self.draw_laser_traces()

        self.draw_player_avatar()
        mouse = pygame.Vector2(pygame.mouse.get_pos())
        aim = self.current_fire_direction(mouse)
        self.draw_player_weapon(aim)
        if self.auto_aim_target.length_squared() > 0:
            phase = (pygame.time.get_ticks() * 0.012) % math.tau
            progress = (math.sin(phase) + 1.0) * 0.5
            frame = self.effect_frame(self.auto_aim_frames, progress)
            self.blit_effect_frame(frame, self.auto_aim_target)

        for particle in self.particles:
            pygame.draw.circle(
                self.screen, particle.color, particle.pos, max(1, int(particle.radius))
            )

        for floater in self.floaters:
            surf = self.small_font.render(floater.text, True, floater.color)
            self.screen.blit(surf, surf.get_rect(center=floater.pos))

        self.draw_boss_status_bar()
        self.draw_hud()
        self.draw_overlay()
        if self.screen_shake_timer > 0 and self.screen_shake_strength > 0:
            life = self.screen_shake_timer / max(0.01, self.screen_shake_total)
            amplitude = max(1, int(round(self.screen_shake_strength * life)))
            frame = self.screen.copy()
            offset = (
                self.rng.randint(-amplitude, amplitude),
                self.rng.randint(-amplitude, amplitude),
            )
            self.screen.fill(config.BACKGROUND)
            self.screen.blit(frame, offset)
        self.draw_screen_flash_overlay()
        pygame.display.flip()

    def draw_screen_flash_overlay(self) -> None:
        if self.screen_flash_timer <= 0 or self.screen_flash_total <= 0 or self.screen_flash_alpha <= 0:
            return
        frame = self.timed_effect_frame(
            self.screen_flash_frames, self.screen_flash_timer, self.screen_flash_total
        )
        if frame is None:
            return
        overlay = pygame.transform.smoothscale(frame, (config.WIDTH, config.HEIGHT))
        tinted = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        tinted.fill((*self.screen_flash_color, 255))
        overlay.blit(tinted, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        overlay.set_alpha(self.screen_flash_alpha)
        self.screen.blit(overlay, (0, 0))

    def draw_pulse_skill_effects(self) -> None:
        if self.pulse_effect_timer <= 0 or self.pulse_effect_total <= 0:
            return
        frame = self.timed_effect_frame(
            self.pulse_effect_frames, self.pulse_effect_timer, self.pulse_effect_total
        )
        diameter = max(24, int(self.pulse_effect_radius() * 2))
        if frame is not None:
            scaled = pygame.transform.smoothscale(frame, (diameter, diameter))
            rect = scaled.get_rect(center=(int(self.player_pos.x), int(self.player_pos.y)))
            self.screen.blit(scaled, rect)

    def draw_player_weapon(self, aim: pygame.Vector2) -> None:
        direction = (
            aim.normalize()
            if aim.length_squared() > 0
            else (
                self.last_move.normalize()
                if self.last_move.length_squared() > 0
                else pygame.Vector2(1, 0)
            )
        )
        sprite = self.weapon_sprites.get(self.selected_weapon.key)
        anchor = WEAPON_SPRITE_ANCHORS.get(self.selected_weapon.key)
        handle = self.player_pos + direction * (config.PLAYER_RADIUS - 3)
        angle = -math.degrees(math.atan2(direction.y, direction.x))
        if sprite is not None and anchor is not None:
            self.blit_anchored_surface(
                sprite,
                handle,
                anchor,
                angle_degrees=angle,
            )
            return
        muzzle = handle + direction * 22
        pygame.draw.line(self.screen, config.BULLET_COLOR, handle, muzzle, 4)

    def draw_player_avatar(self) -> None:
        key = self.selected_character.key
        sprite = self.character_sprites.get(key)
        spec = CHARACTER_SPRITE_SPECS.get(key)
        if sprite is not None and spec is not None:
            alpha = None
            if self.iframes > 0 and (pygame.time.get_ticks() // 60) % 2 == 0:
                alpha = 170
            self.blit_anchored_surface(
                sprite,
                self.player_pos,
                spec["anchor"],
                scale=config.PLAYER_RADIUS / max(1.0, float(spec["base_radius"])),
                alpha=alpha,
            )
            return
        player_color = (
            config.PLAYER_HIT_COLOR if self.iframes > 0 else config.PLAYER_COLOR
        )
        pygame.draw.circle(self.screen, player_color, self.player_pos, config.PLAYER_RADIUS)
        self.draw_actor_face(self.player_pos, config.PLAYER_RADIUS, "player")

    def draw_enemy_stun_marker(self, enemy: Enemy) -> None:
        phase = ((pygame.time.get_ticks() * 0.008) % math.tau) / math.tau
        frame = self.effect_frame(self.stun_marker_frames, phase)
        center = enemy.pos + pygame.Vector2(0, -enemy.radius - 8)
        self.blit_effect_frame(frame, center)

    def draw_enemy_poison_marker(self, enemy: Enemy) -> None:
        phase = ((pygame.time.get_ticks() * 0.008) % math.tau) / math.tau
        frame = self.effect_frame(self.poison_marker_frames, phase)
        center = enemy.pos + pygame.Vector2(enemy.radius * 0.55, -enemy.radius - 8)
        self.blit_effect_frame(frame, center)

    def draw_shooter_avatar(self, enemy: Enemy) -> None:
        self.draw_enemy_sprite(enemy)

    def draw_engineer_avatar(self, enemy: Enemy) -> None:
        self.draw_enemy_sprite(enemy)

    def draw_turret_avatar(self, enemy: Enemy) -> None:
        self.draw_enemy_sprite(enemy)

    def draw_elite_avatar(self, enemy: Enemy) -> None:
        self.draw_enemy_sprite(enemy)

    def draw_standard_boss_avatar(self, enemy: Enemy) -> None:
        self.draw_enemy_sprite(enemy)

    def draw_challenge_boss_avatar(self, enemy: Enemy) -> None:
        self.draw_enemy_sprite(enemy)

    def draw_mamba_skill_effects(self) -> None:
        if (
            self.skill_cast_key != "mamba_smash"
            and self.mamba_impact_timer <= 0
        ):
            return

        if (
            self.skill_cast_key == "mamba_smash"
            and self.skill_cast_timer > 0
            and self.skill_cast_total > 0
        ):
            direction = (
                self.skill_cast_direction.normalize()
                if self.skill_cast_direction.length_squared() > 0
                else pygame.Vector2(1, 0)
            )
            frame = self.timed_effect_frame(
                self.mamba_startup_frames, self.skill_cast_timer, self.skill_cast_total
            )
            center = self.player_pos + direction * (config.MAMBA_SKILL_RANGE * 0.471)
            angle = -math.degrees(math.atan2(direction.y, direction.x))
            self.blit_effect_frame(frame, center, angle_degrees=angle)

        if self.mamba_impact_timer > 0 and self.mamba_impact_total > 0:
            direction = (
                self.mamba_impact_direction.normalize()
                if self.mamba_impact_direction.length_squared() > 0
                else pygame.Vector2(1, 0)
            )
            frame = self.timed_effect_frame(
                self.mamba_impact_frames,
                self.mamba_impact_timer,
                self.mamba_impact_total,
            )
            angle = -math.degrees(math.atan2(direction.y, direction.x))
            self.blit_effect_frame(
                frame,
                self.mamba_impact_center,
                angle_degrees=angle,
            )

    def draw_actor_face(
        self, pos: pygame.Vector2, radius: int, kind: str, *, is_boss: bool = False
    ) -> None:
        eye_color = (18, 20, 28)
        accent = (240, 244, 255)
        eye_dx = radius * 0.34
        eye_y = pos.y - radius * 0.14
        eye_size = max(2, int(radius * 0.12))

        if kind == "player":
            pygame.draw.circle(
                self.screen, accent, (int(pos.x - eye_dx), int(eye_y)), eye_size + 1
            )
            pygame.draw.circle(
                self.screen, accent, (int(pos.x + eye_dx), int(eye_y)), eye_size + 1
            )
            pygame.draw.circle(
                self.screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size
            )
            pygame.draw.circle(
                self.screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size
            )
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
            pygame.draw.line(
                self.screen,
                eye_color,
                (left_eye.left - 2, left_eye.top + 2),
                (left_eye.right + 2, left_eye.top - 4),
                3,
            )
            pygame.draw.line(
                self.screen,
                eye_color,
                (right_eye.left - 2, right_eye.top - 4),
                (right_eye.right + 2, right_eye.top + 2),
                3,
            )
            mouth_rect = pygame.Rect(
                0, 0, int(radius * 0.92), max(10, int(radius * 0.42))
            )
            mouth_rect.center = (int(pos.x), int(pos.y + radius * 0.34))
            pygame.draw.arc(
                self.screen, eye_color, mouth_rect, math.pi + 0.25, math.tau - 0.25, 3
            )
            return

        if kind == "toxic_bloater":
            pygame.draw.circle(
                self.screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size
            )
            pygame.draw.circle(
                self.screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size
            )
            mouth_rect = pygame.Rect(
                0, 0, int(radius * 0.64), max(8, int(radius * 0.28))
            )
            mouth_rect.center = (int(pos.x), int(pos.y + radius * 0.24))
            pygame.draw.arc(self.screen, eye_color, mouth_rect, 0.25, math.pi - 0.25, 2)
            pygame.draw.circle(
                self.screen,
                accent,
                (int(pos.x), int(pos.y + radius * 0.42)),
                max(2, eye_size - 1),
                1,
            )
            return

        if kind == "reactor_bomber":
            core = pygame.Rect(
                0, 0, max(10, int(radius * 0.8)), max(10, int(radius * 0.8))
            )
            core.center = (int(pos.x), int(pos.y + radius * 0.05))
            pygame.draw.rect(self.screen, eye_color, core, 2, border_radius=4)
            pygame.draw.line(
                self.screen,
                eye_color,
                (core.left + 2, core.top + 2),
                (core.right - 2, core.bottom - 2),
                2,
            )
            pygame.draw.line(
                self.screen,
                eye_color,
                (core.right - 2, core.top + 2),
                (core.left + 2, core.bottom - 2),
                2,
            )
            pygame.draw.line(
                self.screen,
                eye_color,
                (int(pos.x - radius * 0.26), int(pos.y - radius * 0.28)),
                (int(pos.x + radius * 0.26), int(pos.y - radius * 0.28)),
                2,
            )
            return

        if kind in {"shooter", "shotgunner"}:
            pygame.draw.circle(
                self.screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size
            )
            pygame.draw.circle(
                self.screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size
            )
            mouth_radius = max(2, eye_size - 1)
            if kind == "shotgunner":
                pygame.draw.line(
                    self.screen,
                    eye_color,
                    (int(pos.x - mouth_radius * 1.5), int(pos.y + radius * 0.20)),
                    (int(pos.x + mouth_radius * 1.5), int(pos.y + radius * 0.20)),
                    2,
                )
            else:
                pygame.draw.circle(
                    self.screen,
                    eye_color,
                    (int(pos.x), int(pos.y + radius * 0.20)),
                    mouth_radius,
                    1,
                )
            return

        if kind == "laser":
            left_eye = (int(pos.x - eye_dx), int(eye_y))
            right_eye = (int(pos.x + eye_dx), int(eye_y))
            pygame.draw.line(
                self.screen,
                eye_color,
                (left_eye[0] - eye_size, left_eye[1]),
                (left_eye[0] + eye_size, left_eye[1]),
                3,
            )
            pygame.draw.line(
                self.screen,
                eye_color,
                (right_eye[0] - eye_size, right_eye[1]),
                (right_eye[0] + eye_size, right_eye[1]),
                3,
            )
            pygame.draw.line(
                self.screen,
                eye_color,
                (int(pos.x - radius * 0.18), int(pos.y + radius * 0.24)),
                (int(pos.x + radius * 0.18), int(pos.y + radius * 0.24)),
                2,
            )
            return

        if kind in {"charger", "elite"}:
            pygame.draw.line(
                self.screen,
                eye_color,
                (int(pos.x - eye_dx - eye_size), int(eye_y - 2)),
                (int(pos.x - eye_dx + eye_size), int(eye_y + 2)),
                3,
            )
            pygame.draw.line(
                self.screen,
                eye_color,
                (int(pos.x + eye_dx - eye_size), int(eye_y + 2)),
                (int(pos.x + eye_dx + eye_size), int(eye_y - 2)),
                3,
            )
            pygame.draw.arc(
                self.screen,
                eye_color,
                pygame.Rect(
                    int(pos.x - radius * 0.34),
                    int(pos.y + radius * 0.04),
                    int(radius * 0.68),
                    max(8, int(radius * 0.36)),
                ),
                math.pi + 0.15,
                math.tau - 0.15,
                2,
            )
            return

        pygame.draw.circle(
            self.screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size
        )
        pygame.draw.circle(
            self.screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size
        )
        pygame.draw.line(
            self.screen,
            eye_color,
            (int(pos.x - radius * 0.18), int(pos.y + radius * 0.22)),
            (int(pos.x + radius * 0.18), int(pos.y + radius * 0.22)),
            2,
        )

    def draw_screen_doors(self) -> None:
        if self.room_layout is None or self.current_room_state is None:
            return
        for direction, rect in self.room_layout.screen_doors.items():
            locked = self.is_door_locked(self.current_room_state, direction)
            key = f"{direction}_locked" if locked else direction
            sprite = self.map_sprites.get(key)
            spec = MAP_SPRITE_SPECS.get(direction)
            if sprite is None or spec is None:
                fill = (155, 66, 66) if locked else config.DOOR_FILL
                glow = (210, 96, 96) if locked else config.DOOR_GLOW
                pygame.draw.rect(self.screen, glow, rect.inflate(14, 14), border_radius=12)
                pygame.draw.rect(self.screen, fill, rect, border_radius=8)
                continue
            self.blit_anchored_surface(
                sprite,
                pygame.Vector2(rect.center),
                spec["anchor"],
                scale=(
                    rect.width / max(1.0, float(spec["body_size"][0])),
                    rect.height / max(1.0, float(spec["body_size"][1])),
                ),
            )

    def draw_enemy_telegraphs(self) -> None:
        for enemy in self.enemies:
            if enemy.kind == "boss" and enemy.action_state:
                if enemy.action_state == "stomp":
                    frame = self.timed_effect_frame(
                        self.boss_stomp_frames,
                        enemy.action_timer,
                        config.BOSS_STOMP_TELEGRAPH,
                    )
                    frame = self.tinted_effect_frame(
                        frame, self.boss_stomp_effect_color(enemy)
                    )
                    scale = self.current_boss_stomp_radius(enemy) / max(
                        1.0, float(config.BOSS_STOMP_RADIUS)
                    )
                    self.blit_effect_frame(frame, enemy.pos, scale=scale)
                elif enemy.action_state == "nova":
                    frame = self.timed_effect_frame(
                        self.boss_nova_frames,
                        enemy.action_timer,
                        config.BOSS_NOVA_TELEGRAPH,
                    )
                    scale = enemy.radius / max(1.0, float(config.BOSS_RADIUS))
                    self.blit_effect_frame(frame, enemy.pos, scale=scale)
                elif enemy.action_state == "dash_charge":
                    direction = (
                        enemy.aim_direction.normalize()
                        if enemy.aim_direction.length_squared() > 0
                        else pygame.Vector2(1, 0)
                    )
                    frame = self.timed_effect_frame(
                        self.challenge_dash_charge_frames,
                        enemy.action_timer,
                        config.CHALLENGE_BOSS_DASH_WINDUP,
                    )
                    dash_length = max(
                        120,
                        int(
                            self.current_challenge_boss_dash_distance(enemy)
                            * 0.7
                        ),
                    )
                    center = enemy.pos + direction * (dash_length * 0.3917)
                    angle = -math.degrees(math.atan2(direction.y, direction.x))
                    self.blit_effect_frame(
                        frame,
                        center,
                        scale=dash_length / 180.0,
                        angle_degrees=angle,
                    )
                elif enemy.action_state == "summon":
                    frame = self.timed_effect_frame(
                        self.challenge_summon_frames,
                        enemy.action_timer,
                        config.CHALLENGE_BOSS_SUMMON_TELEGRAPH,
                    )
                    scale = enemy.radius / max(1.0, float(config.BOSS_RADIUS))
                    self.blit_effect_frame(frame, enemy.pos, scale=scale)
            if (
                (
                    enemy.kind == "boss"
                    and enemy.variant == "challenge"
                    and enemy.action_state
                )
                or (
                    not self.enemy_uses_laser_attack(enemy)
                    or enemy.aim_direction.length_squared() <= 0
                )
            ):
                continue
            telegraph_window, _ = self.get_enemy_laser_timing(enemy)
            if not (0 < enemy.shoot_timer <= telegraph_window):
                continue
            points, _ = self.trace_beam(enemy.pos, enemy.aim_direction, 3)
            if len(points) < 2:
                continue
            frame = self.timed_effect_frame(
                self.enemy_laser_frames, enemy.shoot_timer, telegraph_window
            )
            start = points[0]
            end = points[-1]
            segment = end - start
            if segment.length_squared() <= 0:
                continue
            direction = segment.normalize()
            normal = pygame.Vector2(-direction.y, direction.x)
            length = segment.length()
            scale = length / 494.162
            center = (
                start
                + direction * (length * 0.4783)
                + normal * (8.685 * scale)
            )
            angle = -math.degrees(math.atan2(direction.y, direction.x)) - 7.44
            self.blit_effect_frame(
                frame,
                center,
                scale=scale,
                angle_degrees=angle,
            )

    def draw_explosion_waves(self) -> None:
        if not self.explosion_waves:
            return
        for wave in self.explosion_waves:
            frame = self.timed_effect_frame(
                self.explosion_wave_frames, wave.ttl, wave.max_ttl
            )
            frame = self.tinted_effect_frame(frame, wave.color)
            scale = wave.radius / 140.0
            self.blit_effect_frame(frame, wave.pos, scale=scale)

    def draw_laser_traces(self) -> None:
        if not self.laser_traces:
            return
        for trace in self.laser_traces:
            frames, _, base_width = self.laser_trace_asset(trace)
            frame = self.timed_effect_frame(frames, trace.ttl, trace.max_ttl)
            for start, end in zip(trace.points, trace.points[1:]):
                self.draw_laser_segment_sprite(
                    frame,
                    start,
                    end,
                    trace.color,
                    trace.width,
                    base_width,
                )

    def draw_room_specials(self) -> None:
        room = self.current_room_state
        if room is None:
            return
        if room.room_type == "shop":
            shop_limit_reached = self.shop_purchase_limit_reached(room)
            for offer in room.shop_offers:
                if offer.key == "repair":
                    accent = config.HEAL_COLOR
                elif offer.key in {"shield_charge", "shield_core"}:
                    accent = config.SHIELD_COLOR
                elif offer.key in {"damage", "crit_rate", "crit_damage"}:
                    accent = config.CRIT_COLOR
                elif offer.key in {"speed", "dash"}:
                    accent = config.PLAYER_COLOR
                elif offer.key == "what_can_i_say":
                    accent = config.MAMBA_JERSEY_COLOR
                elif offer.key in {"ricochet", "pierce", "multishot", "accuracy", "shotgun_range"}:
                    accent = config.BULLET_COLOR
                elif offer.key == "rocket_blast":
                    accent = config.ROCKET_EXPLOSION_COLOR
                else:
                    accent = config.CREDIT_COLOR
                locked_by_limit = shop_limit_reached and not offer.sold
                disabled = offer.sold or locked_by_limit
                fill = (54, 59, 82) if not disabled else (44, 42, 48)
                border = accent if not disabled else (112, 112, 118)
                panel = pygame.Rect(0, 0, 160, 110)
                panel.center = (offer.pos.x, offer.pos.y)
                pygame.draw.rect(self.screen, fill, panel, border_radius=18)
                pygame.draw.rect(self.screen, border, panel, 2, border_radius=18)
                icon_center = (panel.centerx, panel.top + 20)
                pygame.draw.circle(self.screen, accent, icon_center, 14)
                pygame.draw.circle(self.screen, (255, 255, 255), icon_center, 14, 2)

                name_lines = self.wrap_text(offer.name, self.small_font, panel.width - 20, 2)
                for idx, line in enumerate(name_lines):
                    name_surf = self.small_font.render(line, True, config.TEXT_COLOR)
                    self.screen.blit(name_surf, name_surf.get_rect(center=(panel.centerx, panel.top + 42 + idx * 16)))

                for idx, line in enumerate(self.wrap_text(offer.description, self.tiny_font, panel.width - 24, 2)):
                    desc_surf = self.tiny_font.render(line, True, config.MUTED_TEXT)
                    self.screen.blit(desc_surf, desc_surf.get_rect(center=(panel.centerx, panel.top + 74 + idx * 13)))

                if offer.sold:
                    footer_text = "已售出"
                elif locked_by_limit:
                    footer_text = "已售罄"
                else:
                    footer_text = f"{offer.cost} 晶片"
                footer_color = config.MUTED_TEXT if disabled else border
                footer_surf = self.small_font.render(footer_text, True, footer_color)
                self.screen.blit(footer_surf, footer_surf.get_rect(center=(panel.centerx, panel.bottom - 15)))
        if room.room_event is not None and room.room_event.key == "nuke" and not room.room_event.completed:
            center = (
                room.room_event.anchor.copy()
                if room.room_event.anchor is not None
                else pygame.Vector2(self.arena_rect().center)
            )
            phase = (math.sin(pygame.time.get_ticks() * 0.008) + 1.0) * 0.5
            frame = self.effect_frame(self.nuke_event_frames, phase)
            self.blit_effect_frame(frame, center)
            warning = self.small_font.render("核弹", True, config.NUKE_BORDER_COLOR)
            self.screen.blit(
                warning,
                warning.get_rect(center=(center.x, center.y - 68)),
            )
        elif (
            room.room_event is not None
            and room.room_event.key == "elite_turret"
            and not room.room_event.spawned
            and not room.room_event.completed
        ):
            center = (
                room.room_event.anchor.copy()
                if room.room_event.anchor is not None
                else pygame.Vector2(self.arena_rect().center)
            )
            phase = (math.sin(pygame.time.get_ticks() * 0.009) + 1.0) * 0.5
            frame = self.effect_frame(self.elite_turret_event_frames, phase)
            self.blit_effect_frame(frame, center)
            warning = self.small_font.render("炮塔核心", True, config.TURRET_ELITE_COLOR)
            self.screen.blit(
                warning,
                warning.get_rect(center=(center.x, center.y - 58)),
            )
        elif room.room_type == "treasure" and not room.chest_opened:
            pos = self.get_room_feature_anchor(room)
            sprite = self.map_sprites.get("treasure")
            self.blit_anchored_surface(
                sprite,
                pos,
                MAP_SPRITE_SPECS["treasure"]["anchor"],
            )
        elif room.room_type == "boss" and room.exit_active:
            pos = self.get_room_feature_anchor(room)
            sprite = self.map_sprites.get("exit_active")
            self.blit_anchored_surface(
                sprite,
                pos,
                MAP_SPRITE_SPECS["exit_active"]["anchor"],
            )

    def draw_hud_panel(
        self, rect: pygame.Rect, border_color: tuple[int, int, int] | None = None
    ) -> None:
        border = config.ARENA_BORDER if border_color is None else border_color
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            overlay,
            (*config.PANEL, config.HUD_PANEL_ALPHA),
            overlay.get_rect(),
            border_radius=16,
        )
        self.screen.blit(overlay, rect)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=16)

    def draw_hud_meter(
        self,
        rect: pygame.Rect,
        label: str,
        ratio: float,
        value_text: str,
        fill: tuple[int, int, int],
        background: tuple[int, int, int],
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(self.screen, background, rect, border_radius=8)
        inner = rect.inflate(-2, -2)
        if ratio > 0:
            width = max(8, int(inner.width * ratio))
            pygame.draw.rect(
                self.screen,
                fill,
                (inner.left, inner.top, width, inner.height),
                border_radius=7,
            )
        pygame.draw.rect(self.screen, (240, 244, 255), rect, 1, border_radius=8)
        label_text = self.fit_text_line(
            label, self.tiny_font, max(24, rect.width // 2 - 12)
        )
        value_text = self.fit_text_line(
            value_text, self.tiny_font, max(24, rect.width // 2 - 12)
        )
        if label_text:
            label_surf = self.tiny_font.render(label_text, True, config.TEXT_COLOR)
            self.screen.blit(
                label_surf,
                (rect.left + 8, rect.centery - label_surf.get_height() // 2),
            )
        if value_text:
            value_surf = self.tiny_font.render(value_text, True, config.TEXT_COLOR)
            self.screen.blit(
                value_surf,
                (
                    rect.right - value_surf.get_width() - 8,
                    rect.centery - value_surf.get_height() // 2,
                ),
            )

    def draw_hud_chip(
        self, rect: pygame.Rect, label: str, value: str, accent: tuple[int, int, int]
    ) -> None:
        pygame.draw.rect(self.screen, (28, 32, 46), rect, border_radius=10)
        pygame.draw.rect(self.screen, accent, rect, 2, border_radius=10)
        accent_bar = pygame.Rect(
            rect.left + 4, rect.top + 4, 4, max(4, rect.height - 8)
        )
        pygame.draw.rect(self.screen, accent, accent_bar, border_radius=2)
        chip_text = self.fit_text_line(
            f"{label} {value}", self.tiny_font, rect.width - 18
        )
        chip_surf = self.tiny_font.render(chip_text, True, config.TEXT_COLOR)
        self.screen.blit(
            chip_surf, chip_surf.get_rect(center=(rect.centerx + 3, rect.centery))
        )

    def draw_cooldown_widget(
        self,
        rect: pygame.Rect,
        label: str,
        timer: float,
        cooldown: float,
        accent: tuple[int, int, int],
    ) -> None:
        ready = timer <= 0
        ratio = 1.0 if ready or cooldown <= 0 else 1.0 - timer / cooldown
        ratio = max(0.0, min(1.0, ratio))
        fill_color = config.HUD_COOLDOWN_READY if ready else accent
        border = fill_color if ready else config.HUD_COOLDOWN_DIM
        pygame.draw.rect(self.screen, (24, 28, 40), rect, border_radius=12)
        inner = rect.inflate(-4, -4)
        pygame.draw.rect(self.screen, (44, 49, 64), inner, border_radius=10)
        if ratio > 0:
            fill_rect = pygame.Rect(
                inner.left,
                inner.top,
                max(10, int(inner.width * ratio)),
                inner.height,
            )
            pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=10)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=12)
        label_surf = self.tiny_font.render(label, True, config.TEXT_COLOR)
        value_text = "就绪" if ready else f"{timer:.1f}s"
        value_surf = self.tiny_font.render(value_text, True, config.TEXT_COLOR)
        self.screen.blit(label_surf, (rect.left + 8, rect.top + 4))
        self.screen.blit(
            value_surf,
            (rect.right - value_surf.get_width() - 8, rect.top + 4),
        )

    def draw_skill_cooldowns(self) -> None:
        panel = pygame.Rect(12, config.HEIGHT - 58, 196, 38)
        self.draw_hud_panel(panel, border_color=config.CARD_HILITE)
        gap = 6
        widget_width = (panel.width - 16 - gap) // 2
        dash_rect = pygame.Rect(panel.left + 5, panel.top + 6, widget_width, 24)
        skill_rect = pygame.Rect(
            dash_rect.right + gap,
            panel.top + 6,
            widget_width,
            24,
        )
        self.draw_cooldown_widget(
            dash_rect,
            "冲刺",
            self.dash_timer,
            self.dash_cooldown,
            config.PLAYER_COLOR,
        )
        self.draw_cooldown_widget(
            skill_rect,
            f"Q {self.active_skill_label}",
            self.skill_timer,
            self.active_skill_cooldown(),
            config.XP_COLOR,
        )

    def draw_boss_status_bar(self) -> None:
        boss = next((enemy for enemy in self.enemies if enemy.kind == "boss"), None)
        if boss is None:
            return
        panel = pygame.Rect(config.WIDTH // 2 - 220, 14, 440, 42)
        self.draw_hud_panel(panel, border_color=config.BOSS_BAR_BORDER)
        ratio = max(0.0, boss.hp / max(1.0, boss.max_hp))
        bar = pygame.Rect(panel.left + 12, panel.top + 18, panel.width - 24, 12)
        pygame.draw.rect(self.screen, config.BOSS_BAR_BG, bar, border_radius=8)
        fill = bar.inflate(-2, -2)
        pygame.draw.rect(
            self.screen,
            config.BOSS_BAR_FILL,
            (fill.left, fill.top, max(12, int(fill.width * ratio)), fill.height),
            border_radius=7,
        )
        pygame.draw.rect(self.screen, config.BOSS_BAR_BORDER, bar, 2, border_radius=8)
        name = f"{self.boss_name(boss)}  P{boss.phase}"
        name_surf = self.small_font.render(name, True, config.TEXT_COLOR)
        hp_surf = self.tiny_font.render(
            f"{int(max(0.0, boss.hp))}/{int(boss.max_hp)}",
            True,
            config.TEXT_COLOR,
        )
        self.screen.blit(name_surf, (panel.left + 12, panel.top + 2))
        self.screen.blit(hp_surf, (panel.right - hp_surf.get_width() - 12, panel.top + 4))
        for idx in range(2):
            center = (panel.centerx - 16 + idx * 32, panel.bottom - 7)
            color = config.BOSS_BAR_PHASE if idx < boss.phase else config.HUD_COOLDOWN_DIM
            pygame.draw.circle(self.screen, color, center, 5)
            pygame.draw.circle(self.screen, (24, 18, 18), center, 7, 1)

    def draw_hud(self) -> None:
        hp_ratio = self.player_hp / self.player_max_hp
        shield_ratio = (
            0.0
            if self.player_max_shield <= 0
            else self.player_shield / self.player_max_shield
        )
        xp_ratio = self.xp / self.xp_to_level
        room_label = self.room_display_label(self.current_room_state)
        badge_color = self.room_badge_color(self.current_room_state)

        hud_left = 12
        hud_top = 12
        panel_width = 228
        status_panel = pygame.Rect(hud_left, hud_top, panel_width, 88)
        detail_panel = pygame.Rect(hud_left, status_panel.bottom + 5, panel_width, 50)
        self.draw_hud_panel(status_panel)
        self.draw_hud_panel(detail_panel, border_color=config.CARD_HILITE)

        floor_label = self.small_font.render(f"\u7b2c {self.floor_index} \u5c42", True, config.TEXT_COLOR)
        self.screen.blit(floor_label, (status_panel.left + 10, status_panel.top + 7))

        badge = pygame.Rect(status_panel.right - 68, status_panel.top + 8, 56, 18)
        pygame.draw.rect(self.screen, config.CARD, badge, border_radius=12)
        pygame.draw.rect(self.screen, badge_color, badge, 2, border_radius=12)
        badge_text = self.fit_text_line(room_label, self.tiny_font, badge.width - 12)
        badge_surf = self.tiny_font.render(badge_text, True, config.TEXT_COLOR)
        self.screen.blit(badge_surf, badge_surf.get_rect(center=badge.center))

        meter_width = status_panel.width - 20
        self.draw_hud_meter(
            pygame.Rect(status_panel.left + 10, status_panel.top + 28, meter_width, 10),
            "",
            hp_ratio,
            "",
            config.HUD_HP_BAR,
            config.HUD_HP_BG,
        )
        self.draw_hud_meter(
            pygame.Rect(status_panel.left + 10, status_panel.top + 42, meter_width, 8),
            "",
            shield_ratio,
            "",
            config.HUD_SHIELD_BAR,
            config.HUD_SHIELD_BG,
        )
        self.draw_hud_meter(
            pygame.Rect(status_panel.left + 10, status_panel.top + 54, meter_width, 8),
            "",
            xp_ratio,
            "",
            config.HUD_XP_BAR,
            config.HUD_XP_BG,
        )

        chip_gap = 6
        chip_width = (status_panel.width - 20 - chip_gap) // 2
        chip_y = status_panel.bottom - 22
        chip_specs = (
            ("\u7b49\u7ea7", str(self.level), config.XP_COLOR),
            ("\u6676\u7247", str(self.credits), config.CREDIT_COLOR),
        )
        for idx, (label, value, accent) in enumerate(chip_specs):
            chip_rect = pygame.Rect(status_panel.left + 10 + idx * (chip_width + chip_gap), chip_y, chip_width, 16)
            self.draw_hud_chip(chip_rect, label, value, accent)

        loadout_line = self.fit_text_line(
            f"{self.selected_character.name} / {self.selected_weapon.name}",
            self.tiny_font,
            detail_panel.width - 20,
        )
        self.screen.blit(self.tiny_font.render(loadout_line, True, config.TEXT_COLOR), (detail_panel.left + 10, detail_panel.top + 7))

        detail_text = (
            f"\u4f24 {int(self.displayed_player_damage())} \u00b7 \u66b4 {int(round(self.player_crit_chance * 100))}%"
        )
        detail_line = self.fit_text_line(detail_text, self.tiny_font, detail_panel.width - 20)
        self.screen.blit(self.tiny_font.render(detail_line, True, config.MUTED_TEXT), (detail_panel.left + 10, detail_panel.top + 25))

        buff_text = self.active_player_buff_status_text()
        self.draw_skill_cooldowns()
        if buff_text:
            buff_line = self.fit_text_line(buff_text, self.tiny_font, 220)
            skills = self.tiny_font.render(buff_line, True, config.MUTED_TEXT)
            self.screen.blit(skills, (16, config.HEIGHT - 18))
        prompt = self.current_interaction_prompt()
        if prompt:
            prompt_surf = self.font.render(prompt, True, config.PLAYER_HIT_COLOR)
            self.screen.blit(
                prompt_surf,
                prompt_surf.get_rect(center=(config.WIDTH / 2, config.HEIGHT - 52)),
            )
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
            if room.challenge_tag == "high_difficulty":
                color = (
                    config.CHALLENGE_ROOM_COLOR
                    if room.visited
                    else (108, 62, 62)
                )
            elif room.room_type == "shop":
                color = config.CREDIT_COLOR if room.visited else (110, 98, 72)
            elif room.room_type == "treasure":
                color = (255, 180, 88) if room.visited else (104, 86, 66)
            elif room.room_type == "maze":
                color = (
                    config.MAZE_ROOM_COLOR if room.visited else (78, 96, 126)
                )
            elif room.room_type == "elite":
                color = (255, 130, 96) if room.visited else (112, 74, 66)
            elif room.room_type == "boss":
                color = (255, 84, 84) if room.visited else (96, 58, 58)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            if room.room_id == self.current_room_id:
                pygame.draw.rect(
                    self.screen, (255, 255, 255), rect.inflate(6, 6), 2, border_radius=5
                )
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
        elif self.mode == "floor_confirm":
            self.draw_center_card(
                "确认下潜",
                f"是否进入第 {self.floor_index + 1} 层？",
                "E / Enter 确认 · Esc 取消",
            )
        elif self.mode == "floor_transition":
            self.draw_floor_transition()
        elif self.room_clear_delay > 0:
            title = "战利品回收中" if self.pickups else "区域已清空"
            surf = self.big_font.render(title, True, config.TEXT_COLOR)
            self.screen.blit(surf, surf.get_rect(center=(config.WIDTH / 2, 54)))

    def draw_center_card(self, title: str, subtitle: str, prompt: str) -> None:
        panel = pygame.Rect(0, 0, 548, 248)
        panel.center = (config.WIDTH / 2, config.HEIGHT / 2)
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 130))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, config.PANEL, panel, border_radius=18)
        pygame.draw.rect(self.screen, config.ARENA_BORDER, panel, 3, border_radius=18)
        title_surf = self.big_font.render(title, True, config.TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(panel.centerx, panel.top + 52)))
        y = panel.top + 98
        for line in self.wrap_text(subtitle, self.font, panel.width - 72, 3):
            surf = self.font.render(line, True, config.MUTED_TEXT)
            self.screen.blit(surf, surf.get_rect(center=(panel.centerx, y)))
            y += 28
        y = max(y + 10, panel.bottom - 58)
        for line in self.wrap_text(prompt, self.small_font, panel.width - 72, 2):
            surf = self.small_font.render(line, True, config.PLAYER_COLOR)
            self.screen.blit(surf, surf.get_rect(center=(panel.centerx, y)))
            y += 22

    def draw_choice_cards(
        self,
        title: str,
        subtitle: str,
        items: list[tuple[str, str]],
        accent: tuple[int, int, int],
    ) -> None:
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        self.screen.blit(shade, (0, 0))
        title_surf = self.big_font.render(title, True, config.TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(config.WIDTH / 2, 108)))
        subtitle_surf = self.small_font.render(subtitle, True, config.MUTED_TEXT)
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(config.WIDTH / 2, 144)))
        mouse_pos = pygame.mouse.get_pos()
        for idx, ((name, description), rect) in enumerate(zip(items, self.get_choice_rects())):
            hovered = rect.collidepoint(mouse_pos)
            fill = (40, 47, 70) if hovered else config.CARD
            border = accent if hovered else config.CARD_HILITE
            pygame.draw.rect(self.screen, fill, rect, border_radius=18)
            pygame.draw.rect(self.screen, border, rect, 3, border_radius=18)
            badge = pygame.Rect(rect.left + 16, rect.top + 14, 34, 28)
            pygame.draw.rect(self.screen, config.PANEL, badge, border_radius=12)
            pygame.draw.rect(self.screen, accent, badge, 2, border_radius=12)
            num = self.small_font.render(str(idx + 1), True, config.TEXT_COLOR)
            self.screen.blit(num, num.get_rect(center=badge.center))
            name_y = rect.top + 54
            for line in self.wrap_text(name, self.font, rect.width - 32, 2):
                surf = self.font.render(line, True, config.TEXT_COLOR)
                self.screen.blit(surf, (rect.left + 16, name_y))
                name_y += 24
            desc_y = max(rect.top + 104, name_y + 6)
            for line in self.wrap_text(description, self.small_font, rect.width - 32, 3):
                surf = self.small_font.render(line, True, config.MUTED_TEXT)
                self.screen.blit(surf, (rect.left + 16, desc_y))
                desc_y += 19

    def draw_floor_transition(self) -> None:
        total = max(0.01, self.floor_transition_total)
        progress = 1.0 - self.floor_transition_timer / total
        fade = progress / 0.5 if progress < 0.5 else (1.0 - progress) / 0.5
        fade = max(0.0, min(1.0, fade))
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, int(230 * fade)))
        self.screen.blit(shade, (0, 0))
        title = (
            "下潜中..."
            if not self.floor_transition_switched
            else f"第 {self.floor_index} 层"
        )
        subtitle = (
            f"正在进入第 {self.floor_transition_target} 层"
            if not self.floor_transition_switched
            else "舱门解锁，准备继续推进"
        )
        prompt = "请稍候"
        panel = pygame.Rect(0, 0, 480, 210)
        panel.center = (config.WIDTH / 2, config.HEIGHT / 2)
        pygame.draw.rect(self.screen, config.PANEL, panel, border_radius=18)
        pygame.draw.rect(self.screen, config.ARENA_BORDER, panel, 3, border_radius=18)
        texts = [
            self.big_font.render(title, True, config.TEXT_COLOR),
            self.font.render(subtitle, True, config.MUTED_TEXT),
            self.font.render(prompt, True, config.PLAYER_COLOR),
        ]
        ys = [panel.top + 46, panel.top + 102, panel.top + 154]
        for surf, y in zip(texts, ys):
            self.screen.blit(surf, surf.get_rect(center=(panel.centerx, y)))

    def draw_level_up(self) -> None:
        self.draw_choice_cards(
            "选择增益",
            "1 / 2 / 3 或点击卡片",
            [(upgrade.name, upgrade.description) for upgrade in self.upgrade_choices],
            config.PLAYER_COLOR,
        )

    def draw_reward_room(self) -> None:
        title_text = "宝箱奖励" if self.reward_source == "treasure" else "奖励房"
        sub_text = "打开后选择 1 项强化" if self.reward_source == "treasure" else "免费获得 1 项强化"
        self.draw_choice_cards(
            title_text,
            sub_text,
            [(upgrade.name, upgrade.description) for upgrade in self.reward_choices],
            config.PLAYER_HIT_COLOR,
        )

    def draw_supply_room(self) -> None:
        self.draw_choice_cards(
            "补给房",
            "选择 1 项补给",
            [(option.name, option.description) for option in self.supply_choices],
            config.XP_COLOR,
        )

    def draw_title_menu(self) -> None:
        shade = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 152))
        self.screen.blit(shade, (0, 0))
        title = self.big_font.render("\u94a2\u94c1\u8702\u5de2", True, config.TEXT_COLOR)
        sub = self.small_font.render("\u56de\u8f66 / Space \u5f00\u59cb\u90e8\u7f72", True, config.MUTED_TEXT)
        self.screen.blit(title, title.get_rect(midleft=(44, 48)))
        self.screen.blit(sub, sub.get_rect(midleft=(46, 80)))
        mouse_pos = pygame.mouse.get_pos()
        panel = self.get_title_info_panel()
        pygame.draw.rect(self.screen, config.PANEL, panel, border_radius=18)
        pygame.draw.rect(self.screen, config.ARENA_BORDER, panel, 2, border_radius=18)

        if self.title_panel == "main":
            left_panel = pygame.Rect(28, 112, 368, 560)
            pygame.draw.rect(self.screen, config.PANEL, left_panel, border_radius=18)
            pygame.draw.rect(
                self.screen, config.ARENA_BORDER, left_panel, 2, border_radius=18
            )
            btns = self.get_title_menu_buttons()
            items = (
                ("stage", "1 \u5173\u5361\u9009\u62e9", self.selected_stage.name, self.selected_stage.description, config.PLAYER_COLOR),
                ("character", "2 \u89d2\u8272\u9009\u62e9", self.selected_character.name, self.selected_character_skill_summary(), config.SHIELD_COLOR),
                ("weapon", "3 \u6b66\u5668\u9009\u62e9", self.selected_weapon.name, self.selected_weapon.passive, config.CREDIT_COLOR),
            )
            for key, title_text, selected_name, desc, color in items:
                rect = btns[key]
                hovered = rect.collidepoint(mouse_pos)
                border = color if hovered else config.CARD_HILITE
                pygame.draw.rect(self.screen, config.CARD, rect, border_radius=14)
                pygame.draw.rect(self.screen, border, rect, 2, border_radius=14)
                self.screen.blit(
                    self.small_font.render(title_text, True, border),
                    (rect.left + 12, rect.top + 8),
                )
                self.screen.blit(
                    self.font.render(selected_name, True, config.TEXT_COLOR),
                    (rect.left + 12, rect.top + 24),
                )
                self.screen.blit(
                    self.small_font.render(
                        self.wrap_text(desc, self.small_font, rect.width - 24, 1)[0],
                        True,
                        config.MUTED_TEXT,
                    ),
                    (rect.left + 12, rect.top + 45),
                )

            record_card = pygame.Rect(44, 420, 338, 122)
            pygame.draw.rect(self.screen, config.CARD, record_card, border_radius=14)
            pygame.draw.rect(
                self.screen, config.CARD_HILITE, record_card, 2, border_radius=14
            )
            self.screen.blit(
                self.small_font.render(
                    "\u5386\u53f2\u7eaa\u5f55", True, config.MUTED_TEXT
                ),
                (record_card.left + 12, record_card.top + 8),
            )
            for idx, line in enumerate(
                (
                    f"\u6700\u9ad8\u5206\uff1a{self.best_record['best_score']}",
                    f"\u6700\u9ad8\u697c\u5c42\uff1a{self.best_record['best_floor']}",
                    f"\u6700\u9ad8\u6e05\u623f\uff1a{self.best_record['best_rooms']}",
                )
            ):
                self.screen.blit(
                    self.font.render(line, True, config.TEXT_COLOR),
                    (record_card.left + 12, record_card.top + 28 + idx * 26),
                )

            deploy_card = pygame.Rect(
                panel.left + 16, panel.top + 16, panel.width - 32, 86
            )
            pygame.draw.rect(self.screen, config.CARD, deploy_card, border_radius=14)
            pygame.draw.rect(
                self.screen, config.CARD_HILITE, deploy_card, 2, border_radius=14
            )
            self.screen.blit(
                self.font.render("当前部署", True, config.TEXT_COLOR),
                (deploy_card.left + 14, deploy_card.top + 10),
            )
            deploy_lines = (
                f"关卡：{self.selected_stage.name}",
                f"机体：{self.selected_character.name}",
                f"武器：{self.selected_weapon.name}",
            )
            deploy_col_width = (deploy_card.width - 28) // 3
            for idx, line in enumerate(deploy_lines):
                self.screen.blit(self.small_font.render(line, True, config.MUTED_TEXT), (deploy_card.left + 14 + idx * deploy_col_width, deploy_card.top + 44))

            detail_width = (panel.width - 48) // 2
            for idx, (title_text, name_text, desc_text) in enumerate(
                self.title_detail_sections()
            ):
                col = idx % 2
                row = idx // 2
                card = pygame.Rect(
                    panel.left + 16 + col * (detail_width + 16),
                    panel.top + 118 + row * 100,
                    detail_width,
                    84,
                )
                pygame.draw.rect(self.screen, config.CARD, card, border_radius=14)
                pygame.draw.rect(
                    self.screen, config.CARD_HILITE, card, 2, border_radius=14
                )
                self.screen.blit(
                    self.small_font.render(title_text, True, config.MUTED_TEXT),
                    (card.left + 12, card.top + 8),
                )
                self.screen.blit(
                    self.font.render(name_text, True, config.TEXT_COLOR),
                    (card.left + 12, card.top + 24),
                )
                for line_no, wrapped in enumerate(
                    self.wrap_text(desc_text, self.small_font, card.width - 22, 2)
                ):
                    self.screen.blit(
                        self.small_font.render(wrapped, True, config.MUTED_TEXT),
                        (card.left + 12, card.top + 48 + line_no * 16),
                    )

            skills_card = pygame.Rect(
                panel.left + 16, panel.top + 336, panel.width - 32, 78
            )
            pygame.draw.rect(self.screen, config.CARD, skills_card, border_radius=14)
            pygame.draw.rect(self.screen, config.CARD_HILITE, skills_card, 2, border_radius=14)
            self.screen.blit(self.small_font.render("\u57fa\u7840\u64cd\u4f5c", True, config.MUTED_TEXT), (skills_card.left + 12, skills_card.top + 8))
            skill_col_width = (skills_card.width - 24) // 2
            for idx, line in enumerate(TITLE_SKILLS):
                col = idx % 2
                row = idx // 2
                self.screen.blit(self.small_font.render(line, True, config.TEXT_COLOR), (skills_card.left + 12 + col * skill_col_width, skills_card.top + 28 + row * 18))

            action_card = pygame.Rect(
                panel.left + 16, panel.bottom - 90, panel.width - 32, 66
            )
            pygame.draw.rect(self.screen, config.CARD, action_card, border_radius=14)
            pygame.draw.rect(self.screen, config.CARD_HILITE, action_card, 2, border_radius=14)
            hint = self.small_font.render("确认配置后即可开始", True, config.MUTED_TEXT)
            self.screen.blit(hint, hint.get_rect(midleft=(action_card.left + 16, action_card.centery)))

            start_rect = self.get_title_start_button()
            hovered = start_rect.collidepoint(mouse_pos)
            fill = config.PLAYER_COLOR if hovered else config.CARD_HILITE
            pygame.draw.rect(self.screen, fill, start_rect, border_radius=16)
            pygame.draw.rect(
                self.screen, (240, 248, 255), start_rect, 2, border_radius=16
            )
            label = self.font.render("\u5f00\u59cb\u90e8\u7f72", True, (15, 18, 28))
            self.screen.blit(label, label.get_rect(center=start_rect.center))
        else:
            title_text, subtitle = TITLE_PANEL_INFO[self.title_panel]
            header = pygame.Rect(44, 116, 1192, 60)
            viewport = self.get_title_panel_viewport_rect()
            footer = pygame.Rect(44, 612, 1192, 60)
            pygame.draw.rect(self.screen, config.CARD, header, border_radius=16)
            pygame.draw.rect(
                self.screen, config.CARD_HILITE, header, 2, border_radius=16
            )
            self.screen.blit(
                self.font.render(title_text, True, config.TEXT_COLOR),
                (header.left + 18, header.top + 10),
            )
            self.screen.blit(
                self.small_font.render(subtitle, True, config.MUTED_TEXT),
                (header.left + 18, header.top + 34),
            )
            pygame.draw.rect(
                self.screen, config.CARD, viewport.inflate(0, 8), border_radius=18
            )
            pygame.draw.rect(
                self.screen,
                config.CARD_HILITE,
                viewport.inflate(0, 8),
                2,
                border_radius=18,
            )
            options = self.current_title_options()
            selected_key = (
                self.selected_stage.key
                if self.title_panel == "stage"
                else self.selected_character.key
                if self.title_panel == "character"
                else self.selected_weapon.key
            )
            option_rects = self.get_title_panel_option_rects(len(options))
            previous_clip = self.screen.get_clip()
            self.screen.set_clip(viewport)
            for idx, (option, rect) in enumerate(zip(options, option_rects)):
                active = option.key == selected_key
                hovered = rect.collidepoint(mouse_pos) and viewport.collidepoint(
                    mouse_pos
                )
                border = (
                    config.PLAYER_COLOR
                    if active
                    else (config.CREDIT_COLOR if hovered else config.CARD_HILITE)
                )
                fill = (44, 52, 76) if active else config.CARD
                pygame.draw.rect(self.screen, fill, rect, border_radius=16)
                pygame.draw.rect(self.screen, border, rect, 2, border_radius=16)
                index_label = self.small_font.render(str(idx + 1), True, border)
                self.screen.blit(index_label, (rect.left + 16, rect.top + 12))
                self.screen.blit(
                    self.font.render(option.name, True, config.TEXT_COLOR),
                    (rect.left + 54, rect.top + 10),
                )
                if active:
                    active_badge = pygame.Rect(rect.right - 98, rect.top + 12, 82, 24)
                    pygame.draw.rect(self.screen, config.PANEL, active_badge, border_radius=12)
                    pygame.draw.rect(self.screen, config.PLAYER_COLOR, active_badge, 2, border_radius=12)
                    badge_text = self.small_font.render("已选择", True, config.TEXT_COLOR)
                    self.screen.blit(badge_text, badge_text.get_rect(center=active_badge.center))
                if self.title_panel == "weapon":
                    desc_lines = self.wrap_text(option.description, self.small_font, rect.width - 92, 2)
                else:
                    desc_lines = self.wrap_text(option.description, self.small_font, rect.width - 92, 1)
                passive = option.passive if hasattr(option, "passive") else f"起始难度：{option.start_room}"
                passive_lines = self.wrap_text(passive, self.small_font, rect.width - 92, 1 if self.title_panel == "character" else 2)
                skill_lines: list[str] = []
                if self.title_panel == "character" and hasattr(option, "skill_key"):
                    skill_lines = self.wrap_text(self.character_skill_data(option.skill_key).description, self.small_font, rect.width - 92, 2)
                line_y = rect.top + 40
                for line in desc_lines:
                    self.screen.blit(
                        self.small_font.render(line, True, config.MUTED_TEXT),
                        (rect.left + 54, line_y),
                    )
                    line_y += 16
                for line in passive_lines:
                    self.screen.blit(
                        self.small_font.render(line, True, config.TEXT_COLOR),
                        (rect.left + 54, line_y),
                    )
                    line_y += 16
                for line in skill_lines:
                    self.screen.blit(self.small_font.render(line, True, config.SHIELD_COLOR), (rect.left + 54, line_y))
                    line_y += 16
            self.screen.set_clip(previous_clip)

            if self.title_panel_uses_scroll() and options:
                max_scroll = self.max_title_panel_scroll(count=len(options))
                if max_scroll > 0:
                    track = pygame.Rect(
                        viewport.right - 12, viewport.top + 6, 6, viewport.height - 12
                    )
                    pygame.draw.rect(self.screen, (54, 60, 82), track, border_radius=4)
                    thumb_h = max(
                        44,
                        int(
                            track.height
                            * (
                                viewport.height
                                / self.title_panel_content_height(len(options))
                            )
                        ),
                    )
                    thumb_y = track.top + int(
                        (track.height - thumb_h)
                        * (self.title_panel_scroll / max_scroll)
                    )
                    pygame.draw.rect(
                        self.screen,
                        config.PLAYER_COLOR,
                        (track.left, thumb_y, track.width, thumb_h),
                        border_radius=4,
                    )

            pygame.draw.rect(self.screen, config.CARD, footer, border_radius=16)
            pygame.draw.rect(self.screen, config.CARD_HILITE, footer, 2, border_radius=16)
            hint_text = "滚轮 / ↑↓ 滚动，数字键可直接选" if self.title_panel_uses_scroll() else "点击卡片或按数字键选择"
            hint = self.small_font.render(hint_text, True, config.MUTED_TEXT)
            self.screen.blit(
                hint, (footer.left + 18, footer.centery - hint.get_height() // 2)
            )
            self.draw_action_button(self.get_title_panel_back_button(), "\u8fd4\u56de")
            self.draw_action_button(self.get_title_panel_start_button(), "\u5f00\u5c40")

    def draw_pause_menu(self) -> None:
        self.draw_center_card("\u5df2\u6682\u505c", "\u9009\u62e9\u4e00\u9879\u64cd\u4f5c", "ESC \u7ee7\u7eed")
        labels = ["\u7ee7\u7eed", "\u91cd\u5f00", "\u83dc\u5355"]
        for rect, label in zip(self.get_center_action_buttons(3), labels):
            self.draw_action_button(rect, label)

    def draw_dead_menu(self) -> None:
        current_score = self.calculate_score()
        self.draw_center_card(
            "\u672c\u5c40\u5931\u8d25",
            f"\u5206\u6570 {current_score} · \u6e05\u623f {self.rooms_cleared} · \u51fb\u6740 {self.kills} · \u697c\u5c42 {self.floor_index}",
            f"\u6700\u9ad8\u5206 {self.best_record['best_score']} · \u6700\u9ad8\u5c42 {self.best_record['best_floor']}",
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

    def trigger_mamba_revive(self) -> bool:
        if self.selected_character.key != "mamba" or self.player_revives_remaining <= 0:
            return False
        self.player_revives_remaining -= 1
        self.player_hp = max(1.0, self.player_max_hp * config.MAMBA_REVIVE_HP_RATIO)
        self.iframes = max(self.iframes, config.MAMBA_REVIVE_IFRAMES)
        self.add_player_buff("unstoppable", config.MAMBA_REVIVE_BUFF_DURATION)
        self.spawn_particles(
            self.player_pos.copy(),
            config.MAMBA_GLOW_COLOR,
            18,
            1.2,
            (1.6, 4.8),
            (0.10, 0.24),
        )
        self.floaters.append(
            FloatingText(
                self.player_pos.copy() + pygame.Vector2(0, -30),
                "曼巴复燃",
                config.MAMBA_GLOW_COLOR,
                1.0,
            )
        )
        self.message = "曼巴奥特原地复活，进入霸体"
        return True

    def damage_player(
        self,
        amount: float,
        color: tuple[int, int, int],
        iframe_duration: float,
        *,
        shield_multiplier: float = 1.0,
    ) -> None:
        if amount <= 0:
            return
        damage_multiplier = self.player_damage_taken_multiplier()
        if damage_multiplier <= 0:
            return
        self.iframes = max(self.iframes, iframe_duration)
        remaining = amount * damage_multiplier
        if self.player_shield > 0:
            shield_load = remaining * max(1.0, shield_multiplier)
            absorbed = min(self.player_shield, shield_load)
            self.player_shield -= absorbed
            remaining = max(0.0, remaining - absorbed / max(1.0, shield_multiplier))
            self.floaters.append(
                FloatingText(
                    self.player_pos.copy() + pygame.Vector2(0, -20),
                    f"护盾 -{int(absorbed)}",
                    config.SHIELD_COLOR,
                    0.45,
                )
            )
        if remaining > 0:
            self.player_hp -= remaining
            self.floaters.append(
                FloatingText(self.player_pos.copy(), f"-{int(remaining)}", color, 0.5)
            )
        if self.player_hp <= 0:
            if self.trigger_mamba_revive():
                return
            self.player_hp = 0
            self.update_best_record()
            self.mode = "dead"
            self.message = "信号中断"

    def get_enemy_navigation_target(
        self, pos: pygame.Vector2, radius: int
    ) -> tuple[pygame.Vector2, bool]:
        if self.room_layout is None:
            return self.player_pos.copy(), True
        los_radius = max(6, radius // 2)
        if self.has_line_of_sight(pos, self.player_pos, los_radius):
            return self.player_pos.copy(), True
        field = self.get_navigation_field(radius)
        if field is not None:
            waypoint = field.next_waypoint(pos, self.player_pos)
            if waypoint is not None and waypoint.distance_squared_to(pos) > 4:
                return waypoint, False
        if len(self.room_layout.chambers) <= 1:
            return self.player_pos.copy(), False
        enemy_cell = self.room_layout.closest_cell(pos)
        player_cell = self.room_layout.closest_cell(self.player_pos)
        if enemy_cell is None or player_cell is None or enemy_cell == player_cell:
            return self.player_pos.copy(), True
        path = self.room_layout.path_between(enemy_cell, player_cell)
        if len(path) >= 2:
            door = self.room_layout.door_between(path[0], path[1])
            if door is not None:
                next_center = (
                    self.room_layout.chambers[path[1]].center
                    if path[1] in self.room_layout.chambers
                    else self.player_pos
                )
                return door.lerp(next_center, 0.2), False
        return self.player_pos.copy(), False

    def has_line_of_sight(
        self, start: pygame.Vector2, end: pygame.Vector2, radius: int = 4
    ) -> bool:
        return self.find_line_of_sight_blocker(start, end, radius) is None

    def move_circle_with_collisions(
        self, pos: pygame.Vector2, radius: int, delta: pygame.Vector2
    ) -> pygame.Vector2:
        start = pos.copy()
        if delta.length_squared() <= 0:
            self.clamp_circle_to_arena(pos, radius)
            self.push_circle_out_of_obstacles(pos, radius)
            return pos - start
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
        return pos - start

    def position_hits_obstacle(self, pos: pygame.Vector2, radius: int) -> bool:
        return any(
            self.circle_intersects_rect(pos, radius, obstacle.rect)
            for obstacle in self.obstacles
        )

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

    def circle_intersects_rect(
        self, pos: pygame.Vector2, radius: int, rect: pygame.Rect
    ) -> bool:
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
