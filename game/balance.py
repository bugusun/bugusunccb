from __future__ import annotations

import math
from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class ShopOfferTemplate:
    key: str
    name: str
    description: str
    base_cost: int


@dataclass(frozen=True)
class HazardProfile:
    hp_scale: float
    radius: float
    damage: float
    ttl: float


@dataclass(frozen=True)
class NukeEventProfile:
    chance: float
    hp: float
    player_damage: float
    enemy_damage: float
    cloud_count: int


SHOP_OFFER_POOL = (
    ShopOfferTemplate("repair", "纳米修复", "回复 40 生命", 18),
    ShopOfferTemplate("shield_charge", "护盾电池", "回复 30 护盾", 20),
    ShopOfferTemplate("shield_core", "护盾核心", "护盾上限 +10，并回复 14 护盾", 28),
    ShopOfferTemplate("damage", "火力扩容", "武器伤害 +12%", 30),
    ShopOfferTemplate("rapid", "枪机校准", "射击冷却 -6%", 26),
    ShopOfferTemplate("accuracy", "瞄具微调", "子弹偏移 -18%，准度提升", 28),
    ShopOfferTemplate("shotgun_range", "加长枪膛", "子弹距离增加，扩散略微收束", 28),
    ShopOfferTemplate("basketball_training", "篮球实习生", "坤坤：篮球速度上升，伤害小幅提高", 28),
    ShopOfferTemplate("what_can_i_say", "what can i say", "曼巴重击伤害与眩晕时间小幅提高", 30),
    ShopOfferTemplate("crit_rate", "脆弱扫描", "暴击率 +6%", 30),
    ShopOfferTemplate("crit_damage", "高压穿芯", "暴击伤害 +18%", 32),
    ShopOfferTemplate("speed", "动力靴组", "移动速度 +18", 24),
    ShopOfferTemplate("magnet", "磁环模组", "拾取范围 +16", 22),
    ShopOfferTemplate("enemy_bullet_slow", "迟滞电场", "敌方子弹速度 -12%", 28),
    ShopOfferTemplate("credit_boost", "回收协议", "晶片获取 +25%", 30),
    ShopOfferTemplate("ricochet", "折射弹仓", "攻击增加 1 次反射", 34),
)

CREDIT_DROP_BASE_MULTIPLIER = 0.70
ENEMY_FLOOR_CREDIT_DROP_STEP = 0.05
ENEMY_FLOOR_CREDIT_DROP_CAP = 0.50


def floor_damage_adjustment(floor_index: int) -> float:
    floor_value = max(1.0, float(floor_index))
    if floor_value <= 3.0:
        t = (floor_value - 1.0) / 2.0
        return -0.30 + 0.20 * t
    if floor_value <= 6.0:
        t = (floor_value - 3.0) / 3.0
        return -0.10 + 0.15 * t
    if floor_value <= 9.0:
        t = (floor_value - 6.0) / 3.0
        return 0.05 + 0.10 * t
    return 0.15


def enemy_scaling(room_index: int, floor_index: int) -> tuple[float, float, float]:
    difficulty = max(1, room_index)
    floor_bonus = max(0, floor_index - 1)
    hp_scale = (1.0 + difficulty * 0.07 + floor_bonus * 0.12) * 1.10
    damage_scale = (
        1.0 + difficulty * 0.04 + floor_bonus * 0.10
    ) * (1.0 + floor_damage_adjustment(floor_index))
    speed_bonus = difficulty * 1.5 + floor_bonus * 4.0
    return hp_scale, damage_scale, speed_bonus


def nuke_event_profile(room_index: int, floor_index: int) -> NukeEventProfile:
    floor_value = max(1, floor_index)
    room_value = max(1, room_index)
    chance = min(0.36, (0.03 + (floor_value - 1) * 0.017) * 2.0)
    hp = 190.0 + room_value * 26.0 + (floor_value - 1) * 18.0
    player_damage = min(92.0, 82.0 + (floor_value - 1) * 1.5)
    enemy_damage = min(176.0, 118.0 + room_value * 5.0 + (floor_value - 1) * 6.0)
    cloud_count = min(7, 3 + floor_value // 2)
    return NukeEventProfile(
        chance=chance,
        hp=hp,
        player_damage=player_damage,
        enemy_damage=enemy_damage,
        cloud_count=cloud_count,
    )


def scale_shop_cost(base_cost: int, floor_index: int, difficulty: int) -> int:
    floor_markup = max(0, floor_index - 1) * 0.22
    difficulty_markup = max(0, difficulty - 1) * 0.03
    return int(math.ceil(base_cost * (1.0 + floor_markup + difficulty_markup)))


def scale_credit_amount(amount: int, multiplier: float) -> int:
    return max(1, int(round(amount * multiplier)))


def enemy_floor_credit_multiplier(floor_index: int) -> float:
    floor_penalty = min(
        ENEMY_FLOOR_CREDIT_DROP_CAP,
        max(0, floor_index - 1) * ENEMY_FLOOR_CREDIT_DROP_STEP,
    )
    return 1.0 - floor_penalty


def enemy_attack_cooldown(kind: str, room_index: int, floor_index: int) -> float:
    floor_bonus = max(0, floor_index - 1)
    if kind == "laser":
        return max(1.5, 2.28 - room_index * 0.03 - floor_bonus * 0.05)
    if kind == "shooter":
        return max(1.18, 2.24 - room_index * 0.028 - floor_bonus * 0.045)
    if kind == "shotgunner":
        return max(1.28, 1.92 - room_index * 0.018 - floor_bonus * 0.04)
    if kind == "elite":
        return max(1.45, 2.15 - room_index * 0.024 - floor_bonus * 0.05)
    if kind == "boss":
        return max(0.82, 1.42 - room_index * 0.02 - floor_bonus * 0.04)
    return 0.0


def enemy_credit_drop(room_index: int, floor_index: int, kind: str) -> int:
    amount = 4 + room_index // 4 + max(0, floor_index - 1)
    if kind in {"toxic_bloater", "reactor_bomber"}:
        amount += 1
    if kind == "elite":
        amount += 2
    elif kind == "boss":
        amount += 4
    multiplier = CREDIT_DROP_BASE_MULTIPLIER * enemy_floor_credit_multiplier(
        floor_index
    )
    return scale_credit_amount(amount, multiplier)


def obstacle_credit_drop(room_index: int, floor_index: int) -> int:
    amount = 4 + room_index // 5 + max(0, floor_index - 1)
    return scale_credit_amount(amount, CREDIT_DROP_BASE_MULTIPLIER)


def reward_credit_drop(floor_index: int, reward_type: str) -> int:
    amount = 10 + max(0, floor_index - 1) * 3
    if reward_type == "boss":
        amount = 18 + max(0, floor_index - 1) * 4
    return scale_credit_amount(amount, CREDIT_DROP_BASE_MULTIPLIER)


def hazard_profile(tag: str, rect: pygame.Rect) -> HazardProfile:
    size = max(rect.width, rect.height)
    area = rect.width * rect.height
    if tag == "reactor":
        hp_scale = 1.0 + min(2.4, area / 1800)
        radius = max(100.0, min(340.0, size * 2.8 + area / 26))
        damage = max(14.0, min(34.0, 12.0 + area / 160))
        return HazardProfile(hp_scale=hp_scale, radius=radius, damage=damage, ttl=0.26)
    if tag == "toxic":
        hp_scale = 1.0 + min(1.8, area / 2200)
        radius = max(72.0, min(260.0, size * 2.3 + area / 34))
        damage = max(4.0, min(10.0, 3.0 + area / 420))
        ttl = max(3.2, min(6.0, 2.8 + area / 1300))
        return HazardProfile(hp_scale=hp_scale, radius=radius, damage=damage, ttl=ttl)
    return HazardProfile(hp_scale=1.0, radius=0.0, damage=0.0, ttl=0.0)
