from __future__ import annotations

from dataclasses import dataclass, field

import pygame


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
    shoot_cooldown: float = 0.0
    shoot_timer: float = 0.0
    aim_direction: pygame.Vector2 = field(default_factory=pygame.Vector2)
    action_state: str = ""
    action_timer: float = 0.0
    special_timer: float = 0.0
    alt_special_timer: float = 0.0


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
