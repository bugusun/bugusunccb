from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Upgrade:
    key: str
    name: str
    description: str


@dataclass(frozen=True)
class StageOption:
    key: str
    name: str
    description: str
    start_room: int


@dataclass(frozen=True)
class CharacterOption:
    key: str
    name: str
    description: str
    passive: str


@dataclass(frozen=True)
class WeaponOption:
    key: str
    name: str
    description: str
    passive: str


@dataclass(frozen=True)
class SupplyOption:
    key: str
    name: str
    description: str


UPGRADES = (
    Upgrade("damage", "重型弹匣", "武器伤害 +12%"),
    Upgrade("rapid", "热能枪机", "射击冷却 -6%"),
    Upgrade("accuracy", "精密校准", "子弹偏移 -18%，准度提升"),
    Upgrade("crit_rate", "弹道解析", "暴击率 +6%"),
    Upgrade("crit_damage", "破甲核心", "暴击伤害 +18%"),
    Upgrade("speed", "轻翼战靴", "移动速度 +16"),
    Upgrade("max_hp", "强化核心", "最大生命 +12，并回复 12 生命"),
    Upgrade("heal", "战地修补", "立即回复 22 生命"),
    Upgrade("shield_core", "相位护盾", "护盾上限 +10，并回复 14 护盾"),
    Upgrade("pierce", "穿甲弹头", "投射物穿透 +1"),
    Upgrade("multishot", "双生锯齿", "追加 1 组侧射"),
    Upgrade("magnet", "废料磁环", "拾取吸附范围 +16"),
    Upgrade("pulse", "电弧反应堆", "脉冲伤害 +8，冷却 -6%"),
    Upgrade("dash", "矢量驱动", "冲刺冷却 -7%，移速 +8"),
    Upgrade("enemy_bullet_slow", "迟滞电场", "敌方子弹速度 -12%"),
    Upgrade("credit_boost", "回收协议", "晶片获取 +25%"),
    Upgrade("ricochet", "折射弹仓", "攻击获得 1 次反射"),
    Upgrade("pulse_radius", "广域脉冲", "脉冲范围 +22"),
)
UPGRADE_KEYS = {upgrade.key for upgrade in UPGRADES}

STAGES = (
    StageOption("stage_1", "第一关", "标准开局，适合熟悉玩法", 1),
    StageOption("stage_2", "第二关", "中层开局，敌人更强更密集", 3),
    StageOption("stage_3", "第三关", "高压开局，精英敌人更多", 6),
)

CHARACTERS = (
    CharacterOption("vanguard", "先锋机体", "耐久偏强的前线框架", "生命与护盾更厚，适合稳扎稳打"),
    CharacterOption("ranger", "游骑机体", "高机动侦察框架", "移速、冲刺与吸附范围更强"),
    CharacterOption("engineer", "工蜂机体", "偏技能与资源调度的支援框架", "脉冲恢复更快，开局自带晶片"),
)

WEAPONS = (
    WeaponOption("rifle", "制式步枪", "折中稳定的标准武器", "中等射速、中等伤害与中等准度"),
    WeaponOption("scatter", "蜂群机枪", "高速压制型武器", "射速极高，但单发伤害和准度更低"),
    WeaponOption("rail", "猎隼狙击枪", "高伤高准的远距武器", "射速慢，但单发伤害、准度和暴击都更强"),
    WeaponOption("laser_burst", "脉冲激光", "低伤高频的贯穿激光", "瞬时命中整条直线，可反射并穿透可破坏障碍"),
    WeaponOption("laser_lance", "棱镜重激光", "高伤低频的聚焦激光", "单次命中更重，开火时会产生轻微后坐力"),
)

SUPPLY_OPTIONS = (
    SupplyOption("repair", "应急维修", "回复 40 生命"),
    SupplyOption("overclock", "火力过载", "伤害 +4，并重置脉冲冷却"),
    SupplyOption("charge", "电容充能", "重置冲刺与脉冲冷却"),
)

TITLE_INTRO = (
    "逐房推进，清敌升级，击败首领进入下一层。",
    "商店、宝箱、精英与首领房已经接入完整流程。",
    "新增双系激光、暴击、准度升级与特殊危险桶。",
)

TITLE_SKILLS = (
    "左键：射击",
    "Space：冲刺",
    "Q：脉冲",
    "E：交互",
)

TITLE_PANEL_INFO = {
    "main": ("部署总览", ""),
    "stage": ("关卡选择", "选择起始压力和开局进度"),
    "character": ("角色选择", "选择机体倾向与基础被动"),
    "weapon": ("武器选择", "选择开局武器与火力结构"),
}
