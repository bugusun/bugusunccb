from __future__ import annotations

from dataclasses import dataclass

from . import config


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
    skill_key: str


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


@dataclass(frozen=True)
class UpgradeWeaponRule:
    required_weapon_keys: frozenset[str] = frozenset()
    required_weapon_tags: frozenset[str] = frozenset()
    required_character_keys: frozenset[str] = frozenset()
    required_skill_keys: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CharacterSkill:
    key: str
    name: str
    description: str
    cooldown: float
    hud_label: str


@dataclass(frozen=True)
class CharacterProfile:
    hp_bonus: float = 0.0
    shield_bonus: float = 0.0
    speed_bonus: float = 0.0
    pickup_radius_bonus: float = 0.0
    dash_distance_bonus: float = 0.0
    dash_cooldown_mult: float = 1.0
    pulse_damage_bonus: float = 0.0
    pulse_cooldown_mult: float = 1.0
    starting_credits: int = 0
    skill_key: str = "pulse"


UPGRADES = (
    Upgrade("damage", "重型弹匣", "武器伤害 +12%"),
    Upgrade("rapid", "热能枪机", "射击冷却 -6%"),
    Upgrade("accuracy", "精密校准", "弹道更稳，偏移 -18%"),
    Upgrade("crit_rate", "弹道解析", "暴击率 +6%"),
    Upgrade("crit_damage", "破甲核心", "暴击伤害 +18%"),
    Upgrade("speed", "轻翼战靴", "移动速度 +18"),
    Upgrade("max_hp", "强化核心", "最大生命 +12，并回复 12 生命"),
    Upgrade("heal", "战地修补", "立即回复 22 生命"),
    Upgrade("shield_core", "相位护盾", "护盾上限 +10，并回复 14 护盾"),
    Upgrade("pierce", "穿甲弹头", "投射物穿透 +1"),
    Upgrade("multishot", "侧翼弹夹", "每次只追加 1 条额外弹道"),
    Upgrade("shotgun_range", "加长枪膛", "飞行距离增加，扩散略收束"),
    Upgrade("rocket_blast", "广域装药", "火箭炮：爆炸范围 +18"),
    Upgrade("basketball_training", "篮球实习生", "坤坤：篮球速度 +5%，伤害 +2"),
    Upgrade("what_can_i_say", "what can i say", "曼巴重击伤害 +4，眩晕 +0.12 秒"),
    Upgrade("magnet", "废料磁环", "拾取吸附范围 +16"),
    Upgrade("pulse", "电弧反应堆", "脉冲伤害 +8，冷却 -6%"),
    Upgrade("dash", "矢量驱动", "冲刺冷却 -7%，移速 +8"),
    Upgrade("enemy_bullet_slow", "迟滞电场", "敌方子弹速度 -12%"),
    Upgrade("credit_boost", "回收协议", "晶片获取 +25%"),
    Upgrade("ricochet", "折射弹仓", "普枪 +1 反射；激光最多 3 次"),
    Upgrade("pulse_radius", "广域脉冲", "脉冲范围 +22"),
)
UPGRADE_KEYS = {upgrade.key for upgrade in UPGRADES}
WEAPON_TAGS = {
    "rifle": frozenset({"projectile", "ballistic", "bullet_weapon"}),
    "scatter": frozenset({"projectile", "ballistic", "rapid_fire", "bullet_weapon"}),
    "shotgun": frozenset({"projectile", "ballistic", "shotgun", "bullet_weapon"}),
    "rail": frozenset({"projectile", "ballistic", "precision", "bullet_weapon"}),
    "rocket": frozenset({"projectile", "explosive", "heavy"}),
    "laser_burst": frozenset({"laser", "beam", "rapid_fire"}),
    "laser_lance": frozenset({"laser", "beam", "heavy"}),
}
WEAPON_EXCLUSIVE_UPGRADES = {
    "shotgun_range": {"shotgun"},
    "rocket_blast": {"rocket"},
}
UPGRADE_WEAPON_RULES = {
    "accuracy": UpgradeWeaponRule(required_weapon_tags=frozenset({"bullet_weapon"})),
    "pierce": UpgradeWeaponRule(required_weapon_tags=frozenset({"bullet_weapon"})),
    "multishot": UpgradeWeaponRule(required_weapon_tags=frozenset({"bullet_weapon"})),
    "ricochet": UpgradeWeaponRule(required_weapon_tags=frozenset({"bullet_weapon", "laser"})),
    "shotgun_range": UpgradeWeaponRule(required_weapon_tags=frozenset({"shotgun"})),
    "basketball_training": UpgradeWeaponRule(
        required_character_keys=frozenset({"kunkun"}),
        required_skill_keys=frozenset({"basketball"}),
    ),
    "what_can_i_say": UpgradeWeaponRule(
        required_character_keys=frozenset({"mamba"}),
        required_skill_keys=frozenset({"mamba_smash"}),
    ),
    "pulse": UpgradeWeaponRule(required_skill_keys=frozenset({"pulse"})),
    "pulse_radius": UpgradeWeaponRule(required_skill_keys=frozenset({"pulse"})),
}

STAGES = (
    StageOption("stage_1", "第一关", "标准开局", 1),
    StageOption("stage_2", "第二关", "中层开局", 3),
    StageOption("stage_3", "第三关", "高压开局", 6),
)

CHARACTERS = (
    CharacterOption("vanguard", "先锋机体", "更厚实的前线框架", "生命与护盾更厚，适合正面推进", "pulse"),
    CharacterOption("mamba", "曼巴奥特", "黄黑突进机体", "移速与冲刺切入更强，擅长贴身重击", "mamba_smash"),
    CharacterOption("engineer", "工蜂机体", "偏技能与资源调度的支援框架", "脉冲恢复更快，开局自带晶片", "pulse"),
    CharacterOption("kunkun", "坤坤", "均衡型表演机体", "血量、速度与护盾都较均衡", "basketball"),
)

CHARACTER_SKILLS = {
    "pulse": CharacterSkill(
        "pulse",
        "电弧脉冲",
        "Q：释放脉冲，击退周围敌人",
        config.PULSE_COOLDOWN,
        "脉冲",
    ),
    "basketball": CharacterSkill(
        "basketball",
        "弹射篮球",
        "Q：放出无限弹射的篮球，清房后消失",
        config.BASKETBALL_SKILL_COOLDOWN,
        "篮球",
    ),
    "mamba_smash": CharacterSkill(
        "mamba_smash",
        "曼巴重击",
        "Q：短暂蓄势后向前方区域挥出重击，造成伤害、强击飞与眩晕",
        config.MAMBA_SKILL_COOLDOWN,
        "重击",
    ),
}

CHARACTER_PROFILES = {
    "vanguard": CharacterProfile(
        hp_bonus=18,
        shield_bonus=18,
        dash_cooldown_mult=0.96,
        skill_key="pulse",
    ),
    "mamba": CharacterProfile(
        speed_bonus=22,
        dash_distance_bonus=14,
        dash_cooldown_mult=0.93,
        skill_key="mamba_smash",
    ),
    "engineer": CharacterProfile(
        pulse_damage_bonus=8,
        pulse_cooldown_mult=0.88,
        starting_credits=12,
        skill_key="pulse",
    ),
    "kunkun": CharacterProfile(
        skill_key="basketball",
    ),
}

WEAPONS = (
    WeaponOption("rifle", "制式步枪", "均衡稳定的标准火力", "中速、中伤、泛用性最好"),
    WeaponOption("scatter", "蜂群机枪", "高速压制武器", "射速极高，但单发更轻、扩散更大"),
    WeaponOption("shotgun", "废土霰弹枪", "近距爆发武器", "一次喷出多枚弹丸，可强化有效距离"),
    WeaponOption("rail", "猎隼狙击枪", "高伤高准的远距火力", "射速慢，但单发更重，侧弹道会成对增加"),
    WeaponOption("rocket", "铁锤火箭炮", "低频重火力武器", "命中后爆炸并击飞目标，可强化爆炸范围"),
    WeaponOption("laser_burst", "脉冲激光", "低伤高频的贯穿激光", "瞬时命中整条直线"),
    WeaponOption("laser_lance", "棱镜重激光", "高伤低频的聚焦激光", "单次命中更重并带有后坐力"),
)

SUPPLY_OPTIONS = (
    SupplyOption("repair", "应急维修", "回复 40 生命"),
    SupplyOption("overclock", "火力过载", "伤害 +4，并重置技能冷却"),
    SupplyOption("charge", "电容充能", "重置冲刺与技能冷却"),
)

TITLE_INTRO = (
    "逐房推进，清敌升级，然后继续下潜。",
    "商店、宝箱、精英与首领房都已接入。",
    "不同武器会各自过滤专属强化。",
)

TITLE_SKILLS = (
    "左键 射击",
    "Space 冲刺",
    "Q 角色技能",
    "E 交互",
)

TITLE_PANEL_INFO = {
    "main": ("部署总览", ""),
    "stage": ("关卡选择", "选择起始楼层"),
    "character": ("角色选择", "选择机体倾向"),
    "weapon": ("武器选择", "选择开局武器"),
}
