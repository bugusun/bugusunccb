from __future__ import annotations

from dataclasses import dataclass, field

import pygame


@dataclass
class EnemyNavigationState:
    committed_target: pygame.Vector2 = field(default_factory=pygame.Vector2)
    obstacle_anchor: pygame.Vector2 = field(default_factory=pygame.Vector2)
    sample_origin: pygame.Vector2 = field(default_factory=pygame.Vector2)
    last_desired_move: pygame.Vector2 = field(default_factory=pygame.Vector2)
    last_actual_move: pygame.Vector2 = field(default_factory=pygame.Vector2)
    commit_timer: float = 0.0
    repath_timer: float = 0.0
    los_timer: float = 0.0
    blocked_timer: float = 0.0
    obstacle_mode_timer: float = 0.0
    sample_timer: float = 0.0
    has_los: bool = False
    force_repath: bool = True
    pending_unstuck: bool = False
    route_mode: str = "direct"
    obstacle_failures: int = 0
    unstuck_side: int = 1


@dataclass
class Bullet:
    pos: pygame.Vector2
    velocity: pygame.Vector2
    damage: float
    radius: int
    knockback: float
    ttl: float
    max_ttl: float = 0.0
    pierce: int = 0
    bounces_left: int = 0
    friendly: bool = True
    color: tuple[int, int, int] = (255, 255, 255)
    crit: bool = False
    hits_all: bool = False
    decay_visual: bool = False
    style: str = "bullet"
    explosion_radius: float = 0.0
    explosion_color: tuple[int, int, int] = (255, 255, 255)
    explosion_knockback: float = 0.0
    trail_color: tuple[int, int, int] | None = None
    trail_interval: float = 0.0
    trail_timer: float = 0.0
    expires_on_room_clear: bool = False
    homing_strength: float = 0.0
    homing_radius: float = 0.0
    affect_enemies: bool = True


@dataclass
class Enemy:
    pos: pygame.Vector2
    hp: float
    max_hp: float
    speed: float
    radius: int
    damage: float
    xp_reward: int
    color: tuple[int, int, int]
    knockback_resist: float = 1.0
    is_boss: bool = False
    kind: str = "grunt"
    variant: str = ""
    shoot_cooldown: float = 0.0
    shoot_timer: float = 0.0
    aim_direction: pygame.Vector2 = field(default_factory=pygame.Vector2)
    action_state: str = ""
    action_timer: float = 0.0
    special_timer: float = 0.0
    alt_special_timer: float = 0.0
    summon_timer: float = 0.0
    stun_timer: float = 0.0
    phase: int = 1
    shield_damage_multiplier: float = 1.0
    immobile: bool = False
    statuses: list["ActiveEnemyStatus"] = field(default_factory=list)
    navigation: EnemyNavigationState = field(default_factory=EnemyNavigationState)


@dataclass
class Pickup:
    pos: pygame.Vector2
    amount: int
    radius: int
    kind: str = "xp"
    color: tuple[int, int, int] = (255, 255, 255)
    label: str = ""
    hover_phase: float = 0.0
    absorbing: bool = False
    absorb_timer: float = 0.0


@dataclass
class FloatingText:
    pos: pygame.Vector2
    text: str
    color: tuple[int, int, int]
    ttl: float


@dataclass
class Particle:
    pos: pygame.Vector2
    velocity: pygame.Vector2
    color: tuple[int, int, int]
    radius: float
    ttl: float


@dataclass
class LaserTrace:
    points: list[pygame.Vector2]
    color: tuple[int, int, int]
    width: int
    ttl: float
    max_ttl: float
    impact_points: list[pygame.Vector2] = field(default_factory=list)


@dataclass
class ExplosionWave:
    pos: pygame.Vector2
    radius: float
    ttl: float
    max_ttl: float
    color: tuple[int, int, int]


@dataclass
class GasCloud:
    pos: pygame.Vector2
    radius: float
    ttl: float
    damage: float = 4.0
    tick_timer: float = 0.0
    target_radius: float = 0.0
    growth_speed: float = 0.0
    activation_delay: float = 0.0


@dataclass
class ActivePlayerBuff:
    key: str
    duration: float
    max_duration: float
    potency: float = 1.0


@dataclass
class ActiveEnemyStatus:
    key: str
    duration: float
    max_duration: float
    tick_interval: float
    damage: float
    color: tuple[int, int, int] = (255, 255, 255)
    tick_timer: float = 0.0
