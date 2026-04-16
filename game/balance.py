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


SHOP_OFFER_POOL = (
    ShopOfferTemplate("repair", "纳米修复", "回复 40 生命", 18),
    ShopOfferTemplate("shield_charge", "护盾电池", "回复 30 护盾", 20),
    ShopOfferTemplate("shield_core", "护盾核心", "护盾上限 +10，并回复 14 护盾", 28),
    ShopOfferTemplate("damage", "火力扩容", "武器伤害 +12%", 30),
    ShopOfferTemplate("rapid", "枪机校准", "射击冷却 -6%", 26),
    ShopOfferTemplate("accuracy", "瞄具微调", "子弹偏移 -18%，准度提升", 28),
    ShopOfferTemplate("crit_rate", "脆弱扫描", "暴击率 +6%", 30),
    ShopOfferTemplate("crit_damage", "高压穿芯", "暴击伤害 +18%", 32),
    ShopOfferTemplate("speed", "动力靴组", "移动速度 +16", 24),
    ShopOfferTemplate("magnet", "磁环模组", "拾取范围 +16", 22),
    ShopOfferTemplate("enemy_bullet_slow", "迟滞电场", "敌方子弹速度 -12%", 28),
    ShopOfferTemplate("credit_boost", "回收协议", "晶片获取 +25%", 30),
    ShopOfferTemplate("ricochet", "折射弹仓", "攻击获得 1 次反射", 34),
)


def enemy_scaling(room_index: int, floor_index: int) -> tuple[float, float, float]:
    difficulty = max(1, room_index)
    floor_bonus = max(0, floor_index - 1)
    hp_scale = 1.0 + difficulty * 0.07 + floor_bonus * 0.12
    damage_scale = 1.0 + difficulty * 0.04 + floor_bonus * 0.10
    speed_bonus = difficulty * 1.5 + floor_bonus * 4.0
    return hp_scale, damage_scale, speed_bonus


def scale_shop_cost(base_cost: int, floor_index: int, difficulty: int) -> int:
    floor_markup = max(0, floor_index - 1) * 0.16
    difficulty_markup = max(0, difficulty - 1) * 0.02
    return int(math.ceil(base_cost * (1.0 + floor_markup + difficulty_markup)))


def enemy_credit_drop(room_index: int, floor_index: int, kind: str) -> int:
    amount = 4 + room_index // 4 + max(0, floor_index - 1)
    if kind == "elite":
        amount += 2
    elif kind == "boss":
        amount += 4
    return amount


def obstacle_credit_drop(room_index: int, floor_index: int) -> int:
    return 4 + room_index // 5 + max(0, floor_index - 1)


def reward_credit_drop(floor_index: int, reward_type: str) -> int:
    if reward_type == "boss":
        return 18 + max(0, floor_index - 1) * 4
    return 10 + max(0, floor_index - 1) * 3


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
