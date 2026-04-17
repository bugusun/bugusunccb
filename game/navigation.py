from __future__ import annotations

from collections import deque
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
    walkable: dict[GridCell, pygame.Vector2] = field(init=False, default_factory=dict)
    neighbors: dict[GridCell, tuple[GridCell, ...]] = field(init=False, default_factory=dict)
    distances: dict[GridCell, int] = field(init=False, default_factory=dict)
    target_cell: GridCell | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        cols = max(1, int((self.arena.width - self.step) / self.step) + 1)
        rows = max(1, int((self.arena.height - self.step) / self.step) + 1)
        origin_x = self.arena.left + self.step / 2
        origin_y = self.arena.top + self.step / 2

        for gx in range(cols):
            for gy in range(rows):
                point = pygame.Vector2(origin_x + gx * self.step, origin_y + gy * self.step)
                if self.is_walkable_point(point):
                    self.walkable[(gx, gy)] = point

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

    def is_walkable_point(self, point: pygame.Vector2) -> bool:
        clearance = self.agent_radius + self.padding
        inner_arena = self.arena.inflate(-clearance * 2, -clearance * 2)
        if inner_arena.width <= 0 or inner_arena.height <= 0:
            return False
        if not inner_arena.collidepoint(point.x, point.y):
            return False
        return not any(circle_intersects_rect(point, clearance, rect) for rect in self.obstacle_rects)

    def closest_walkable_cell(self, pos: pygame.Vector2) -> GridCell | None:
        if not self.walkable:
            return None
        return min(
            self.walkable,
            key=lambda cell: self.walkable[cell].distance_squared_to(pos),
        )

    def rebuild_distances(self, goal: pygame.Vector2) -> None:
        goal_cell = self.closest_walkable_cell(goal)
        if goal_cell == self.target_cell:
            return
        self.target_cell = goal_cell
        self.distances.clear()
        if goal_cell is None:
            return
        frontier: deque[GridCell] = deque([goal_cell])
        self.distances[goal_cell] = 0
        while frontier:
            cell = frontier.popleft()
            base_distance = self.distances[cell] + 1
            for nxt in self.neighbors.get(cell, ()):
                if nxt in self.distances:
                    continue
                self.distances[nxt] = base_distance
                frontier.append(nxt)

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
                ),
            )
            return self.walkable[best].copy()
        if start_cell == self.target_cell:
            return goal.copy()
        best_neighbor: GridCell | None = None
        best_distance = current_distance
        for nxt in self.neighbors.get(start_cell, ()):
            distance = self.distances.get(nxt)
            if distance is None or distance >= best_distance:
                continue
            if best_neighbor is None:
                best_neighbor = nxt
                best_distance = distance
                continue
            current = self.walkable[nxt]
            chosen = self.walkable[best_neighbor]
            if distance < best_distance or current.distance_squared_to(goal) < chosen.distance_squared_to(goal):
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
                    self.walkable[cell].distance_squared_to(goal),
                ),
            )
            lookahead_distance = self.distances.get(lookahead, lookahead_distance)
        return self.walkable[lookahead].copy()
