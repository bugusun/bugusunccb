from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import pygame

GridCell = tuple[int, int]
CARDINAL_DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONAL_DIRECTIONS = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def circle_intersects_rect(pos: pygame.Vector2, radius: int, rect: pygame.Rect) -> bool:
    nearest_x = max(rect.left, min(pos.x, rect.right))
    nearest_y = max(rect.top, min(pos.y, rect.bottom))
    dx = pos.x - nearest_x
    dy = pos.y - nearest_y
    return dx * dx + dy * dy <= radius * radius


@dataclass
class NavigationField:
    arena: pygame.Rect
    obstacle_rects: tuple[pygame.Rect, ...]
    agent_radius: int
    step: int = 28
    padding: int = 4
    tight_gap_extra: int = 10
    cross_gap_extra: int = 12
    distance_cache_limit: int = 6
    waypoint_cache_limit: int = 96
    walkable: dict[GridCell, pygame.Vector2] = field(init=False, default_factory=dict)
    neighbors: dict[GridCell, tuple[GridCell, ...]] = field(init=False, default_factory=dict)
    distances: dict[GridCell, int] = field(init=False, default_factory=dict)
    cell_costs: dict[GridCell, int] = field(init=False, default_factory=dict)
    distance_cache: dict[GridCell, dict[GridCell, int]] = field(
        init=False, default_factory=dict
    )
    waypoint_cache: dict[tuple[GridCell, GridCell], GridCell] = field(
        init=False, default_factory=dict
    )
    target_cell: GridCell | None = field(init=False, default=None)
    cols: int = field(init=False, default=0)
    rows: int = field(init=False, default=0)
    x_positions: tuple[float, ...] = field(init=False, default_factory=tuple)
    y_positions: tuple[float, ...] = field(init=False, default_factory=tuple)
    inner_arena: pygame.Rect = field(init=False)

    def __post_init__(self) -> None:
        clearance = self.clearance
        self.inner_arena = self.arena.inflate(-clearance * 2, -clearance * 2)
        if self.inner_arena.width <= 0 or self.inner_arena.height <= 0:
            self.inner_arena = pygame.Rect(0, 0, 0, 0)
            return

        self.x_positions = self.build_axis_positions(
            self.inner_arena.left, self.inner_arena.right
        )
        self.y_positions = self.build_axis_positions(
            self.inner_arena.top, self.inner_arena.bottom
        )
        self.cols = len(self.x_positions)
        self.rows = len(self.y_positions)

        for gx in range(self.cols):
            for gy in range(self.rows):
                point = pygame.Vector2(
                    self.x_positions[gx],
                    self.y_positions[gy],
                )
                if self.is_walkable_point(point):
                    cell = (gx, gy)
                    self.walkable[cell] = point
                    self.cell_costs[cell] = self.compute_cell_cost(point)

        for cell in self.walkable:
            next_cells: list[GridCell] = []
            for dx, dy in CARDINAL_DIRECTIONS:
                nxt = (cell[0] + dx, cell[1] + dy)
                if nxt in self.walkable:
                    next_cells.append(nxt)
            for dx, dy in DIAGONAL_DIRECTIONS:
                nxt = (cell[0] + dx, cell[1] + dy)
                side_x = (cell[0] + dx, cell[1])
                side_y = (cell[0], cell[1] + dy)
                if (
                    nxt in self.walkable
                    and side_x in self.walkable
                    and side_y in self.walkable
                ):
                    next_cells.append(nxt)
            self.neighbors[cell] = tuple(next_cells)

    @property
    def clearance(self) -> int:
        return self.agent_radius + self.padding

    def build_axis_positions(self, start: int, end: int) -> tuple[float, ...]:
        span = max(0.0, float(end - start))
        if span <= 0:
            return (float(start),)
        count = max(2, int(math.floor(span / self.step)) + 1)
        if count == 2:
            return (float(start), float(end))
        gap = span / (count - 1)
        return tuple(float(start) + gap * index for index in range(count))

    def is_walkable_point(self, point: pygame.Vector2) -> bool:
        if self.inner_arena.width <= 0 or self.inner_arena.height <= 0:
            return False
        if not self.inner_arena.collidepoint(point.x, point.y):
            return False
        if any(
            circle_intersects_rect(point, self.clearance, rect)
            for rect in self.obstacle_rects
        ):
            return False
        return not self.is_tight_gap_point(point)

    def axis_clearances(
        self, point: pygame.Vector2
    ) -> tuple[float, float, float, float]:
        if self.inner_arena.width <= 0 or self.inner_arena.height <= 0:
            return 0.0, 0.0, 0.0, 0.0
        clearance = self.clearance
        left = max(0.0, point.x - self.inner_arena.left)
        right = max(0.0, self.inner_arena.right - point.x)
        top = max(0.0, point.y - self.inner_arena.top)
        bottom = max(0.0, self.inner_arena.bottom - point.y)

        for rect in self.obstacle_rects:
            expanded = rect.inflate(clearance * 2, clearance * 2)
            if expanded.top <= point.y <= expanded.bottom:
                if expanded.right <= point.x:
                    left = min(left, max(0.0, point.x - expanded.right))
                elif expanded.left >= point.x:
                    right = min(right, max(0.0, expanded.left - point.x))
            if expanded.left <= point.x <= expanded.right:
                if expanded.bottom <= point.y:
                    top = min(top, max(0.0, point.y - expanded.bottom))
                elif expanded.top >= point.y:
                    bottom = min(bottom, max(0.0, expanded.top - point.y))

        return left, right, top, bottom

    def axis_gap_spans(self, point: pygame.Vector2) -> tuple[float, float]:
        left, right, top, bottom = self.axis_clearances(point)
        return left + right, top + bottom

    def is_cross_gap_point(self, point: pygame.Vector2) -> bool:
        left, right, top, bottom = self.axis_clearances(point)
        cross_limit = self.clearance + self.cross_gap_extra
        tight_x = left + right < self.clearance * 2 + self.cross_gap_extra + self.step * 0.5
        tight_y = top + bottom < self.clearance * 2 + self.cross_gap_extra + self.step * 0.5
        return (
            min(left, right) < cross_limit
            and min(top, bottom) < cross_limit
            and tight_x
            and tight_y
        )

    def is_tight_gap_point(self, point: pygame.Vector2) -> bool:
        gap_x, gap_y = self.axis_gap_spans(point)
        tight_gap = self.clearance * 2 + self.tight_gap_extra
        return (gap_x < tight_gap and gap_y < tight_gap) or self.is_cross_gap_point(
            point
        )

    def compute_cell_cost(self, point: pygame.Vector2) -> int:
        left, right, top, bottom = self.axis_clearances(point)
        gap_x = left + right
        gap_y = top + bottom
        tight_span = min(gap_x, gap_y)
        open_span = max(gap_x, gap_y)
        preferred_span = self.clearance * 2.6 + self.step
        penalty = 0
        if tight_span < preferred_span:
            penalty += 6
        elif tight_span < preferred_span + self.step:
            penalty += 3
        if open_span < preferred_span + self.step * 1.4:
            penalty += 2
        if (
            min(left, right) < self.clearance + self.cross_gap_extra
            and min(top, bottom) < self.clearance + self.cross_gap_extra
        ):
            penalty += 8
        return penalty

    def closest_walkable_cell(self, pos: pygame.Vector2) -> GridCell | None:
        if not self.walkable:
            return None
        base = self.grid_cell_from_pos(pos)
        if base in self.walkable:
            return base

        best: GridCell | None = None
        best_distance = float("inf")
        for radius in range(1, 4):
            for gx in range(base[0] - radius, base[0] + radius + 1):
                for gy in range(base[1] - radius, base[1] + radius + 1):
                    if (
                        gx < 0
                        or gy < 0
                        or gx >= self.cols
                        or gy >= self.rows
                        or max(abs(gx - base[0]), abs(gy - base[1])) != radius
                    ):
                        continue
                    cell = (gx, gy)
                    point = self.walkable.get(cell)
                    if point is None:
                        continue
                    distance = point.distance_squared_to(pos)
                    if distance < best_distance:
                        best = cell
                        best_distance = distance
            if best is not None:
                return best

        return min(
            self.walkable,
            key=lambda cell: self.walkable[cell].distance_squared_to(pos),
        )

    def grid_cell_from_pos(self, pos: pygame.Vector2) -> GridCell:
        if self.cols <= 1 or not self.x_positions:
            gx = 0
        else:
            gx = min(
                range(self.cols),
                key=lambda index: abs(self.x_positions[index] - pos.x),
            )
        if self.rows <= 1 or not self.y_positions:
            gy = 0
        else:
            gy = min(
                range(self.rows),
                key=lambda index: abs(self.y_positions[index] - pos.y),
            )
        return gx, gy

    def rebuild_distances(self, goal: pygame.Vector2) -> None:
        goal_cell = self.closest_walkable_cell(goal)
        if goal_cell is None:
            self.target_cell = None
            self.distances = {}
            return

        cached = self.distance_cache.get(goal_cell)
        self.target_cell = goal_cell
        if cached is not None:
            self.distances = cached
            return

        distances: dict[GridCell, int] = {goal_cell: 0}
        frontier: list[tuple[int, GridCell]] = [(0, goal_cell)]
        while frontier:
            cost, cell = heapq.heappop(frontier)
            if cost != distances.get(cell):
                continue
            for nxt in self.neighbors.get(cell, ()):
                move_cost = self.neighbor_step_cost(cell, nxt) + self.cell_costs.get(nxt, 0)
                new_cost = cost + move_cost
                if new_cost >= distances.get(nxt, 10**9):
                    continue
                distances[nxt] = new_cost
                heapq.heappush(frontier, (new_cost, nxt))

        self.distances = distances
        self.distance_cache[goal_cell] = distances
        while len(self.distance_cache) > self.distance_cache_limit:
            oldest = next(iter(self.distance_cache))
            if oldest == goal_cell and len(self.distance_cache) > 1:
                oldest = next(iter({key: None for key in self.distance_cache if key != goal_cell}))
            self.distance_cache.pop(oldest, None)
        stale_waypoints = [
            key for key in self.waypoint_cache if key[1] not in self.distance_cache
        ]
        for key in stale_waypoints:
            self.waypoint_cache.pop(key, None)

    def neighbor_step_cost(self, start: GridCell, end: GridCell) -> int:
        return 14 if start[0] != end[0] and start[1] != end[1] else 10

    def next_waypoint(self, start: pygame.Vector2, goal: pygame.Vector2) -> pygame.Vector2 | None:
        if not self.walkable:
            return None
        self.rebuild_distances(goal)
        if self.target_cell is None:
            return None
        start_cell = self.closest_walkable_cell(start)
        if start_cell is None:
            return None
        current_distance = self.distances.get(start_cell)
        if current_distance is None:
            reachable = [cell for cell in self.walkable if cell in self.distances]
            if not reachable:
                return None
            best = min(
                reachable,
                key=lambda cell: (
                    self.walkable[cell].distance_squared_to(start),
                    self.distances.get(cell, 10**9),
                    self.cell_costs.get(cell, 0),
                ),
            )
            return self.walkable[best].copy()
        if start_cell == self.target_cell:
            return goal.copy()

        cache_key = (start_cell, self.target_cell)
        cached_waypoint = self.waypoint_cache.get(cache_key)
        if cached_waypoint in self.walkable and self.distances.get(
            cached_waypoint, 10**9
        ) <= current_distance:
            return self.walkable[cached_waypoint].copy()

        best_neighbor: GridCell | None = None
        best_distance = current_distance
        for nxt in self.neighbors.get(start_cell, ()):
            distance = self.distances.get(nxt)
            if distance is None or distance > best_distance:
                continue
            if best_neighbor is None:
                best_neighbor = nxt
                best_distance = distance
                continue
            current = self.walkable[nxt]
            chosen = self.walkable[best_neighbor]
            if (
                distance < best_distance
                or self.cell_costs.get(nxt, 0) < self.cell_costs.get(best_neighbor, 0)
                or current.distance_squared_to(goal) < chosen.distance_squared_to(goal)
            ):
                best_neighbor = nxt
                best_distance = distance
        if best_neighbor is None:
            return self.walkable[start_cell].copy()

        lookahead = best_neighbor
        lookahead_distance = best_distance
        for _ in range(2):
            next_options = [
                nxt
                for nxt in self.neighbors.get(lookahead, ())
                if self.distances.get(nxt, lookahead_distance) < lookahead_distance
            ]
            if not next_options:
                break
            lookahead = min(
                next_options,
                key=lambda cell: (
                    self.distances.get(cell, 10**9),
                    self.cell_costs.get(cell, 0),
                    self.walkable[cell].distance_squared_to(goal),
                ),
            )
            lookahead_distance = self.distances.get(lookahead, lookahead_distance)
        self.waypoint_cache[cache_key] = lookahead
        while len(self.waypoint_cache) > self.waypoint_cache_limit:
            self.waypoint_cache.pop(next(iter(self.waypoint_cache)), None)
        return self.walkable[lookahead].copy()
