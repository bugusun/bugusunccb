import math
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game import config

ROOT = Path(r"T:/gameV1")
OUT = ROOT / "resources" / "effects"

pygame.init()


def ensure_dirs():
    for rel in [
        "skills/pulse",
        "skills/mamba_smash_startup",
        "skills/mamba_smash_impact",
        "combat/explosion_wave",
        "combat/laser_trace",
        "combat/laser_lance_trace",
        "combat/enemy_laser_trace",
        "telegraphs/boss_stomp",
        "telegraphs/boss_nova",
        "telegraphs/challenge_dash_charge",
        "telegraphs/challenge_summon",
        "telegraphs/enemy_laser",
        "status/stun_marker",
        "status/poison_marker",
        "environment/gas_cloud",
        "room_events/nuke",
        "room_events/elite_turret",
        "ui/auto_aim",
        "ui/screen_flash",
    ]:
        (OUT / rel).mkdir(parents=True, exist_ok=True)


def crop_surface(surface: pygame.Surface, pad: int = 4) -> pygame.Surface:
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


def save_frame(surface: pygame.Surface, directory: Path, idx: int):
    final = crop_surface(surface)
    pygame.image.save(final, str(directory / f"{idx:03d}.png"))


def make_surface(size=(768, 768)):
    return pygame.Surface(size, pygame.SRCALPHA)


def ring_rect(center: pygame.Vector2, radius: float) -> pygame.Rect:
    rect = pygame.Rect(0, 0, max(2, int(radius * 2)), max(2, int(radius * 2)))
    rect.center = (int(center.x), int(center.y))
    return rect


def draw_segmented_ring(
    surface: pygame.Surface,
    center: pygame.Vector2,
    radius: float,
    *,
    segments: int,
    coverage: float,
    rotation: float,
    color: tuple[int, int, int],
    alpha: int,
    width: int,
) -> None:
    rect = ring_rect(center, radius)
    span = math.tau / max(1, segments)
    arc_span = span * max(0.08, min(0.92, coverage))
    for idx in range(max(1, segments)):
        start = rotation + span * idx + span * 0.08
        pygame.draw.arc(
            surface,
            (*color, alpha),
            rect,
            start,
            start + arc_span,
            max(1, width),
        )


def draw_star_burst(
    surface: pygame.Surface,
    center: pygame.Vector2,
    inner_radius: float,
    outer_radius: float,
    *,
    spokes: int,
    rotation: float,
    color: tuple[int, int, int],
    alpha: int,
    width: int,
) -> None:
    for idx in range(max(1, spokes)):
        angle = rotation + math.tau * idx / max(1, spokes)
        direction = pygame.Vector2(math.cos(angle), math.sin(angle))
        tangent = pygame.Vector2(-direction.y, direction.x)
        start = center + direction * inner_radius
        mid = center + direction * ((inner_radius + outer_radius) * 0.54)
        end = center + direction * outer_radius
        offset = tangent * (4 + (idx % 2) * 3)
        pygame.draw.lines(
            surface,
            (*color, alpha),
            False,
            (start, mid + offset, end),
            max(1, width),
        )


def export_pulse(frames: int = 48):
    directory = OUT / "skills" / "pulse"
    center = pygame.Vector2(384, 384)
    radius = 180.0
    for idx in range(frames):
        progress = idx / max(1, frames - 1)
        eased = 1.0 - (1.0 - progress) ** 2.2
        surf = make_surface()
        ring_alpha = int(132 + 74 * (1.0 - progress))
        ring_width = max(3, int(8 - eased * 3))
        phase = progress * math.tau
        pygame.draw.circle(
            surf,
            (*config.BULLET_SHOCK_COLOR, 28 + int(18 * (1.0 - progress))),
            center,
            int(radius * 0.92),
        )
        pygame.draw.circle(
            surf,
            (*config.LASER_LIGHT_COLOR, 56 + int(24 * (1.0 - progress))),
            center,
            max(12, int(radius * 0.16)),
        )
        pygame.draw.circle(
            surf,
            (*config.LASER_TRACE_CORE, 168),
            center,
            max(8, int(radius * 0.08)),
        )
        draw_segmented_ring(
            surf,
            center,
            radius,
            segments=10,
            coverage=0.56,
            rotation=phase * 0.38,
            color=config.LASER_LIGHT_COLOR,
            alpha=ring_alpha,
            width=ring_width,
        )
        draw_segmented_ring(
            surf,
            center,
            radius * 0.86,
            segments=7,
            coverage=0.24,
            rotation=-phase * 0.55,
            color=config.LASER_TRACE_CORE,
            alpha=92 + int(48 * (1.0 - progress)),
            width=max(1, ring_width - 2),
        )
        for arc_idx in range(config.PULSE_EFFECT_ARCS + 2):
            angle = phase * 0.74 + arc_idx * (math.tau / (config.PULSE_EFFECT_ARCS + 2))
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            tangent = pygame.Vector2(-direction.y, direction.x)
            path = [center + direction * max(10.0, radius * 0.08)]
            steps = 4
            for step in range(1, steps + 1):
                ratio = 0.12 + 0.82 * (step / steps)
                bend = math.sin(phase * 2.4 + arc_idx * 1.1 + step * 0.8)
                point = (
                    center
                    + direction * (radius * ratio)
                    + tangent * (radius * 0.06 * bend * (1.0 - ratio * 0.32))
                )
                path.append(point)
            pygame.draw.lines(
                surf,
                (*config.BULLET_SHOCK_COLOR, 182),
                False,
                path,
                2,
            )
            pygame.draw.lines(
                surf,
                (*config.LASER_TRACE_CORE, 148),
                False,
                path[-3:],
                1,
            )
            tip = path[-1]
            pygame.draw.circle(
                surf,
                (*config.LASER_TRACE_CORE, 184),
                (int(tip.x), int(tip.y)),
                4,
            )
        for branch_idx in range(4):
            angle = phase * 1.1 + branch_idx * (math.tau / 4) + 0.18
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            tangent = pygame.Vector2(-direction.y, direction.x)
            start = center + direction * (radius * 0.34)
            mid = center + direction * (radius * 0.56) + tangent * (10 if branch_idx % 2 == 0 else -10)
            end = center + direction * (radius * 0.76)
            pygame.draw.lines(
                surf,
                (*config.BULLET_SHOCK_COLOR, 134),
                False,
                (start, mid, end),
                2,
            )
        save_frame(surf, directory, idx)


def export_mamba(frames: int = 48):
    startup_dir = OUT / "skills" / "mamba_smash_startup"
    impact_dir = OUT / "skills" / "mamba_smash_impact"
    center = pygame.Vector2(220, 384)
    direction = pygame.Vector2(1, 0)
    side = pygame.Vector2(0, 1)
    for idx in range(frames):
        life = 1.0 - idx / max(1, frames - 1)
        surf = make_surface()
        base = center + direction * 10
        tip = center + direction * (config.MAMBA_SKILL_RANGE * 0.88)
        half_width = 24 + (1.0 - life) * 24
        polygon = (base - side * 18, tip - side * half_width, tip + side * half_width, base + side * 18)
        pygame.draw.polygon(surf, (*config.MAMBA_JERSEY_COLOR, int(38 + 54 * life)), polygon)
        pygame.draw.polygon(surf, (*config.MAMBA_TRIM_COLOR, int(160 + 55 * life)), polygon, 3)
        for line_idx in range(3):
            line_pos = 0.28 + line_idx * 0.17
            center_line = base.lerp(tip, line_pos)
            width = 14 + line_idx * 8
            start = center_line - side * width
            end = center_line + side * width
            pygame.draw.line(
                surf,
                (*config.MAMBA_TRIM_COLOR, int(120 + 45 * life)),
                start,
                end,
                3,
            )
        save_frame(surf, startup_dir, idx)

    center = pygame.Vector2(384, 384)
    for idx in range(frames):
        life = 1.0 - idx / max(1, frames - 1)
        surf = make_surface()
        tip = center + direction * (48 + 28 * (1.0 - life))
        back = center - direction * 26
        wing = 18 + 24 * life
        polygon = (
            back - side * (wing * 0.55),
            center - side * wing,
            tip,
            center + side * wing,
            back + side * (wing * 0.55),
        )
        pygame.draw.polygon(surf, (*config.MAMBA_IMPACT_COLOR, int(72 + 84 * life)), polygon)
        pygame.draw.polygon(surf, (*config.MAMBA_GLOW_COLOR, int(150 + 80 * life)), polygon, 3)
        for line_idx in range(3):
            offset = (line_idx - 1) * 12
            start = center - direction * (10 + line_idx * 10) + side * offset
            end = start + direction * (46 + line_idx * 8)
            pygame.draw.line(
                surf,
                (*config.MAMBA_TRIM_COLOR, int(168 + 55 * life)),
                start,
                end,
                4 - min(line_idx, 2),
            )
        save_frame(surf, impact_dir, idx)


def export_explosion_wave(frames: int = 48):
    directory = OUT / "combat" / "explosion_wave"
    center = pygame.Vector2(384, 384)
    for idx in range(frames):
        progress = idx / max(1, frames - 1)
        eased = 1.0 - (1.0 - progress) ** 2.1
        life = 1.0 - progress
        surf = make_surface()
        radius = 26.0 + 114.0 * eased
        inner_radius = max(8.0, radius * (0.26 + 0.12 * life))
        flash_radius = 14.0 + 52.0 * (life ** 0.52)

        pygame.draw.circle(
            surf,
            (255, 255, 255, int(18 + 44 * (life ** 0.8))),
            center,
            int(radius * 0.82),
        )
        pygame.draw.circle(
            surf,
            (255, 255, 255, int(46 + 88 * (life ** 0.55))),
            center,
            int(flash_radius),
            max(1, int(6 - progress * 3)),
        )
        pygame.draw.circle(
            surf,
            (210, 210, 210, int(34 + 54 * (life ** 0.8))),
            center,
            int(max(10.0, flash_radius * 0.52)),
        )

        draw_segmented_ring(
            surf,
            center,
            radius,
            segments=8,
            coverage=0.66 - progress * 0.12,
            rotation=progress * 0.46,
            color=(255, 255, 255),
            alpha=int(124 + 88 * (life ** 0.65)),
            width=max(2, int(8 - progress * 3)),
        )
        draw_segmented_ring(
            surf,
            center,
            radius * (0.88 + 0.04 * math.sin(progress * math.tau * 1.5)),
            segments=12,
            coverage=0.36,
            rotation=-progress * 0.82,
            color=(214, 214, 214),
            alpha=int(64 + 56 * life),
            width=max(1, int(4 - progress * 1.5)),
        )
        draw_star_burst(
            surf,
            center,
            inner_radius,
            radius * 0.96,
            spokes=7,
            rotation=progress * 0.38,
            color=(255, 255, 255),
            alpha=int(44 + 60 * life),
            width=max(1, int(3 - progress * 1.2)),
        )

        puff_alpha = int(34 + 48 * life)
        for puff_idx in range(6):
            angle = progress * 0.65 + math.tau * puff_idx / 6
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            tangent = pygame.Vector2(-direction.y, direction.x)
            puff_center = (
                center
                + direction * (radius * (0.68 + 0.06 * (puff_idx % 2)))
                + tangent * ((-1) ** puff_idx) * (6 + 2 * life)
            )
            puff_radius = 10 + int(8 * life) + (puff_idx % 3)
            pygame.draw.circle(
                surf,
                (196, 196, 196, puff_alpha),
                (int(puff_center.x), int(puff_center.y)),
                puff_radius,
            )
        save_frame(surf, directory, idx)


def export_laser_trace(frames: int = 48):
    specs = (
        ("laser_trace", config.LASER_LIGHT_COLOR, config.LASER_TRACE_CORE, 12),
        ("laser_lance_trace", config.LASER_HEAVY_COLOR, (240, 248, 255), 18),
        ("enemy_laser_trace", config.ENEMY_LASER_COLOR, config.ENEMY_LASER_LOCK_COLOR, 12),
    )
    start = pygame.Vector2(140, 384)
    end = pygame.Vector2(620, 384)
    for name, outer_color, core_color, width in specs:
        directory = OUT / "combat" / name
        for idx in range(frames):
            life = 1.0 - idx / max(1, frames - 1)
            surf = make_surface()
            outer_width = width + max(4, int(width * 0.45 * life))
            mid_width = width + max(2, int(width * 0.22 * life))
            core_width = max(2, int(width * 0.42))
            glow_radius = max(width + 2, int(width * (0.9 + 0.28 * life)))
            pygame.draw.line(
                surf,
                (*outer_color, int(52 + 84 * life)),
                start,
                end,
                outer_width,
            )
            pygame.draw.line(
                surf,
                (*core_color, int(104 + 108 * life)),
                start,
                end,
                mid_width,
            )
            pygame.draw.line(
                surf,
                (*outer_color, int(164 + 72 * life)),
                start,
                end,
                core_width,
            )
            for point in (start, end):
                pygame.draw.circle(
                    surf,
                    (*core_color, int(112 + 92 * life)),
                    point,
                    glow_radius,
                )
                pygame.draw.circle(
                    surf,
                    (*outer_color, int(178 + 60 * life)),
                    point,
                    max(4, glow_radius - 5),
                    2,
                )
            save_frame(surf, directory, idx)


def export_telegraphs(frames: int = 48):
    center = pygame.Vector2(384, 384)
    enemy_radius = config.BOSS_RADIUS
    specs = {
        "boss_stomp": OUT / "telegraphs" / "boss_stomp",
        "boss_nova": OUT / "telegraphs" / "boss_nova",
        "challenge_dash_charge": OUT / "telegraphs" / "challenge_dash_charge",
        "challenge_summon": OUT / "telegraphs" / "challenge_summon",
        "enemy_laser": OUT / "telegraphs" / "enemy_laser",
    }
    for idx in range(frames):
        life = idx / max(1, frames - 1)

        surf = make_surface()
        radius = float(config.BOSS_STOMP_RADIUS) * (0.76 + 0.24 * life)
        outer_width = max(2, int(6 - life * 2))
        inner_ring = enemy_radius + 10 + int(2 * math.sin(life * math.tau * 1.2))
        pygame.draw.circle(
            surf,
            (255, 255, 255, int(18 + 30 * life)),
            center,
            int(radius * 0.9),
        )
        draw_segmented_ring(
            surf,
            center,
            radius,
            segments=10,
            coverage=0.62,
            rotation=life * 0.26,
            color=(255, 255, 255),
            alpha=int(150 + 60 * life),
            width=outer_width,
        )
        draw_segmented_ring(
            surf,
            center,
            radius * 0.82,
            segments=6,
            coverage=0.28,
            rotation=-life * 0.42,
            color=(216, 216, 216),
            alpha=int(72 + 54 * life),
            width=max(1, outer_width - 2),
        )
        pygame.draw.circle(
            surf,
            (255, 255, 255, int(124 + 60 * life)),
            center,
            inner_ring,
            2,
        )
        draw_star_burst(
            surf,
            center,
            enemy_radius + 14,
            radius * 0.64,
            spokes=6,
            rotation=life * 0.35,
            color=(235, 235, 235),
            alpha=int(78 + 52 * life),
            width=2,
        )
        for crack_idx in range(4):
            angle = math.tau * crack_idx / 4 + life * 0.22
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            tangent = pygame.Vector2(-direction.y, direction.x)
            start = center + direction * (enemy_radius + 12)
            mid = center + direction * (radius * 0.36) + tangent * (10 - crack_idx * 3)
            end = center + direction * (radius * (0.56 + 0.04 * crack_idx))
            pygame.draw.lines(
                surf,
                (208, 208, 208, int(66 + 42 * life)),
                False,
                (start, mid, end),
                2,
            )
        save_frame(surf, specs["boss_stomp"], idx)

        surf = make_surface()
        radius = int(enemy_radius + 32 + 18 * life)
        pygame.draw.circle(surf, config.BULLET_ELITE_COLOR, center, radius, 3)
        for line_idx in range(4):
            angle = math.tau * line_idx / 4 + life * 0.42
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            pygame.draw.line(surf, config.BULLET_ELITE_COLOR, center, center + direction * radius, 2)
        save_frame(surf, specs["boss_nova"], idx)

        surf = make_surface()
        direction = pygame.Vector2(1, 0)
        dash_length = 180
        end = center + direction * dash_length
        pygame.draw.line(surf, config.CHALLENGE_ROOM_COLOR, center, end, 4)
        pygame.draw.circle(surf, config.CHALLENGE_ROOM_COLOR, center, enemy_radius + 10, 3)
        save_frame(surf, specs["challenge_dash_charge"], idx)

        surf = make_surface()
        radius = int(enemy_radius + 18 + 12 * life)
        pygame.draw.circle(surf, config.CHALLENGE_ROOM_COLOR, center, radius, 3)
        for mark_idx in range(config.CHALLENGE_BOSS_SUMMON_COUNT):
            angle = math.tau * mark_idx / max(1, config.CHALLENGE_BOSS_SUMMON_COUNT) + life * 0.8
            marker = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * (radius + 12)
            pygame.draw.circle(surf, config.CHALLENGE_ROOM_COLOR, marker, 8, 2)
        save_frame(surf, specs["challenge_summon"], idx)

        surf = make_surface()
        start = pygame.Vector2(140, 384)
        end = pygame.Vector2(630, 320)
        color = config.ENEMY_LASER_LOCK_COLOR if idx > frames // 2 else config.ENEMY_LASER_COLOR
        width = 3 if idx > frames // 2 else 2
        pygame.draw.line(surf, color, start, end, width)
        pygame.draw.circle(surf, color, start, config.ENEMY_RADIUS + 4, 1)
        save_frame(surf, specs["enemy_laser"], idx)


def export_screen_flash(frames: int = 24):
    directory = OUT / "ui" / "screen_flash"
    color = config.BULLET_SHOCK_COLOR
    alpha_base = 180
    for idx in range(frames):
        life = 1.0 - idx / max(1, frames - 1)
        alpha = int(alpha_base * (life ** 0.7))
        surf = make_surface((512, 512))
        surf.fill((*color, alpha))
        save_frame(surf, directory, idx)


def export_status_markers(frames: int = 48):
    stun_dir = OUT / "status" / "stun_marker"
    poison_dir = OUT / "status" / "poison_marker"
    enemy_pos = pygame.Vector2(128, 128)
    enemy_radius = 24
    for idx in range(frames):
        phase = idx / frames * math.tau
        surf = make_surface((256, 256))
        center = enemy_pos + pygame.Vector2(0, -enemy_radius - 8)
        orbit_radius = max(6, enemy_radius * 0.42)
        for orb in range(3):
            angle = phase + orb * (math.tau / 3)
            point = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit_radius
            pygame.draw.circle(surf, config.MAMBA_STUN_COLOR, point, 3)
            pygame.draw.circle(surf, config.MAMBA_TRIM_COLOR, point, 3, 1)
        save_frame(surf, stun_dir, idx)

        surf = make_surface((256, 256))
        center = enemy_pos + pygame.Vector2(enemy_radius * 0.55, -enemy_radius - 8)
        bob = math.sin(phase) * 1.5
        for offset in (-5, 0, 5):
            pygame.draw.circle(
                surf,
                config.POISON_STATUS_COLOR,
                (int(center.x + offset), int(center.y - abs(offset) * 0.3 + bob)),
                2,
            )
        save_frame(surf, poison_dir, idx)


def export_gas_cloud(frames: int = 48):
    directory = OUT / "environment" / "gas_cloud"
    for idx in range(frames):
        progress = idx / max(1, frames - 1)
        target_radius = 84.0
        radius = 14.0 + (target_radius - 14.0) * progress
        surf = make_surface((256, 256))
        center = pygame.Vector2(128, 128)
        dark = (58, 102, 50, 42 + int(32 * progress))
        body = (92, 150, 76, 58 + int(52 * progress))
        glow = (156, 222, 128, 28 + int(20 * progress))
        outline = (168, 238, 146, 18 + int(18 * progress))
        for puff_idx in range(9):
            angle = math.tau * puff_idx / 9 + progress * 0.35 + math.sin(progress * 3.1 + puff_idx) * 0.08
            distance = radius * (0.14 + 0.38 * (0.5 + 0.5 * math.sin(progress * 2.2 + puff_idx * 1.3)))
            pos = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
            rx = radius * (0.30 + 0.08 * math.sin(progress * 3.2 + puff_idx * 0.7))
            ry = radius * (0.22 + 0.07 * math.cos(progress * 2.8 + puff_idx * 1.1))
            rect = pygame.Rect(0, 0, int(max(12, rx * 2)), int(max(10, ry * 2)))
            rect.center = (int(pos.x), int(pos.y))
            pygame.draw.ellipse(surf, dark if puff_idx % 3 == 0 else body, rect)
        for haze_idx in range(6):
            angle = math.tau * haze_idx / 6 + progress * 0.28
            pos = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * (radius * 0.58)
            haze = pygame.Rect(0, 0, int(radius * 0.82), int(radius * 0.44))
            haze.center = (int(pos.x), int(pos.y))
            pygame.draw.ellipse(surf, glow, haze)
        for ring_idx in range(5):
            angle = math.tau * ring_idx / 5 + progress * 0.6
            point = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * (radius * 0.72)
            pygame.draw.circle(
                surf,
                outline,
                (int(point.x), int(point.y)),
                max(6, int(radius * 0.12)),
                1,
            )
        for mote_idx in range(12):
            angle = math.tau * mote_idx / 12 + progress * 0.42
            dist = radius * (0.12 + 0.78 * ((mote_idx % 4) / 4))
            point = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
            pygame.draw.circle(
                surf,
                (190, 255, 170, 52 + int(30 * progress)),
                (int(point.x), int(point.y)),
                2,
            )
        save_frame(surf, directory, idx)


def export_room_events(frames: int = 48):
    nuke_dir = OUT / "room_events" / "nuke"
    turret_dir = OUT / "room_events" / "elite_turret"
    center = pygame.Vector2(160, 160)
    for idx in range(frames):
        pulse = 0.5 + 0.5 * math.sin((idx / frames) * math.tau)
        surf = make_surface((320, 320))
        pygame.draw.circle(surf, config.NUKE_BORDER_COLOR, center, int(56 + pulse * 10), 2)
        save_frame(surf, nuke_dir, idx)

        surf = make_surface((320, 320))
        pygame.draw.circle(surf, config.TURRET_ELITE_COLOR, center, int(46 + pulse * 8), 2)
        save_frame(surf, turret_dir, idx)


def export_auto_aim(frames: int = 48):
    directory = OUT / "ui" / "auto_aim"
    center = pygame.Vector2(96, 96)
    for idx in range(frames):
        ring = 12 + int(2 * math.sin((idx / frames) * math.tau))
        surf = make_surface((192, 192))
        pygame.draw.circle(surf, config.CREDIT_COLOR, center, ring, 2)
        pygame.draw.circle(surf, config.CREDIT_COLOR, center, 4)
        save_frame(surf, directory, idx)


def main():
    ensure_dirs()
    export_pulse()
    export_mamba()
    export_explosion_wave()
    export_laser_trace()
    export_telegraphs()
    export_status_markers()
    export_gas_cloud()
    export_room_events()
    export_auto_aim()
    export_screen_flash()
    print("done")


if __name__ == "__main__":
    main()
    pygame.quit()
