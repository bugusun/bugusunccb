from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random

import pygame

from .balance import hazard_profile

Cell = tuple[int, int]
GridPos = tuple[int, int]

DIRECTIONS = ("north", "east", "south", "west")
DIRECTION_OFFSETS: dict[str, GridPos] = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}
OPPOSITE_DIRECTIONS = {
    "north": "south",
    "east": "west",
    "south": "north",
    "west": "east",
}

ROOM_THEMES = (
    "\u5f00\u9614\u8f66\u95f4",
    "\u63a9\u4f53\u5de5\u5e26",
    "\u5e9f\u6599\u5806\u573a",
    "\u53cd\u5e94\u5806\u5ba4",
    "\u5c01\u9501\u58c1\u5792",
)


@dataclass(frozen=True)
class Chamber:
    cell: Cell
    rect: pygame.Rect
    center: pygame.Vector2


@dataclass
class RoomObstacle:
    rect: pygame.Rect
    destructible: bool = False
    max_hp: float = 0.0
    hp: float = 0.0
    tag: str = "normal"
    fill_color: tuple[int, int, int] | None = None
    border_color: tuple[int, int, int] | None = None

    def damage(self, amount: float) -> bool:
        if not self.destructible:
            return False
        self.hp = max(0.0, self.hp - amount)
        return self.hp <= 0


@dataclass
class RoomLayout:
    name: str
    theme: str
    obstacles: list[RoomObstacle]
    doorways: list[pygame.Rect]
    chambers: dict[Cell, Chamber]
    links: dict[Cell, tuple[Cell, ...]]
    door_centers: dict[frozenset[Cell], pygame.Vector2]
    player_spawn: pygame.Vector2
    enemy_cells: tuple[Cell, ...]
    pickup_cells: tuple[Cell, ...]
    screen_doors: dict[str, pygame.Rect]
    door_entries: dict[str, pygame.Vector2]

    def closest_cell(self, pos: pygame.Vector2) -> Cell | None:
        if not self.chambers:
            return None
        for chamber in self.chambers.values():
            if chamber.rect.inflate(24, 24).collidepoint(pos.x, pos.y):
                return chamber.cell
        return min(
            self.chambers,
            key=lambda cell: self.chambers[cell].center.distance_squared_to(pos),
        )

    def path_between(self, start: Cell | None, goal: Cell | None) -> list[Cell]:
        if start is None or goal is None:
            return []
        if start == goal:
            return [start]
        frontier: deque[Cell] = deque([start])
        parents: dict[Cell, Cell | None] = {start: None}
        while frontier:
            cell = frontier.popleft()
            for nxt in self.links.get(cell, ()):
                if nxt in parents:
                    continue
                parents[nxt] = cell
                if nxt == goal:
                    frontier.clear()
                    break
                frontier.append(nxt)
        if goal not in parents:
            return [start]
        path = [goal]
        cell = goal
        while parents[cell] is not None:
            cell = parents[cell]
            path.append(cell)
        path.reverse()
        return path

    def door_between(self, a: Cell, b: Cell) -> pygame.Vector2 | None:
        return self.door_centers.get(frozenset((a, b)))

    def sample_point(
        self,
        rng: random.Random,
        allowed_cells: tuple[Cell, ...] | list[Cell] | None = None,
        *,
        margin: int = 28,
        avoid: pygame.Vector2 | None = None,
        min_distance: float = 0.0,
    ) -> pygame.Vector2:
        cells = list(allowed_cells or self.chambers.keys())
        if not cells:
            return self.player_spawn.copy()
        for _ in range(max(8, len(cells) * 4)):
            cell = rng.choice(cells)
            chamber = self.chambers[cell]
            inset = chamber.rect.inflate(-margin * 2, -margin * 2)
            if inset.width <= 12 or inset.height <= 12:
                inset = chamber.rect.inflate(-14, -14)
            pos = pygame.Vector2(
                rng.randint(inset.left, max(inset.left, inset.right - 1)),
                rng.randint(inset.top, max(inset.top, inset.bottom - 1)),
            )
            if avoid is not None and pos.distance_to(avoid) < min_distance:
                continue
            return pos
        return self.chambers[cells[0]].center.copy()


@dataclass(frozen=True)
class FloorRoom:
    room_id: int
    coord: GridPos
    room_type: str
    difficulty: int
    neighbors: dict[str, int]
    layout: RoomLayout


@dataclass
class FloorMap:
    floor_index: int
    rooms: dict[int, FloorRoom]
    start_room_id: int
    boss_room_id: int


LAYOUT_TEMPLATES = (
    {
        "name": "\u4e2d\u592e\u5e7f\u5385",
        "family": "single",
        "grid": (1, 1),
        "spawn": (0, 0),
        "cells": ((0, 0),),
        "links": (),
    },
    {
        "name": "\u53cc\u5385\u5e76\u5217",
        "family": "grid",
        "grid": (2, 2),
        "spawn": (0, 0),
        "cells": ((0, 0), (1, 0), (0, 1), (1, 1)),
        "links": (((0, 0), (1, 0)), ((0, 0), (0, 1)), ((1, 0), (1, 1)), ((0, 1), (1, 1))),
    },
    {
        "name": "\u6298\u89d2\u63a8\u8fdb",
        "family": "grid",
        "grid": (2, 2),
        "spawn": (0, 0),
        "cells": ((0, 0), (1, 0), (1, 1)),
        "links": (((0, 0), (1, 0)), ((1, 0), (1, 1))),
    },
    {
        "name": "\u53cc\u7ebf\u56de\u5eca",
        "family": "grid",
        "grid": (2, 2),
        "spawn": (0, 1),
        "cells": ((0, 0), (1, 0), (0, 1), (1, 1)),
        "links": (((0, 0), (1, 0)), ((0, 1), (1, 1)), ((0, 0), (0, 1))),
    },
    {
        "name": "\u516d\u683c\u8054\u52a8",
        "family": "grid",
        "grid": (2, 3),
        "spawn": (0, 1),
        "cells": ((0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)),
        "links": (
            ((0, 0), (1, 0)),
            ((0, 0), (0, 1)),
            ((1, 0), (1, 1)),
            ((0, 1), (1, 1)),
            ((0, 1), (0, 2)),
            ((1, 1), (1, 2)),
            ((0, 2), (1, 2)),
        ),
    },
    {
        "name": "\u7eb5\u6df1\u5de5\u6bb5",
        "family": "grid",
        "grid": (2, 3),
        "spawn": (0, 0),
        "cells": ((0, 0), (1, 0), (1, 1), (0, 1), (0, 2), (1, 2)),
        "links": (((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 2)), ((0, 2), (1, 2))),
    },
    {
        "name": "\u8ff7\u5bab\u56de\u8def",
        "family": "maze",
        "grid": (3, 3),
        "spawn": (0, 1),
        "cells": ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)),
        "links": (
            ((0, 1), (1, 1)),
            ((1, 1), (1, 0)),
            ((1, 0), (2, 0)),
            ((2, 0), (2, 1)),
            ((2, 1), (1, 1)),
            ((1, 1), (1, 2)),
            ((1, 2), (0, 2)),
            ((0, 2), (0, 1)),
            ((1, 2), (2, 2)),
        ),
    },
)

SPECIAL_TAG_COLORS = {
    "reactor": ((86, 118, 150), (132, 240, 255)),
    "toxic": ((70, 96, 64), (116, 210, 120)),
    "bullet": ((124, 88, 56), (255, 188, 102)),
    "crate": ((108, 82, 58), (206, 162, 108)),
    "wall": ((56, 60, 82), (136, 144, 170)),
    "cover": ((86, 78, 66), (184, 154, 110)),
}


def build_stitched_layout(
    arena: pygame.Rect,
    room_index: int,
    rng: random.Random,
    door_dirs: tuple[str, ...] | list[str] | None = None,
) -> RoomLayout:
    template = _choose_layout_template(room_index, len(door_dirs or ()), rng)
    theme = _choose_room_theme(room_index, rng)
    cols, rows = template["grid"]
    used_cells = set(template["cells"])
    linked_pairs = {frozenset(link) for link in template["links"]}

    shell = arena.inflate(-92, -80)
    x_edges = _split_edges(shell.left, shell.right, cols)
    y_edges = _split_edges(shell.top, shell.bottom, rows)
    cell_bounds = {
        (col, row): pygame.Rect(
            x_edges[col],
            y_edges[row],
            x_edges[col + 1] - x_edges[col],
            y_edges[row + 1] - y_edges[row],
        )
        for row in range(rows)
        for col in range(cols)
    }

    chambers: dict[Cell, Chamber] = {}
    for cell in used_cells:
        bounds = cell_bounds[cell]
        if template["family"] == "single":
            rect = bounds.inflate(-38, -34).clip(bounds.inflate(-10, -10))
        elif template["family"] == "maze":
            rect = _make_chamber_rect(bounds, rng, inset_range=(16, 24), min_size=(110, 92))
        else:
            rect = _make_chamber_rect(bounds, rng)
        chambers[cell] = Chamber(cell=cell, rect=rect, center=pygame.Vector2(rect.center))

    obstacles: list[RoomObstacle] = []
    doorways: list[pygame.Rect] = []
    door_centers: dict[frozenset[Cell], pygame.Vector2] = {}
    wall_thickness = 18
    door_size = 108 if template["family"] != "maze" else 82

    if template["family"] != "single":
        wall_fill, wall_border = SPECIAL_TAG_COLORS["wall"]
        for row in range(rows):
            for col in range(cols - 1):
                left = (col, row)
                right = (col + 1, row)
                if left not in used_cells and right not in used_cells:
                    continue
                boundary = cell_bounds[left]
                y0 = boundary.top + 16
                y1 = boundary.bottom - 16
                x = boundary.right
                pair = frozenset((left, right))
                if left in used_cells and right in used_cells and pair in linked_pairs:
                    door_top = _centered_span(y0, y1, door_size, rng)
                    _append_wall_split_vertical(obstacles, doorways, door_centers, pair, x, y0, y1, door_top, door_size, wall_thickness)
                else:
                    obstacles.append(
                        RoomObstacle(
                            pygame.Rect(x - wall_thickness // 2, y0, wall_thickness, y1 - y0),
                            tag="wall",
                            fill_color=wall_fill,
                            border_color=wall_border,
                        )
                    )

        for col in range(cols):
            for row in range(rows - 1):
                top = (col, row)
                bottom = (col, row + 1)
                if top not in used_cells and bottom not in used_cells:
                    continue
                boundary = cell_bounds[top]
                x0 = boundary.left + 16
                x1 = boundary.right - 16
                y = boundary.bottom
                pair = frozenset((top, bottom))
                if top in used_cells and bottom in used_cells and pair in linked_pairs:
                    door_left = _centered_span(x0, x1, door_size, rng)
                    _append_wall_split_horizontal(obstacles, doorways, door_centers, pair, y, x0, x1, door_left, door_size, wall_thickness)
                else:
                    obstacles.append(
                        RoomObstacle(
                            pygame.Rect(x0, y - wall_thickness // 2, x1 - x0, wall_thickness),
                            tag="wall",
                            fill_color=wall_fill,
                            border_color=wall_border,
                        )
                    )

    for cell in _select_feature_cells(template, room_index, theme, rng):
        chamber = chambers[cell]
        for obstacle in _make_cover_set(chamber, theme, rng, room_index, template["family"]):
            if chamber.rect.inflate(-18, -18).contains(obstacle.rect):
                obstacles.append(obstacle)

    links: dict[Cell, list[Cell]] = {cell: [] for cell in used_cells}
    for a, b in template["links"]:
        if a in links and b in links:
            links[a].append(b)
            links[b].append(a)

    spawn_cell = template["spawn"]
    enemy_cells = tuple(
        sorted(
            (cell for cell in used_cells if cell != spawn_cell),
            key=lambda cell: chambers[cell].center.distance_squared_to(chambers[spawn_cell].center),
            reverse=True,
        )
    ) or (spawn_cell,)
    screen_doors, door_entries = _build_screen_doors(arena, door_dirs or ())
    return RoomLayout(
        name=template["name"],
        theme=theme,
        obstacles=obstacles,
        doorways=doorways,
        chambers=chambers,
        links={cell: tuple(neighbors) for cell, neighbors in links.items()},
        door_centers=door_centers,
        player_spawn=chambers[spawn_cell].center.copy(),
        enemy_cells=enemy_cells,
        pickup_cells=tuple(used_cells),
        screen_doors=screen_doors,
        door_entries=door_entries,
    )


def build_floor_map(arena: pygame.Rect, floor_index: int, base_difficulty: int, rng: random.Random) -> FloorMap:
    main_path, branches = _generate_floor_graph(rng)
    room_types: dict[GridPos, str] = {
        main_path[0]: "start",
        main_path[1]: "combat",
        main_path[2]: "combat",
        main_path[3]: "elite",
        main_path[4]: "boss",
    }
    room_types.update(branches)

    coord_to_id = {coord: idx + 1 for idx, coord in enumerate(room_types)}
    distances = _distance_map(main_path, branches)
    rooms: dict[int, FloorRoom] = {}
    for coord, room_type in room_types.items():
        room_id = coord_to_id[coord]
        neighbors: dict[str, int] = {}
        for direction, offset in DIRECTION_OFFSETS.items():
            nxt = (coord[0] + offset[0], coord[1] + offset[1])
            if nxt in coord_to_id:
                neighbors[direction] = coord_to_id[nxt]
        difficulty = base_difficulty + distances.get(coord, 0)
        if room_type == "elite":
            difficulty += 1
        elif room_type == "boss":
            difficulty += 2
        layout = build_stitched_layout(arena, difficulty + floor_index, rng, tuple(neighbors))
        rooms[room_id] = FloorRoom(
            room_id=room_id,
            coord=coord,
            room_type=room_type,
            difficulty=difficulty,
            neighbors=neighbors,
            layout=layout,
        )
    return FloorMap(floor_index=floor_index, rooms=rooms, start_room_id=coord_to_id[main_path[0]], boss_room_id=coord_to_id[main_path[-1]])


def _split_edges(start: int, end: int, parts: int) -> list[int]:
    length = end - start
    return [start + round(length * idx / parts) for idx in range(parts + 1)]


def _append_wall_split_vertical(
    obstacles: list[RoomObstacle],
    doorways: list[pygame.Rect],
    door_centers: dict[frozenset[Cell], pygame.Vector2],
    pair: frozenset[Cell],
    x: int,
    y0: int,
    y1: int,
    door_top: int,
    door_size: int,
    wall_thickness: int,
) -> None:
    wall_fill, wall_border = SPECIAL_TAG_COLORS["wall"]
    top_rect = pygame.Rect(x - wall_thickness // 2, y0, wall_thickness, max(0, door_top - y0))
    bottom_start = door_top + door_size
    bottom_rect = pygame.Rect(x - wall_thickness // 2, bottom_start, wall_thickness, max(0, y1 - bottom_start))
    if top_rect.height > 0:
        obstacles.append(RoomObstacle(top_rect, tag="wall", fill_color=wall_fill, border_color=wall_border))
    if bottom_rect.height > 0:
        obstacles.append(RoomObstacle(bottom_rect, tag="wall", fill_color=wall_fill, border_color=wall_border))
    door = pygame.Rect(x - wall_thickness // 2 + 3, door_top, wall_thickness - 6, door_size)
    doorways.append(door)
    door_centers[pair] = pygame.Vector2(door.center)


def _append_wall_split_horizontal(
    obstacles: list[RoomObstacle],
    doorways: list[pygame.Rect],
    door_centers: dict[frozenset[Cell], pygame.Vector2],
    pair: frozenset[Cell],
    y: int,
    x0: int,
    x1: int,
    door_left: int,
    door_size: int,
    wall_thickness: int,
) -> None:
    wall_fill, wall_border = SPECIAL_TAG_COLORS["wall"]
    left_rect = pygame.Rect(x0, y - wall_thickness // 2, max(0, door_left - x0), wall_thickness)
    right_start = door_left + door_size
    right_rect = pygame.Rect(right_start, y - wall_thickness // 2, max(0, x1 - right_start), wall_thickness)
    if left_rect.width > 0:
        obstacles.append(RoomObstacle(left_rect, tag="wall", fill_color=wall_fill, border_color=wall_border))
    if right_rect.width > 0:
        obstacles.append(RoomObstacle(right_rect, tag="wall", fill_color=wall_fill, border_color=wall_border))
    door = pygame.Rect(door_left, y - wall_thickness // 2 + 3, door_size, wall_thickness - 6)
    doorways.append(door)
    door_centers[pair] = pygame.Vector2(door.center)


def _build_screen_doors(
    arena: pygame.Rect,
    door_dirs: tuple[str, ...] | list[str],
) -> tuple[dict[str, pygame.Rect], dict[str, pygame.Vector2]]:
    door_width = 112
    door_height = 26
    depth = 76
    doors: dict[str, pygame.Rect] = {}
    entries: dict[str, pygame.Vector2] = {}
    for direction in door_dirs:
        if direction == "north":
            rect = pygame.Rect(0, 0, door_width, door_height)
            rect.midtop = (arena.centerx, arena.top + 4)
            entries[direction] = pygame.Vector2(arena.centerx, arena.top + depth)
        elif direction == "south":
            rect = pygame.Rect(0, 0, door_width, door_height)
            rect.midbottom = (arena.centerx, arena.bottom - 4)
            entries[direction] = pygame.Vector2(arena.centerx, arena.bottom - depth)
        elif direction == "west":
            rect = pygame.Rect(0, 0, door_height, door_width)
            rect.midleft = (arena.left + 4, arena.centery)
            entries[direction] = pygame.Vector2(arena.left + depth, arena.centery)
        else:
            rect = pygame.Rect(0, 0, door_height, door_width)
            rect.midright = (arena.right - 4, arena.centery)
            entries[direction] = pygame.Vector2(arena.right - depth, arena.centery)
        doors[direction] = rect
    return doors, entries


def _generate_floor_graph(rng: random.Random) -> tuple[list[GridPos], dict[GridPos, str]]:
    while True:
        current = (0, 0)
        used = {current}
        main_path = [current]
        while len(main_path) < 5:
            options = []
            for direction in DIRECTIONS:
                dx, dy = DIRECTION_OFFSETS[direction]
                nxt = (current[0] + dx, current[1] + dy)
                if nxt in used or abs(nxt[0]) > 3 or abs(nxt[1]) > 3:
                    continue
                options.append(nxt)
            if not options:
                break
            current = rng.choice(options)
            used.add(current)
            main_path.append(current)
        if len(main_path) < 5:
            continue

        branches: dict[GridPos, str] = {}
        for room_type, candidates in (("shop", (1, 2)), ("treasure", (2, 3))):
            placed = False
            indices = list(candidates)
            rng.shuffle(indices)
            for idx in indices:
                base = main_path[idx]
                options = []
                for direction in DIRECTIONS:
                    dx, dy = DIRECTION_OFFSETS[direction]
                    nxt = (base[0] + dx, base[1] + dy)
                    if nxt in used or abs(nxt[0]) > 3 or abs(nxt[1]) > 3:
                        continue
                    options.append(nxt)
                if options:
                    chosen = rng.choice(options)
                    used.add(chosen)
                    branches[chosen] = room_type
                    placed = True
                    break
            if not placed:
                break
        if len(branches) < 2:
            continue
        if rng.random() < 0.35:
            extra_candidates = [main_path[idx] for idx in (1, 2, 3)]
            rng.shuffle(extra_candidates)
            for base in extra_candidates:
                options = []
                for direction in DIRECTIONS:
                    dx, dy = DIRECTION_OFFSETS[direction]
                    nxt = (base[0] + dx, base[1] + dy)
                    if nxt in used or abs(nxt[0]) > 3 or abs(nxt[1]) > 3:
                        continue
                    options.append(nxt)
                if options:
                    branches[rng.choice(options)] = "combat"
                    break
        return main_path, branches


def _distance_map(main_path: list[GridPos], branches: dict[GridPos, str]) -> dict[GridPos, int]:
    distances = {coord: idx for idx, coord in enumerate(main_path)}
    for coord, room_type in branches.items():
        for base_idx, base in enumerate(main_path[1:-1], 1):
            if abs(coord[0] - base[0]) + abs(coord[1] - base[1]) == 1:
                distances[coord] = base_idx + (1 if room_type in {"treasure", "combat"} else 0)
                break
    return distances


def _choose_layout_template(room_index: int, door_count: int, rng: random.Random) -> dict:
    if room_index <= 2:
        pool = LAYOUT_TEMPLATES[:4]
    elif door_count >= 3:
        pool = (LAYOUT_TEMPLATES[1], LAYOUT_TEMPLATES[3], LAYOUT_TEMPLATES[4], LAYOUT_TEMPLATES[6])
    elif room_index >= 7:
        pool = (LAYOUT_TEMPLATES[0], LAYOUT_TEMPLATES[4], LAYOUT_TEMPLATES[5], LAYOUT_TEMPLATES[6])
    else:
        pool = LAYOUT_TEMPLATES
    return rng.choice(pool)


def _choose_room_theme(room_index: int, rng: random.Random) -> str:
    if room_index <= 2:
        return rng.choice(ROOM_THEMES[:3])
    if room_index >= 7:
        return rng.choice(ROOM_THEMES[1:])
    return rng.choice(ROOM_THEMES)


def _make_chamber_rect(
    bounds: pygame.Rect,
    rng: random.Random,
    *,
    inset_range: tuple[int, int] = (24, 36),
    min_size: tuple[int, int] = (168, 128),
) -> pygame.Rect:
    inset_x = rng.randint(*inset_range)
    inset_y = rng.randint(max(14, inset_range[0] - 4), max(inset_range[0], inset_range[1] - 2))
    rect = bounds.inflate(-inset_x * 2, -inset_y * 2)
    min_width, min_height = min_size
    if rect.width < min_width:
        rect = pygame.Rect(bounds.centerx - min_width // 2, rect.top, min_width, rect.height)
    if rect.height < min_height:
        rect = pygame.Rect(rect.left, bounds.centery - min_height // 2, rect.width, min_height)
    return rect.clip(bounds.inflate(-12, -12))


def _centered_span(start: int, end: int, size: int, rng: random.Random) -> int:
    span = end - start - size
    if span <= 0:
        return start
    center = start + span // 2
    return center + rng.randint(-12, 12)


def _select_feature_cells(template: dict, room_index: int, theme: str, rng: random.Random) -> list[Cell]:
    cells = [cell for cell in template["cells"] if cell != template["spawn"]] or [template["spawn"]]
    rng.shuffle(cells)
    family = template["family"]
    if family == "single":
        budget = 1 if room_index <= 3 else 2
    elif family == "maze":
        budget = 3 if room_index <= 4 else 4
    elif template["grid"] == (2, 3):
        budget = 3
    else:
        budget = 2 if room_index <= 3 else 3
    if theme == "\u63a9\u4f53\u5de5\u5e26":
        budget += 2
    elif theme in ("\u5c01\u9501\u58c1\u5792", "\u5e9f\u6599\u5806\u573a"):
        budget += 1
    return cells[: min(len(cells), budget)]


def _make_cover_set(chamber: Chamber, theme: str, rng: random.Random, room_index: int, family: str) -> list[RoomObstacle]:
    cx, cy = chamber.center
    hp_base = 30 + room_index * 4
    weak = lambda r, tag="cover": _make_obstacle(r, True, hp_base, tag)
    tough = lambda r, tag="cover": _make_obstacle(r, True, hp_base * 1.45, tag)
    static = lambda r, tag="wall": _make_obstacle(r, False, 0.0, tag)

    patterns_by_theme = {
        "\u5f00\u9614\u8f66\u95f4": (
            [weak(_rect_center(cx, cy, 54, 30))],
            [weak(_rect_center(cx - 42, cy, 26, 38)), weak(_rect_center(cx + 42, cy, 26, 38)), weak(_rect_center(cx, cy - 40, 24, 24), "bullet")],
            _crate_row(chamber.rect, 3, hp_base, offset=-28) + _crate_row(chamber.rect, 3, hp_base, offset=28),
        ),
        "\u63a9\u4f53\u5de5\u5e26": (
            [static(_rect_center(cx, cy - 36, 84, 18), "wall"), weak(_rect_center(cx, cy + 32, 46, 32))],
            _crate_row(chamber.rect, 5 if family != "single" else 6, hp_base, offset=0) + [weak(_rect_center(cx, cy - 42, 24, 24), "bullet")],
            _crate_row(chamber.rect, 4, hp_base, offset=-34) + _crate_row(chamber.rect, 4, hp_base, offset=34),
            [_wall_row(chamber.rect, horizontal=True, destructible=True, hp=hp_base), weak(_rect_center(cx, cy - 44, 24, 24))],
            [_wall_row(chamber.rect, horizontal=False, destructible=True, hp=hp_base * 1.08), weak(_rect_center(cx - 36, cy, 24, 24)), weak(_rect_center(cx + 36, cy, 24, 24))],
        ),
        "\u5e9f\u6599\u5806\u573a": (
            [weak(_rect_center(cx - 34, cy - 20, 26, 26), "toxic"), weak(_rect_center(cx + 10, cy - 4, 22, 22)), weak(_rect_center(cx + 36, cy + 18, 30, 30), "toxic"), weak(_rect_center(cx - 6, cy + 40, 24, 24), "bullet")],
            _crate_row(chamber.rect, 5, hp_base, offset=0, tag="crate") + [weak(_rect_center(cx, cy - 38, 26, 26), "toxic")],
            _crate_row(chamber.rect, 4, hp_base, offset=-28, tag="crate") + [static(_rect_center(cx + 42, cy + 24, 52, 18), "wall"), weak(_rect_center(cx - 48, cy + 24, 24, 24), "toxic")],
        ),
        "\u53cd\u5e94\u5806\u5ba4": (
            [tough(_rect_center(cx, cy, 58, 58), "reactor"), weak(_rect_center(cx - 50, cy + 8, 24, 24)), weak(_rect_center(cx + 50, cy + 8, 24, 24))],
            [static(_rect_center(cx, cy - 42, 72, 18), "wall"), weak(_rect_center(cx - 36, cy + 26, 28, 28), "reactor"), weak(_rect_center(cx + 36, cy + 26, 28, 28)), weak(_rect_center(cx, cy + 44, 24, 24), "bullet")],
            _crate_row(chamber.rect, 4, hp_base, offset=34, tag="crate") + [tough(_rect_center(cx, cy - 36, 38, 38), "reactor")],
        ),
        "\u5c01\u9501\u58c1\u5792": (
            [_wall_row(chamber.rect, horizontal=True, destructible=False), *_crate_row(chamber.rect, 5, hp_base * 0.95, offset=32, tag="crate")],
            [_wall_row(chamber.rect, horizontal=False, destructible=True, hp=hp_base * 1.18), static(_rect_center(cx, cy - 36, 90, 18), "wall"), static(_rect_center(cx, cy + 36, 90, 18), "wall")],
            _crate_row(chamber.rect, 6, hp_base, offset=0, tag="crate"),
        ),
    }
    chosen = list(rng.choice(patterns_by_theme[theme]))
    if family == "maze":
        chosen.extend(_crate_row(chamber.rect, 3, hp_base * 0.92, offset=0, tag="crate"))
    elif family == "single" and theme in ("\u5e9f\u6599\u5806\u573a", "\u63a9\u4f53\u5de5\u5e26"):
        chosen.extend(_crate_row(chamber.rect, 4, hp_base * 0.9, offset=46, tag="crate"))
    return chosen


def _make_obstacle(rect: pygame.Rect, destructible: bool, hp: float, tag: str) -> RoomObstacle:
    fill, border = SPECIAL_TAG_COLORS.get(tag, SPECIAL_TAG_COLORS["cover"])
    if not destructible and tag in {"normal", "cover"}:
        tag = "wall"
        fill, border = SPECIAL_TAG_COLORS["wall"]
    if destructible and tag in {"reactor", "toxic"}:
        hp *= hazard_profile(tag, rect).hp_scale
    elif destructible and tag == "bullet":
        hp *= 1.0 + min(1.4, rect.width * rect.height / 2200)
    return RoomObstacle(rect, destructible, hp, hp, tag=tag, fill_color=fill, border_color=border)


def _wall_row(rect: pygame.Rect, horizontal: bool, destructible: bool, hp: float = 0.0) -> RoomObstacle:
    if horizontal:
        wall = pygame.Rect(rect.left + 24, rect.centery - 10, rect.width - 48, 20)
    else:
        wall = pygame.Rect(rect.centerx - 10, rect.top + 24, 20, rect.height - 48)
    return _make_obstacle(wall, destructible, hp, "wall")


def _crate_row(rect: pygame.Rect, count: int, hp: float, *, offset: int = 0, tag: str = "crate") -> list[RoomObstacle]:
    gap = 8 if count >= 5 else 10
    size = max(20, min(30, (rect.width - 60 - gap * (count - 1)) // count))
    total = count * size + (count - 1) * gap
    start_x = rect.centerx - total // 2
    y = max(rect.top + 18, min(rect.centery - size // 2 + offset, rect.bottom - size - 18))
    return [_make_obstacle(pygame.Rect(start_x + idx * (size + gap), y, size, size), True, hp, tag) for idx in range(count)]


def _rect_center(cx: float, cy: float, w: int, h: int) -> pygame.Rect:
    rect = pygame.Rect(0, 0, w, h)
    rect.center = (int(cx), int(cy))
    return rect
