import math
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game import config
from game.entities import Bullet, Enemy
from game.map_system import RoomObstacle, SPECIAL_TAG_COLORS

ROOT = Path(r"T:/gameV1")
OUT = ROOT / "resources"

pygame.init()
pygame.font.init()
SMALL_FONT = pygame.font.SysFont(
    ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"], 15
)
TINY_FONT = pygame.font.SysFont(
    ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"], 13
)


def ensure_dirs():
    for name in ["characters", "weapons", "bullets", "enemies", "map"]:
        (OUT / name).mkdir(parents=True, exist_ok=True)


def crop_surface(surface: pygame.Surface, pad: int = 2) -> pygame.Surface:
    mask = pygame.mask.from_surface(surface)
    rects = mask.get_bounding_rects()
    if not rects:
        return surface.copy()
    bbox = rects[0].copy()
    for rect in rects[1:]:
        bbox.union_ip(rect)
    bbox.inflate_ip(pad * 2, pad * 2)
    bbox.clamp_ip(surface.get_rect())
    out = pygame.Surface((bbox.width, bbox.height), pygame.SRCALPHA)
    out.blit(surface, (0, 0), bbox)
    return out


def save(surface: pygame.Surface, path: Path, crop: bool = True):
    final = crop_surface(surface) if crop else surface
    pygame.image.save(final, str(path))


def make_surface(size=(256, 256)):
    return pygame.Surface(size, pygame.SRCALPHA)


def draw_actor_face(
    screen: pygame.Surface,
    pos: pygame.Vector2,
    radius: int,
    kind: str,
    *,
    is_boss: bool = False,
) -> None:
    eye_color = (18, 20, 28)
    accent = (240, 244, 255)
    eye_dx = radius * 0.34
    eye_y = pos.y - radius * 0.14
    eye_size = max(2, int(radius * 0.12))

    if kind == "player":
        pygame.draw.circle(
            screen, accent, (int(pos.x - eye_dx), int(eye_y)), eye_size + 1
        )
        pygame.draw.circle(
            screen, accent, (int(pos.x + eye_dx), int(eye_y)), eye_size + 1
        )
        pygame.draw.circle(
            screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size
        )
        pygame.draw.circle(
            screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size
        )
        mouth_rect = pygame.Rect(0, 0, radius, max(8, radius // 2))
        mouth_rect.center = (int(pos.x), int(pos.y + radius * 0.18))
        pygame.draw.arc(screen, eye_color, mouth_rect, 0.15, math.pi - 0.15, 2)
        return

    if is_boss or kind == "boss":
        eye_w = radius * 0.48
        eye_h = radius * 0.30
        left_eye = pygame.Rect(0, 0, int(eye_w), int(eye_h))
        right_eye = pygame.Rect(0, 0, int(eye_w), int(eye_h))
        left_eye.center = (int(pos.x - eye_dx * 1.08), int(eye_y))
        right_eye.center = (int(pos.x + eye_dx * 1.08), int(eye_y))
        pygame.draw.arc(screen, eye_color, left_eye, math.pi, math.tau, 3)
        pygame.draw.arc(screen, eye_color, right_eye, math.pi, math.tau, 3)
        pygame.draw.line(
            screen,
            eye_color,
            (left_eye.left - 2, left_eye.top + 2),
            (left_eye.right + 2, left_eye.top - 4),
            3,
        )
        pygame.draw.line(
            screen,
            eye_color,
            (right_eye.left - 2, right_eye.top - 4),
            (right_eye.right + 2, right_eye.top + 2),
            3,
        )
        mouth_rect = pygame.Rect(0, 0, int(radius * 0.92), max(10, int(radius * 0.42)))
        mouth_rect.center = (int(pos.x), int(pos.y + radius * 0.34))
        pygame.draw.arc(
            screen, eye_color, mouth_rect, math.pi + 0.25, math.tau - 0.25, 3
        )
        return

    if kind == "toxic_bloater":
        pygame.draw.circle(
            screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size
        )
        pygame.draw.circle(
            screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size
        )
        mouth_rect = pygame.Rect(0, 0, int(radius * 0.64), max(8, int(radius * 0.28)))
        mouth_rect.center = (int(pos.x), int(pos.y + radius * 0.24))
        pygame.draw.arc(screen, eye_color, mouth_rect, 0.25, math.pi - 0.25, 2)
        pygame.draw.circle(
            screen,
            accent,
            (int(pos.x), int(pos.y + radius * 0.42)),
            max(2, eye_size - 1),
            1,
        )
        return

    if kind == "reactor_bomber":
        core = pygame.Rect(0, 0, max(10, int(radius * 0.8)), max(10, int(radius * 0.8)))
        core.center = (int(pos.x), int(pos.y + radius * 0.05))
        pygame.draw.rect(screen, eye_color, core, 2, border_radius=4)
        pygame.draw.line(
            screen, eye_color, (core.left + 2, core.top + 2), (core.right - 2, core.bottom - 2), 2
        )
        pygame.draw.line(
            screen, eye_color, (core.right - 2, core.top + 2), (core.left + 2, core.bottom - 2), 2
        )
        pygame.draw.line(
            screen,
            eye_color,
            (int(pos.x - radius * 0.26), int(pos.y - radius * 0.28)),
            (int(pos.x + radius * 0.26), int(pos.y - radius * 0.28)),
            2,
        )
        return

    if kind in {"shooter", "shotgunner"}:
        pygame.draw.circle(
            screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size
        )
        pygame.draw.circle(
            screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size
        )
        mouth_radius = max(2, eye_size - 1)
        if kind == "shotgunner":
            pygame.draw.line(
                screen,
                eye_color,
                (int(pos.x - mouth_radius * 1.5), int(pos.y + radius * 0.20)),
                (int(pos.x + mouth_radius * 1.5), int(pos.y + radius * 0.20)),
                2,
            )
        else:
            pygame.draw.circle(
                screen, eye_color, (int(pos.x), int(pos.y + radius * 0.20)), mouth_radius, 1
            )
        return

    if kind == "laser":
        left_eye = (int(pos.x - eye_dx), int(eye_y))
        right_eye = (int(pos.x + eye_dx), int(eye_y))
        pygame.draw.line(
            screen, eye_color, (left_eye[0] - eye_size, left_eye[1]), (left_eye[0] + eye_size, left_eye[1]), 3
        )
        pygame.draw.line(
            screen, eye_color, (right_eye[0] - eye_size, right_eye[1]), (right_eye[0] + eye_size, right_eye[1]), 3
        )
        pygame.draw.line(
            screen,
            eye_color,
            (int(pos.x - radius * 0.18), int(pos.y + radius * 0.24)),
            (int(pos.x + radius * 0.18), int(pos.y + radius * 0.24)),
            2,
        )
        return

    if kind in {"charger", "elite"}:
        pygame.draw.line(
            screen,
            eye_color,
            (int(pos.x - eye_dx - eye_size), int(eye_y - 2)),
            (int(pos.x - eye_dx + eye_size), int(eye_y + 2)),
            3,
        )
        pygame.draw.line(
            screen,
            eye_color,
            (int(pos.x + eye_dx - eye_size), int(eye_y + 2)),
            (int(pos.x + eye_dx + eye_size), int(eye_y - 2)),
            3,
        )
        pygame.draw.arc(
            screen,
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

    pygame.draw.circle(screen, eye_color, (int(pos.x - eye_dx), int(eye_y)), eye_size)
    pygame.draw.circle(screen, eye_color, (int(pos.x + eye_dx), int(eye_y)), eye_size)
    pygame.draw.line(
        screen,
        eye_color,
        (int(pos.x - radius * 0.18), int(pos.y + radius * 0.22)),
        (int(pos.x + radius * 0.18), int(pos.y + radius * 0.22)),
        2,
    )


def draw_character_avatar(character_key: str) -> pygame.Surface:
    surface = make_surface((128, 128))
    pos = pygame.Vector2(64, 64)
    radius = config.PLAYER_RADIUS
    if character_key == "vanguard":
        surface = make_surface((44, 44))
        pos = pygame.Vector2(22, 22)
        radius = config.PLAYER_RADIUS
        outline = (30, 64, 62)
        shell = (84, 198, 166)
        armor = (132, 236, 204)
        glow = config.BULLET_SHOCK_COLOR
        core = (232, 255, 248)
        shoulder = (62, 126, 118)
        pygame.draw.circle(surface, outline, pos, radius + 2)
        pygame.draw.circle(surface, shell, pos, radius)
        torso = pygame.Rect(0, 0, 24, 18)
        torso.center = (22, 25)
        pygame.draw.rect(surface, outline, torso, border_radius=8)
        pygame.draw.rect(surface, shell, torso.inflate(-4, -4), border_radius=7)
        chest = pygame.Rect(0, 0, 12, 10)
        chest.center = (22, 25)
        pygame.draw.rect(surface, armor, chest, border_radius=4)
        pygame.draw.rect(surface, outline, chest, 1, border_radius=4)
        for side in (-1, 1):
            plate = (
                (22 + side * 6, 12),
                (22 + side * 14, 17),
                (22 + side * 10, 25),
                (22 + side * 3, 20),
            )
            pygame.draw.polygon(surface, shoulder, plate)
            pygame.draw.polygon(surface, outline, plate, 1)
        visor = pygame.Rect(0, 0, 22, 9)
        visor.center = (22, 18)
        pygame.draw.ellipse(surface, outline, visor)
        pygame.draw.ellipse(surface, (28, 86, 88), visor.inflate(-2, -2))
        pygame.draw.line(surface, core, (14, 18), (30, 18), 2)
        pygame.draw.arc(
            surface,
            glow,
            pygame.Rect(11, 7, 22, 14),
            math.pi * 1.10,
            math.pi * 1.90,
            2,
        )
        pygame.draw.circle(surface, core, (22, 25), 3)
        pygame.draw.circle(surface, glow, (22, 25), 5, 1)
        pygame.draw.line(surface, glow, (22, 21), (22, 15), 1)
        return surface
    if character_key == "kunkun":
        outline = (46, 52, 70)
        body_color = config.KUNKUN_BODY_COLOR
        inner_radius = max(4, radius - 2)
        pygame.draw.circle(surface, outline, pos, radius)
        pygame.draw.circle(surface, body_color, pos, inner_radius)
        overall_rect = pygame.Rect(
            int(pos.x - inner_radius + 1),
            int(pos.y - radius * 0.04),
            int(inner_radius * 2 - 2),
            int(inner_radius * 1.06),
        )
        pygame.draw.ellipse(surface, config.KUNKUN_OVERALL_COLOR, overall_rect)
        bib = pygame.Rect(0, 0, int(radius * 1.08), max(10, int(radius * 0.82)))
        bib.center = (int(pos.x), int(pos.y + radius * 0.26))
        pygame.draw.rect(surface, config.KUNKUN_OVERALL_HILITE, bib, border_radius=6)
        pygame.draw.rect(surface, outline, bib, 2, border_radius=6)
        strap_width = max(4, int(radius * 0.24))
        left_top = (int(pos.x - radius * 0.54), int(pos.y - radius * 0.34))
        left_bottom = (int(pos.x - radius * 0.18), int(pos.y + radius * 0.16))
        right_top = (int(pos.x + radius * 0.54), int(pos.y - radius * 0.34))
        right_bottom = (int(pos.x + radius * 0.18), int(pos.y + radius * 0.16))
        pygame.draw.line(surface, config.KUNKUN_OVERALL_COLOR, left_top, left_bottom, strap_width)
        pygame.draw.line(surface, config.KUNKUN_OVERALL_COLOR, right_top, right_bottom, strap_width)
        pygame.draw.circle(surface, outline, left_bottom, 2)
        pygame.draw.circle(surface, outline, right_bottom, 2)
        draw_actor_face(surface, pos + pygame.Vector2(0, 1), radius, "player")
        hair_cap = (
            (int(pos.x - radius * 0.86), int(pos.y - radius * 0.10)),
            (int(pos.x - radius * 0.62), int(pos.y - radius * 0.78)),
            (int(pos.x - radius * 0.10), int(pos.y - radius * 1.02)),
            (int(pos.x), int(pos.y - radius * 0.84)),
            (int(pos.x + radius * 0.10), int(pos.y - radius * 1.02)),
            (int(pos.x + radius * 0.62), int(pos.y - radius * 0.78)),
            (int(pos.x + radius * 0.86), int(pos.y - radius * 0.10)),
        )
        left_bang = (
            (int(pos.x - radius * 0.10), int(pos.y - radius * 0.86)),
            (int(pos.x - radius * 0.50), int(pos.y - radius * 0.36)),
            (int(pos.x - radius * 0.10), int(pos.y - radius * 0.08)),
        )
        right_bang = (
            (int(pos.x + radius * 0.10), int(pos.y - radius * 0.86)),
            (int(pos.x + radius * 0.50), int(pos.y - radius * 0.36)),
            (int(pos.x + radius * 0.10), int(pos.y - radius * 0.08)),
        )
        pygame.draw.polygon(surface, config.KUNKUN_HAIR_SHADOW, hair_cap)
        pygame.draw.polygon(surface, config.KUNKUN_HAIR_COLOR, left_bang)
        pygame.draw.polygon(surface, config.KUNKUN_HAIR_COLOR, right_bang)
        shine_rect = pygame.Rect(0, 0, int(radius * 0.92), int(radius * 0.58))
        shine_rect.center = (int(pos.x), int(pos.y - radius * 0.62))
        pygame.draw.arc(surface, (248, 250, 255), shine_rect, math.pi * 1.08, math.pi * 1.92, 2)
        pygame.draw.line(surface, outline, (int(pos.x), int(pos.y - radius * 0.92)), (int(pos.x), int(pos.y - radius * 0.24)), 1)
        return surface
    outline_color = config.MAMBA_OUTLINE_COLOR
    upper_color = config.MAMBA_UPPER_COLOR
    lower_color = config.MAMBA_JERSEY_COLOR
    inner_radius = max(4, radius - 3)
    pygame.draw.circle(surface, outline_color, pos, radius)
    pygame.draw.circle(surface, lower_color, pos, inner_radius)
    upper_rect = pygame.Rect(
        int(pos.x - inner_radius),
        int(pos.y - inner_radius - radius * 0.06),
        int(inner_radius * 2),
        int(inner_radius * 0.82),
    )
    pygame.draw.ellipse(surface, upper_color, upper_rect)
    split_y = int(pos.y - radius * 0.18)
    pygame.draw.line(surface, outline_color, (int(pos.x - inner_radius + 2), split_y), (int(pos.x + inner_radius - 2), split_y), 2)
    visor = pygame.Rect(0, 0, int(radius * 1.18), max(8, int(radius * 0.62)))
    visor.center = (int(pos.x), int(pos.y - radius * 0.10))
    pygame.draw.ellipse(surface, outline_color, visor)
    pygame.draw.ellipse(surface, config.MAMBA_GLOW_COLOR, visor.inflate(-6, -4), 1)
    shoulder = (
        (int(pos.x - radius * 0.78), int(pos.y - radius * 0.10)),
        (int(pos.x - radius * 0.22), int(pos.y - radius * 0.52)),
        (int(pos.x + radius * 0.24), int(pos.y - radius * 0.20)),
        (int(pos.x + radius * 0.04), int(pos.y + radius * 0.02)),
        (int(pos.x - radius * 0.52), int(pos.y + radius * 0.04)),
    )
    pygame.draw.polygon(surface, config.MAMBA_TRIM_COLOR, shoulder)
    pygame.draw.circle(surface, outline_color, (int(pos.x - radius * 0.60), int(pos.y - radius * 0.08)), 2)
    pygame.draw.circle(surface, outline_color, (int(pos.x + radius * 0.60), int(pos.y - radius * 0.08)), 2)
    number = TINY_FONT.render("24", True, (248, 248, 250))
    number_rect = number.get_rect(center=(int(pos.x), int(pos.y + radius * 0.34)))
    surface.blit(number, number_rect)
    return surface


def draw_weapon(key: str) -> pygame.Surface:
    surface = make_surface((96, 48))
    outline = (27, 31, 40)
    metal_dark = (70, 78, 94)
    metal = (116, 126, 144)
    metal_light = (214, 222, 236)
    grip = (90, 66, 50)
    grip_shadow = (60, 42, 30)
    wood = (132, 95, 62)
    wood_light = (184, 142, 96)
    cyan_core = config.LASER_LIGHT_COLOR
    gold_core = config.LASER_HEAVY_COLOR

    def rect(
        fill: tuple[int, int, int],
        x: int,
        y: int,
        w: int,
        h: int,
        *,
        border=outline,
    ) -> pygame.Rect:
        r = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, fill, r)
        if border is not None:
            pygame.draw.rect(surface, border, r, 1)
        return r

    def poly(
        fill: tuple[int, int, int],
        points,
        *,
        border=outline,
    ) -> None:
        pygame.draw.polygon(surface, fill, points)
        if border is not None:
            pygame.draw.polygon(surface, border, points, 1)

    def line(color: tuple[int, int, int], start: tuple[int, int], end: tuple[int, int], width: int = 1) -> None:
        pygame.draw.line(surface, color, start, end, width)

    def dot(color: tuple[int, int, int], x: int, y: int) -> None:
        surface.set_at((x, y), color)

    def common_grip(x: int, y: int, *, tall: bool = False) -> None:
        grip_pts = (
            (x, y),
            (x + 3, y),
            (x + 1, y + (8 if tall else 7)),
            (x - 2, y + (7 if tall else 6)),
        )
        poly(grip, grip_pts)
        line(grip_shadow, (x, y + 1), (x - 1, y + (6 if tall else 5)))
        line(metal_light, (x + 2, y + 1), (x + 1, y + (5 if tall else 4)))

    def trigger_guard(x: int, y: int) -> None:
        line(outline, (x, y), (x + 3, y))
        line(outline, (x, y), (x, y + 2))
        line(outline, (x + 3, y), (x + 3, y + 2))

    if key == "rifle":
        rect(metal_dark, 10, 17, 8, 6)
        rect(metal, 17, 15, 12, 8)
        rect(metal_dark, 29, 17, 12, 4)
        rect(metal_light, 41, 17, 3, 4)
        rect(metal_light, 21, 14, 6, 2)
        line(config.BULLET_COLOR, (19, 18), (27, 18), 1)
        line(metal_light, (18, 16), (27, 16), 1)
        poly(grip, ((22, 23), (26, 23), (24, 31), (20, 29)))
        line(grip_shadow, (24, 24), (22, 29))
        common_grip(18, 22)
        trigger_guard(19, 22)
    elif key == "scatter":
        rect(metal_dark, 10, 17, 7, 6)
        rect((136, 118, 94), 16, 15, 11, 8)
        rect(metal, 27, 15, 9, 8)
        rect(metal_light, 36, 16, 4, 2)
        rect(metal_light, 36, 20, 4, 2)
        rect(outline, 19, 14, 6, 2, border=None)
        line(config.BULLET_COLOR, (18, 18), (25, 18), 1)
        dot(outline, 30, 17)
        dot(outline, 32, 17)
        dot(outline, 30, 20)
        dot(outline, 32, 20)
        rect(grip, 21, 23, 4, 5)
        line(grip_shadow, (24, 24), (23, 27))
        common_grip(17, 22)
        trigger_guard(18, 22)
    elif key == "shotgun":
        rect(grip_shadow, 10, 16, 10, 7)
        rect(wood, 12, 17, 7, 5)
        rect(metal, 20, 15, 10, 8)
        rect(metal_dark, 29, 16, 15, 2)
        rect(metal_dark, 28, 20, 14, 2)
        rect(wood_light, 24, 18, 7, 5)
        line(outline, (24, 20), (30, 20), 1)
        rect(metal_light, 44, 16, 2, 2)
        rect(metal_light, 42, 20, 2, 2)
        common_grip(18, 22, tall=True)
        trigger_guard(19, 22)
    elif key == "rail":
        rect(metal_dark, 10, 17, 8, 6)
        rect((94, 106, 126), 18, 15, 11, 7)
        rect(metal_dark, 29, 17, 16, 2)
        rect(metal_light, 20, 13, 11, 2)
        rect(metal_light, 24, 20, 4, 2)
        line(config.BULLET_COLOR, (30, 18), (44, 18), 1)
        line(cyan_core, (31, 19), (43, 19), 1)
        dot(metal_light, 42, 17)
        common_grip(18, 21)
        trigger_guard(19, 21)
    elif key == "rocket":
        rect(metal_dark, 10, 17, 8, 6)
        rect(config.ROCKET_COLOR, 18, 14, 22, 10)
        rect((138, 86, 54), 20, 16, 17, 6)
        rect((232, 186, 132), 38, 15, 5, 8)
        pygame.draw.circle(surface, config.ROCKET_CORE_COLOR, (40, 19), 2)
        rect(metal_light, 24, 13, 7, 2)
        line((255, 214, 170), (21, 16), (36, 16), 1)
        common_grip(19, 23, tall=True)
        trigger_guard(20, 23)
    elif key == "laser_burst":
        rect(metal_dark, 10, 17, 7, 6)
        rect((78, 98, 118), 17, 15, 11, 8)
        rect((78, 160, 164), 28, 14, 6, 10)
        rect(outline, 34, 17, 9, 4, border=None)
        rect(cyan_core, 42, 16, 3, 2)
        rect(cyan_core, 42, 20, 3, 2)
        line(cyan_core, (19, 18), (26, 18), 1)
        line(metal_light, (29, 16), (32, 16), 1)
        line(metal_light, (29, 21), (32, 21), 1)
        dot(cyan_core, 31, 19)
        common_grip(18, 22)
        trigger_guard(19, 22)
    elif key == "laser_lance":
        rect(metal_dark, 10, 17, 7, 6)
        rect((168, 126, 74), 17, 14, 8, 10)
        rect((90, 86, 100), 25, 15, 9, 8)
        poly(
            (188, 152, 84),
            ((34, 15), (43, 17), (43, 21), (34, 23)),
        )
        line(gold_core, (27, 18), (41, 18), 1)
        line((255, 238, 180), (27, 19), (40, 19), 1)
        rect(metal_light, 26, 13, 6, 2)
        dot(gold_core, 41, 19)
        common_grip(18, 22, tall=True)
        trigger_guard(19, 22)
    else:
        rect(metal_dark, 10, 17, 8, 6)
        rect(metal, 17, 15, 12, 8)
        rect(metal_dark, 29, 17, 12, 4)
        line(config.BULLET_COLOR, (19, 18), (27, 18), 1)
        common_grip(18, 22)
        trigger_guard(19, 22)

    return surface


def draw_bullet_sprite(bullet: Bullet) -> pygame.Surface:
    if bullet.style == "rail":
        surface = make_surface((44, 20))
        center = pygame.Vector2(22, 10)
        body = pygame.Rect(0, 0, 18, 6)
        body.center = (20, 10)
        jacket = (196, 148, 92)
        tip = (244, 214, 150)
        casing = (132, 98, 68)
        outline = (82, 58, 42)
        pygame.draw.rect(surface, outline, body, border_radius=3)
        pygame.draw.rect(surface, jacket, body.inflate(-2, -2), border_radius=3)
        pygame.draw.polygon(
            surface,
            tip,
            ((28, 7), (38, 10), (28, 13)),
        )
        pygame.draw.polygon(
            surface,
            outline,
            ((28, 7), (38, 10), (28, 13)),
            1,
        )
        tail = pygame.Rect(0, 0, 7, 8)
        tail.center = (11, 10)
        pygame.draw.rect(surface, outline, tail, border_radius=2)
        pygame.draw.rect(surface, casing, tail.inflate(-2, -2), border_radius=2)
        pygame.draw.line(surface, (255, 232, 180), (16, 8), (28, 8), 1)
        pygame.draw.line(surface, (255, 220, 150), (13, 10), (27, 10), 1)
        pygame.draw.line(surface, (150, 116, 82), (10, 13), (28, 13), 1)
        pygame.draw.circle(surface, (255, 248, 224), center, 2, 1)
        return surface
    size = max(64, bullet.radius * 8)
    surface = make_surface((size, size))
    bullet.pos = pygame.Vector2(size // 2, size // 2)
    radius = bullet.radius
    if bullet.style == "rocket" and bullet.velocity.length_squared() > 0:
        heading = bullet.velocity.normalize()
        tail = bullet.pos - heading * (radius * 2.1)
        wing = pygame.Vector2(-heading.y, heading.x) * max(3, radius * 0.75)
        nose = bullet.pos + heading * (radius * 1.4)
        pygame.draw.polygon(surface, bullet.color, (nose, tail + wing, tail - wing))
        pygame.draw.circle(surface, config.ROCKET_CORE_COLOR, bullet.pos, max(2, radius - 3))
        exhaust = tail - heading * 4
        pygame.draw.circle(surface, config.ROCKET_EXPLOSION_COLOR, exhaust, max(2, radius // 2 + 1))
    elif bullet.style == "shotgun_pellet" and bullet.velocity.length_squared() > 0:
        heading = bullet.velocity.normalize()
        tail = bullet.pos - heading * max(5, radius * 2.6)
        pygame.draw.line(surface, config.SHOTGUN_TRAIL_COLOR, tail, bullet.pos, max(2, radius))
        pygame.draw.circle(surface, bullet.color, bullet.pos, radius)
    elif bullet.style == "basketball":
        center = (int(bullet.pos.x), int(bullet.pos.y))
        pygame.draw.circle(surface, bullet.color, center, radius)
        pygame.draw.circle(surface, config.BASKETBALL_LINE_COLOR, center, radius, 2)
        pygame.draw.line(surface, config.BASKETBALL_LINE_COLOR, (center[0] - radius + 2, center[1]), (center[0] + radius - 2, center[1]), 2)
        left_arc = pygame.Rect(center[0] - radius, center[1] - radius, radius + 4, radius * 2)
        right_arc = pygame.Rect(center[0] - 4, center[1] - radius, radius + 4, radius * 2)
        pygame.draw.arc(surface, config.BASKETBALL_LINE_COLOR, left_arc, -math.pi / 2, math.pi / 2, 2)
        pygame.draw.arc(surface, config.BASKETBALL_LINE_COLOR, right_arc, math.pi / 2, math.pi * 1.5, 2)
    else:
        pygame.draw.circle(surface, bullet.color, bullet.pos, radius)
    return surface


def draw_enemy_avatar(enemy: Enemy) -> pygame.Surface:
    surface = make_surface((220, 220))
    enemy = Enemy(**{**enemy.__dict__})
    enemy.pos = pygame.Vector2(110, 110)
    if enemy.kind == "boss" and enemy.variant == "challenge":
        pos = enemy.pos; radius = enemy.radius
        outline = (54, 18, 18); shell = (104, 28, 28); plate = (152, 54, 54); core = config.CHALLENGE_ROOM_COLOR; glow = (255, 214, 214)
        pygame.draw.circle(surface, outline, pos, radius + 5); pygame.draw.circle(surface, shell, pos, radius + 1)
        for direction in (pygame.Vector2(0, -1), pygame.Vector2(1, 0), pygame.Vector2(0, 1), pygame.Vector2(-1, 0)):
            tangent = pygame.Vector2(-direction.y, direction.x); base = pos + direction * (radius * 0.52); tip = pos + direction * (radius + 13); left = base + tangent * (radius * 0.34); right = base - tangent * (radius * 0.34)
            pygame.draw.polygon(surface, plate, (tip, left, right)); pygame.draw.polygon(surface, outline, (tip, left, right), 2)
        inner_rect = pygame.Rect(0, 0, int(radius * 1.78), int(radius * 1.52)); inner_rect.center = (int(pos.x), int(pos.y))
        pygame.draw.ellipse(surface, core, inner_rect); pygame.draw.ellipse(surface, glow, inner_rect.inflate(-10, -16), 2)
        brow_y = pos.y - radius * 0.24; eye_dx = radius * 0.44
        for direction in (-1, 1):
            eye = pygame.Rect(0, 0, int(radius * 0.46), int(radius * 0.24)); eye.center = (int(pos.x + direction * eye_dx), int(brow_y))
            pygame.draw.line(surface, glow, (eye.left, eye.centery + direction), (eye.right, eye.centery - direction * 2), 4); pygame.draw.line(surface, outline, (eye.left, eye.centery + direction), (eye.right, eye.centery - direction * 2), 2)
        core_rect = pygame.Rect(0, 0, int(radius * 0.82), int(radius * 0.64)); core_rect.center = (int(pos.x), int(pos.y + radius * 0.12))
        pygame.draw.ellipse(surface, outline, core_rect); pygame.draw.ellipse(surface, config.ENEMY_LASER_LOCK_COLOR, core_rect.inflate(-8, -6))
        pygame.draw.arc(surface, outline, pygame.Rect(int(pos.x - radius * 0.42), int(pos.y + radius * 0.12), int(radius * 0.84), max(10, int(radius * 0.40))), 0.20, math.pi - 0.20, 3)
        return surface
    if enemy.kind == "boss":
        pos = enemy.pos; radius = enemy.radius
        outline = (54, 18, 18); shell = (112, 34, 34); armor = (170, 76, 76); trim = (238, 198, 132); glow = (255, 236, 184); phase_glow = config.BOSS_BAR_PHASE if enemy.phase >= 2 else trim
        pygame.draw.circle(surface, outline, pos, radius + 5); pygame.draw.circle(surface, shell, pos, radius + 1)
        chassis = pygame.Rect(0, 0, int(radius * 1.78), int(radius * 1.50)); chassis.center = (int(pos.x), int(pos.y + radius * 0.04))
        pygame.draw.ellipse(surface, armor, chassis); pygame.draw.ellipse(surface, outline, chassis, 3)
        visor = pygame.Rect(0, 0, int(radius * 1.32), int(radius * 0.44)); visor.center = (int(pos.x), int(pos.y - radius * 0.14))
        pygame.draw.ellipse(surface, outline, visor); pygame.draw.ellipse(surface, (70, 20, 20), visor.inflate(-6, -6))
        for side in (-1, 1):
            eye = pygame.Rect(0, 0, int(radius * 0.42), int(radius * 0.16)); eye.center = (int(pos.x + side * radius * 0.34), int(pos.y - radius * 0.14))
            pygame.draw.line(surface, glow, (eye.left, eye.centery + side), (eye.right, eye.centery - side * 2), 4); pygame.draw.line(surface, outline, (eye.left, eye.centery + side), (eye.right, eye.centery - side * 2), 2)
        core = pygame.Rect(0, 0, int(radius * 0.74), int(radius * 0.56)); core.center = (int(pos.x), int(pos.y + radius * 0.22))
        pygame.draw.ellipse(surface, outline, core); pygame.draw.ellipse(surface, phase_glow, core.inflate(-7, -6))
        pygame.draw.arc(surface, outline, pygame.Rect(int(pos.x - radius * 0.40), int(pos.y + radius * 0.18), int(radius * 0.80), max(10, int(radius * 0.36))), 0.22, math.pi - 0.22, 3)
        return surface
    if enemy.kind == "elite":
        pos = enemy.pos; radius = enemy.radius
        outline = (96, 44, 20); shell = (180, 96, 58); trim = (255, 226, 152)
        pygame.draw.circle(surface, outline, pos, radius + 3); pygame.draw.circle(surface, shell, pos, radius)
        body = pygame.Rect(0, 0, int(radius * 1.58), int(radius * 1.28)); body.center = (int(pos.x), int(pos.y + radius * 0.04))
        pygame.draw.ellipse(surface, shell, body); pygame.draw.ellipse(surface, outline, body, 2)
        for side in (-1, 1):
            wing = ((int(pos.x + side * radius * 0.26), int(pos.y - radius * 0.12)), (int(pos.x + side * radius * 1.02), int(pos.y - radius * 0.58)), (int(pos.x + side * radius * 0.72), int(pos.y + radius * 0.06)))
            pygame.draw.polygon(surface, trim, wing); pygame.draw.polygon(surface, outline, wing, 2)
        core_rect = pygame.Rect(0, 0, int(radius * 0.72), int(radius * 0.84)); core_rect.center = (int(pos.x), int(pos.y + radius * 0.02))
        pygame.draw.rect(surface, outline, core_rect, border_radius=8); pygame.draw.rect(surface, config.BULLET_ELITE_COLOR, core_rect.inflate(-4, -4), border_radius=7)
        return surface
    if enemy.kind == "reactor_bomber":
        pos = enemy.pos; radius = enemy.radius
        outline = (34, 56, 84)
        shell = (92, 134, 182)
        glow = (132, 240, 255)
        rim = (196, 244, 255)
        pygame.draw.circle(surface, outline, pos, radius + 2)
        pygame.draw.circle(surface, shell, pos, radius)
        body = pygame.Rect(0, 0, int(radius * 1.54), int(radius * 1.40))
        body.center = (int(pos.x), int(pos.y + radius * 0.06))
        pygame.draw.ellipse(surface, shell, body)
        pygame.draw.ellipse(surface, outline, body, 2)
        module = pygame.Rect(0, 0, int(radius * 1.05), int(radius * 1.18))
        module.center = (int(pos.x), int(pos.y + radius * 0.06))
        draw_reactor_module(surface, module, body=shell, border=outline, glow=glow)
        side_y = int(pos.y + radius * 0.08)
        for offset in (-radius * 0.62, radius * 0.62):
            pygame.draw.circle(surface, outline, (int(pos.x + offset), side_y), max(3, radius // 4))
            pygame.draw.circle(surface, glow, (int(pos.x + offset), side_y), max(2, radius // 5))
        pygame.draw.arc(
            surface,
            rim,
            pygame.Rect(
                int(pos.x - radius * 0.72),
                int(pos.y - radius * 0.90),
                int(radius * 1.44),
                int(radius * 0.84),
            ),
            math.pi * 1.10,
            math.pi * 1.90,
            2,
        )
        draw_actor_face(surface, pos, radius, "reactor_bomber")
        return surface
    if enemy.kind == "turret":
        base = draw_turret_base_part(enemy)
        top = draw_turret_top_part(enemy)
        surface.blit(base, base.get_rect(center=(110, 110)))
        surface.blit(top, top.get_rect(center=(110, 110)))
        if enemy.variant == "elite_turret":
            pygame.draw.circle(surface, config.TURRET_ELITE_COLOR, enemy.pos, enemy.radius + 7, 2)
        return surface
    if enemy.kind == "engineer":
        pos = enemy.pos; radius = enemy.radius
        outline = (28, 62, 56); body = enemy.color; trim = (214, 250, 232); accent = (255, 210, 122)
        pygame.draw.circle(surface, outline, pos, radius + 2); pygame.draw.circle(surface, body, pos, radius)
        helmet = pygame.Rect(0, 0, int(radius * 1.5), int(radius * 0.8)); helmet.center = (int(pos.x), int(pos.y - radius * 0.18))
        visor = pygame.Rect(0, 0, int(radius * 0.92), int(radius * 0.22)); visor.center = helmet.center
        pack = pygame.Rect(0, 0, int(radius * 0.9), int(radius * 0.7)); pack.center = (int(pos.x), int(pos.y + radius * 0.40))
        pygame.draw.rect(surface, trim, helmet, border_radius=7); pygame.draw.rect(surface, outline, helmet, 2, border_radius=7); pygame.draw.rect(surface, accent, visor, border_radius=4); pygame.draw.rect(surface, outline, visor, 1, border_radius=4); pygame.draw.rect(surface, outline, pack, border_radius=6); pygame.draw.rect(surface, body, pack.inflate(-4, -4), border_radius=5)
        return surface
    if enemy.kind == "shooter":
        pos = enemy.pos; radius = enemy.radius
        outline = (44, 28, 74); shell = enemy.color; trim = (236, 226, 255); glow = (255, 244, 170)
        pygame.draw.circle(surface, outline, pos, radius + 2); pygame.draw.circle(surface, shell, pos, radius - 1)
        visor = pygame.Rect(0, 0, int(radius * 1.36), max(10, int(radius * 0.50))); visor.center = (int(pos.x), int(pos.y - radius * 0.10))
        pygame.draw.rect(surface, trim, visor, border_radius=6); pygame.draw.rect(surface, outline, visor, 2, border_radius=6)
        for offset in (-radius * 0.22, radius * 0.22): pygame.draw.circle(surface, glow, (int(pos.x + offset), int(visor.centery)), max(2, int(radius * 0.10)))
        return surface
    pygame.draw.circle(surface, enemy.color, enemy.pos, enemy.radius)
    draw_actor_face(surface, enemy.pos, enemy.radius, enemy.kind, is_boss=enemy.is_boss)
    return surface


def draw_turret_base_part(enemy: Enemy) -> pygame.Surface:
    surface = make_surface((96, 96))
    enemy = Enemy(**{**enemy.__dict__})
    enemy.pos = pygame.Vector2(48, 48)
    pos = enemy.pos
    radius = enemy.radius
    elite = enemy.variant == "elite_turret"
    outline = (74, 46, 24) if elite else (82, 56, 26)
    body = (170, 104, 72) if elite else (180, 138, 88)
    trim = config.TURRET_ELITE_COLOR if elite else (246, 228, 180)
    plate = (104, 72, 48)

    skid = pygame.Rect(0, 0, int(radius * 1.9), int(radius * 0.66))
    skid.center = (int(pos.x), int(pos.y + radius * 0.90))
    platform = pygame.Rect(0, 0, int(radius * 1.62), int(radius * 0.84))
    platform.center = (int(pos.x), int(pos.y + radius * 0.54))
    spine = pygame.Rect(0, 0, int(radius * 0.74), int(radius * 1.05))
    spine.center = (int(pos.x), int(pos.y + radius * 0.50))
    hub = pygame.Rect(0, 0, int(radius * 0.92), int(radius * 0.52))
    hub.center = (int(pos.x), int(pos.y + radius * 0.18))
    pygame.draw.ellipse(surface, outline, skid)
    pygame.draw.ellipse(surface, plate, skid.inflate(-4, -4))
    pygame.draw.ellipse(surface, outline, platform)
    pygame.draw.ellipse(surface, body, platform.inflate(-4, -4))
    pygame.draw.rect(surface, outline, spine, border_radius=8)
    pygame.draw.rect(surface, body, spine.inflate(-4, -4), border_radius=7)
    pygame.draw.ellipse(surface, outline, hub)
    pygame.draw.ellipse(surface, trim, hub.inflate(-4, -4))
    for side in (-1, 1):
        anchor = pygame.Vector2(pos.x + side * radius * 0.54, pos.y + radius * 0.52)
        foot = (
            (int(anchor.x), int(anchor.y - 3)),
            (int(anchor.x + side * radius * 0.54), int(anchor.y + radius * 0.34)),
            (int(anchor.x + side * radius * 0.20), int(anchor.y + radius * 0.52)),
            (int(anchor.x - side * radius * 0.12), int(anchor.y + radius * 0.18)),
        )
        pygame.draw.polygon(surface, body, foot)
        pygame.draw.polygon(surface, outline, foot, 2)
    return surface


def draw_turret_top_part(enemy: Enemy) -> pygame.Surface:
    surface = make_surface((96, 96))
    enemy = Enemy(**{**enemy.__dict__})
    enemy.pos = pygame.Vector2(48, 48)
    pos = enemy.pos
    radius = enemy.radius
    elite = enemy.variant == "elite_turret"
    outline = (74, 46, 24) if elite else (82, 56, 26)
    body = (182, 114, 78) if elite else enemy.color
    trim = config.TURRET_ELITE_COLOR if elite else (246, 228, 180)
    glow = (255, 220, 176) if elite else (255, 238, 196)

    core_rect = pygame.Rect(0, 0, int(radius * 1.18), int(radius * 1.02))
    core_rect.center = (int(pos.x), int(pos.y))
    collar = pygame.Rect(0, 0, int(radius * 0.82), int(radius * 0.66))
    collar.center = (int(pos.x), int(pos.y))
    pygame.draw.ellipse(surface, outline, core_rect)
    pygame.draw.ellipse(surface, body, core_rect.inflate(-4, -4))
    pygame.draw.ellipse(surface, outline, collar)
    pygame.draw.ellipse(surface, trim, collar.inflate(-4, -4))

    barrel_len = radius + (20 if elite else 15)
    barrel_w = max(6, int(radius * (0.38 if elite else 0.30)))
    barrel = pygame.Rect(0, 0, int(barrel_len), barrel_w)
    barrel.midleft = (int(pos.x + radius * 0.34), int(pos.y))
    pygame.draw.rect(surface, outline, barrel, border_radius=4)
    pygame.draw.rect(surface, trim, barrel.inflate(-4, -2), border_radius=3)
    muzzle = pygame.Rect(0, 0, max(8, int(radius * 0.42)), barrel_w + 4)
    muzzle.midleft = (barrel.right - 2, barrel.centery)
    pygame.draw.rect(surface, outline, muzzle, border_radius=4)
    pygame.draw.rect(surface, glow, muzzle.inflate(-3, -3), border_radius=3)

    for side in (-1, 1):
        fin = (
            (int(pos.x - radius * 0.14), int(pos.y + side * radius * 0.32)),
            (int(pos.x - radius * 0.64), int(pos.y + side * radius * 0.52)),
            (int(pos.x - radius * 0.26), int(pos.y + side * radius * 0.06)),
        )
        pygame.draw.polygon(surface, body, fin)
        pygame.draw.polygon(surface, outline, fin, 2)
    if elite:
        for idx in range(4):
            angle = math.tau * idx / 4 + math.pi / 4
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            start = pos + direction * (radius * 0.12)
            end = pos + direction * (radius * 0.54)
            pygame.draw.line(surface, outline, start, end, 2)
            pygame.draw.line(surface, trim, start, end, 1)
        pygame.draw.circle(surface, glow, pos, max(5, radius // 3))
        pygame.draw.circle(surface, outline, pos, max(5, radius // 3), 2)
    else:
        lens = pos + pygame.Vector2(radius * 0.18, 0)
        pygame.draw.circle(surface, glow, lens, max(4, radius // 3))
        pygame.draw.circle(surface, outline, lens, max(4, radius // 3), 2)
    return surface


def draw_reactor_module(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    body: tuple[int, int, int],
    border: tuple[int, int, int],
    glow: tuple[int, int, int],
) -> None:
    radius = max(5, min(rect.width, rect.height) // 4)
    pygame.draw.rect(surface, border, rect, border_radius=radius)
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(surface, body, inner, border_radius=max(4, radius - 1))

    cap_h = max(4, rect.height // 5)
    top_cap = pygame.Rect(inner.left + 2, inner.top + 1, inner.width - 4, cap_h)
    bottom_cap = pygame.Rect(inner.left + 2, inner.bottom - cap_h - 1, inner.width - 4, cap_h)
    pygame.draw.rect(surface, border, top_cap, border_radius=3)
    pygame.draw.rect(surface, border, bottom_cap, border_radius=3)

    core_center = (rect.centerx, rect.centery)
    ring_r = max(5, min(rect.width, rect.height) // 4)
    core_r = max(3, ring_r - 3)
    pygame.draw.circle(surface, glow, core_center, ring_r, 2)
    pygame.draw.circle(surface, (222, 248, 255), core_center, core_r)
    pygame.draw.circle(surface, glow, core_center, max(2, core_r - 3))
    pygame.draw.line(
        surface,
        glow,
        (rect.centerx, rect.top + cap_h + 2),
        (rect.centerx, rect.bottom - cap_h - 2),
        2,
    )
    for offset in (-1, 1):
        bolt = pygame.Rect(0, 0, 4, 4)
        bolt.center = (rect.centerx + offset * (rect.width // 3), rect.centery)
        pygame.draw.rect(surface, border, bolt, border_radius=2)


def draw_obstacle(obstacle: RoomObstacle) -> pygame.Surface:
    pad = 20
    w = obstacle.rect.width + pad * 2
    h = obstacle.rect.height + pad * 2 + (14 if obstacle.destructible and obstacle.max_hp > 0 else 0)
    surface = make_surface((max(64, w), max(64, h)))
    rect = obstacle.rect.copy(); rect.topleft = (pad, pad)
    radius = 6 if rect.width < 24 or rect.height < 24 else 10
    pygame.draw.rect(surface, obstacle.fill_color, rect, border_radius=radius)
    pygame.draw.rect(surface, obstacle.border_color, rect, 2, border_radius=radius)
    if obstacle.tag == "bullet":
        center = pygame.Vector2(rect.center); inner = max(4, min(rect.width, rect.height) // 4)
        pygame.draw.circle(surface, config.BULLET_BARREL_COLOR, center, inner, 2); pygame.draw.line(surface, config.BULLET_BARREL_COLOR, (rect.left + 5, center.y), (rect.right - 5, center.y), 2)
    elif obstacle.tag == "reactor":
        body = pygame.Rect(rect.left + 2, rect.top + 1, rect.width - 4, rect.height - 4)
        draw_reactor_module(
            surface,
            body,
            body=obstacle.fill_color,
            border=obstacle.border_color,
            glow=config.BULLET_SHOCK_COLOR,
        )
    elif obstacle.tag == "toxic":
        pygame.draw.circle(surface, (150, 220, 130), rect.center, max(4, min(rect.width, rect.height) // 5), 2)
    elif obstacle.tag == "nuke":
        center = pygame.Vector2(rect.center); core_radius = max(8, min(rect.width, rect.height) // 6)
        pygame.draw.circle(surface, config.NUKE_CORE_COLOR, center, core_radius); pygame.draw.circle(surface, config.NUKE_BORDER_COLOR, center, core_radius + 8, 2)
    if obstacle.destructible and obstacle.max_hp > 0 and obstacle.tag != "reactor":
        bar = pygame.Rect(rect.left, rect.bottom + 4, rect.width, 5); pygame.draw.rect(surface, (48, 28, 20), bar, border_radius=3); pygame.draw.rect(surface, config.ITEM_COLOR, bar, border_radius=3)
    return surface


def draw_treasure() -> pygame.Surface:
    surface = make_surface((84, 60))
    outline = (112, 74, 26)
    wood = (146, 98, 42)
    wood_dark = (114, 74, 32)
    metal = config.CREDIT_COLOR
    glow = (255, 238, 176)
    body = pygame.Rect(10, 20, 64, 30)
    lid = pygame.Rect(12, 10, 60, 20)
    latch = pygame.Rect(0, 0, 14, 12)
    latch.center = (42, 28)
    pygame.draw.rect(surface, outline, body, border_radius=10)
    pygame.draw.rect(surface, wood, body.inflate(-4, -4), border_radius=9)
    pygame.draw.rect(surface, outline, lid, border_radius=10)
    pygame.draw.rect(surface, wood_dark, lid.inflate(-4, -4), border_radius=9)
    pygame.draw.line(surface, metal, (16, 33), (68, 33), 3)
    pygame.draw.line(surface, glow, (18, 32), (66, 32), 1)
    for x in (24, 60):
        strap = pygame.Rect(0, 0, 8, 34)
        strap.center = (x, 30)
        pygame.draw.rect(surface, metal, strap, border_radius=3)
        pygame.draw.rect(surface, outline, strap, 1, border_radius=3)
    pygame.draw.rect(surface, metal, latch, border_radius=4)
    pygame.draw.rect(surface, outline, latch, 2, border_radius=4)
    pygame.draw.circle(surface, glow, latch.center, 3)
    pygame.draw.arc(surface, glow, pygame.Rect(20, 6, 44, 20), math.pi * 1.08, math.pi * 1.92, 2)
    return surface


def draw_exit_active() -> pygame.Surface:
    surface = make_surface((140, 140))
    pos = pygame.Vector2(70, 58)
    pygame.draw.circle(surface, (110, 170, 255), pos, 34, 3); pygame.draw.circle(surface, (70, 120, 210), pos, 18, 2)
    surface.blit(SMALL_FONT.render("出口", True, config.TEXT_COLOR), SMALL_FONT.render("出口", True, config.TEXT_COLOR).get_rect(center=(pos.x, pos.y + 54)))
    return surface


def draw_screen_door(direction: str, locked: bool = False) -> pygame.Surface:
    if direction in {"north", "south"}: rect, size = pygame.Rect(28, 18, 44, 24), (100, 60)
    else: rect, size = pygame.Rect(18, 28, 24, 44), (60, 100)
    surface = make_surface(size)
    fill = (155, 66, 66) if locked else config.DOOR_FILL; glow = (210, 96, 96) if locked else config.DOOR_GLOW
    pygame.draw.rect(surface, glow, rect.inflate(14, 14), border_radius=12); pygame.draw.rect(surface, fill, rect, border_radius=8)
    if not locked:
        arrows = {"north": "↑", "east": "→", "south": "↓", "west": "←"}
        arrow = SMALL_FONT.render(arrows[direction], True, config.TEXT_COLOR); surface.blit(arrow, arrow.get_rect(center=rect.center))
    return surface


def export_characters():
    for key in ["vanguard", "mamba", "kunkun"]:
        save(
            draw_character_avatar(key),
            OUT / "characters" / f"{key}.png",
            crop=key not in {"vanguard"},
        )


def export_weapons():
    for key in ["rifle", "scatter", "shotgun", "rail", "rocket", "laser_burst", "laser_lance"]: save(draw_weapon(key), OUT / "weapons" / f"{key}.png")


def export_bullets():
    bullets = {
        "bullet": Bullet(pygame.Vector2(), pygame.Vector2(1, 0), 0, 6, 0, 1, color=config.BULLET_COLOR, style="bullet"),
        "bullet_enemy": Bullet(pygame.Vector2(), pygame.Vector2(1, 0), 0, 6, 0, 1, color=config.BULLET_ENEMY_COLOR, style="bullet", friendly=False),
        "bullet_elite": Bullet(pygame.Vector2(), pygame.Vector2(1, 0), 0, 7, 0, 1, color=config.BULLET_ELITE_COLOR, style="bullet", friendly=False),
        "bullet_shock": Bullet(pygame.Vector2(), pygame.Vector2(1, 0), 0, 7, 0, 1, color=config.BULLET_SHOCK_COLOR, style="bullet", friendly=False),
        "rail": Bullet(pygame.Vector2(), pygame.Vector2(1, 0), 0, 6, 0, 1, color=config.BULLET_COLOR, style="rail"),
        "shotgun_pellet": Bullet(pygame.Vector2(), pygame.Vector2(1, 0), 0, 5, 0, 1, color=config.SHOTGUN_PELLET_COLOR, style="shotgun_pellet"),
        "rocket": Bullet(pygame.Vector2(), pygame.Vector2(1, 0), 0, config.ROCKET_PROJECTILE_RADIUS, 0, 1, color=config.ROCKET_COLOR, style="rocket"),
        "basketball": Bullet(pygame.Vector2(), pygame.Vector2(1, 0), 0, config.BASKETBALL_RADIUS, 0, 1, color=config.BASKETBALL_COLOR, style="basketball"),
    }
    for key, bullet in bullets.items():
        save(
            draw_bullet_sprite(bullet),
            OUT / "bullets" / f"{key}.png",
            crop=key not in {"rail"},
        )


def export_enemies():
    defs = {
        "grunt": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS, 1, 1, config.ENEMY_COLOR, kind="grunt"),
        "laser": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS, 1, 1, config.ENEMY_LASER_COLOR, kind="laser"),
        "shooter": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS, 1, 1, config.SHOOTER_COLOR, kind="shooter"),
        "shotgunner": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS, 1, 1, config.SHOTGUN_ENEMY_COLOR, kind="shotgunner"),
        "charger": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS, 1, 1, (255, 150, 150), kind="charger"),
        "elite": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS + 2, 1, 1, config.ELITE_COLOR, kind="elite"),
        "boss": Enemy(pygame.Vector2(), 1, 1, 0, config.BOSS_RADIUS, 1, 1, config.BOSS_COLOR, is_boss=True, kind="boss"),
        "challenge": Enemy(pygame.Vector2(), 1, 1, 0, config.BOSS_RADIUS + 4, 1, 1, config.CHALLENGE_ROOM_COLOR, is_boss=True, kind="boss", variant="challenge"),
        "engineer": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS + 1, 1, 1, config.ENGINEER_ENEMY_COLOR, kind="engineer"),
        "turret": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS + 3, 1, 1, config.TURRET_ENEMY_COLOR, kind="turret", variant="turret"),
        "elite_turret": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS + 6, 1, 1, config.TURRET_ELITE_COLOR, kind="turret", variant="elite_turret"),
        "toxic_bloater": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS + 1, 1, 1, config.TOXIC_ENEMY_COLOR, kind="toxic_bloater"),
        "reactor_bomber": Enemy(pygame.Vector2(), 1, 1, 0, config.ENEMY_RADIUS + 2, 1, 1, config.REACTOR_ENEMY_COLOR, kind="reactor_bomber"),
    }
    for key, enemy in defs.items(): save(draw_enemy_avatar(enemy), OUT / "enemies" / f"{key}.png")
    turret_defs = {
        "turret": defs["turret"],
        "elite_turret": defs["elite_turret"],
    }
    for key, enemy in turret_defs.items():
        save(draw_turret_base_part(enemy), OUT / "enemies" / f"{key}_base.png", crop=False)
        save(draw_turret_top_part(enemy), OUT / "enemies" / f"{key}_top.png", crop=False)


def export_map():
    obstacle_defs = {
        "wall": RoomObstacle(pygame.Rect(0, 0, 96, 24), False, tag="wall", fill_color=SPECIAL_TAG_COLORS["wall"][0], border_color=SPECIAL_TAG_COLORS["wall"][1]),
        "cover": RoomObstacle(pygame.Rect(0, 0, 54, 30), True, 40, 40, tag="cover", fill_color=SPECIAL_TAG_COLORS["cover"][0], border_color=SPECIAL_TAG_COLORS["cover"][1]),
        "crate": RoomObstacle(pygame.Rect(0, 0, 28, 28), True, 40, 40, tag="crate", fill_color=SPECIAL_TAG_COLORS["crate"][0], border_color=SPECIAL_TAG_COLORS["crate"][1]),
        "bullet": RoomObstacle(pygame.Rect(0, 0, 24, 24), True, 40, 40, tag="bullet", fill_color=SPECIAL_TAG_COLORS["bullet"][0], border_color=SPECIAL_TAG_COLORS["bullet"][1]),
        "toxic": RoomObstacle(pygame.Rect(0, 0, 26, 26), True, 40, 40, tag="toxic", fill_color=SPECIAL_TAG_COLORS["toxic"][0], border_color=SPECIAL_TAG_COLORS["toxic"][1]),
        "reactor": RoomObstacle(pygame.Rect(0, 0, 38, 38), True, 56, 56, tag="reactor", fill_color=SPECIAL_TAG_COLORS["reactor"][0], border_color=SPECIAL_TAG_COLORS["reactor"][1]),
        "nuke": RoomObstacle(pygame.Rect(0, 0, config.NUKE_OBSTACLE_SIZE, config.NUKE_OBSTACLE_SIZE), True, 100, 100, tag="nuke", fill_color=config.NUKE_FILL_COLOR, border_color=config.NUKE_BORDER_COLOR),
    }
    for key, obstacle in obstacle_defs.items(): save(draw_obstacle(obstacle), OUT / "map" / f"{key}.png")
    save(draw_treasure(), OUT / "map" / "treasure.png", crop=False); save(draw_exit_active(), OUT / "map" / "exit_active.png")
    for direction in ["north", "east", "south", "west"]:
        save(draw_screen_door(direction, False), OUT / "map" / f"{direction}.png")
        save(draw_screen_door(direction, True), OUT / "map" / f"{direction}_locked.png")


def main():
    ensure_dirs(); export_characters(); export_weapons(); export_bullets(); export_enemies(); export_map(); print("done")


if __name__ == "__main__":
    main(); pygame.quit()
