from __future__ import annotations

import heapq
from collections import deque
from typing import Iterable

from .model import TRAP, Maze, Pos


def manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _reconstruct(came_from: dict[Pos, Pos | None], goal: Pos) -> list[Pos]:
    if goal not in came_from:
        return []
    path = [goal]
    current = goal
    while came_from[current] is not None:
        current = came_from[current]  # type: ignore[assignment]
        path.append(current)
    path.reverse()
    return path


def bfs_path(
    maze: Maze,
    start: Pos,
    goal: Pos,
    matrix: list[list[int]] | None = None,
    blocked: Iterable[Pos] | None = None,
) -> list[Pos]:
    if start == goal:
        return [start]
    blocked_set = set(blocked or ())
    blocked_set.discard(start)
    blocked_set.discard(goal)
    queue: deque[Pos] = deque([start])
    came_from: dict[Pos, Pos | None] = {start: None}

    while queue:
        current = queue.popleft()
        for nxt in maze.neighbors(current, matrix=matrix, blocked=blocked_set):
            if nxt in came_from:
                continue
            came_from[nxt] = current
            if nxt == goal:
                return _reconstruct(came_from, goal)
            queue.append(nxt)
    return []


def astar_path(
    maze: Maze,
    start: Pos,
    goal: Pos,
    matrix: list[list[int]] | None = None,
    blocked: Iterable[Pos] | None = None,
) -> list[Pos]:
    if start == goal:
        return [start]
    blocked_set = set(blocked or ())
    blocked_set.discard(start)
    blocked_set.discard(goal)

    counter = 0
    frontier: list[tuple[int, int, Pos]] = [(manhattan(start, goal), counter, start)]
    came_from: dict[Pos, Pos | None] = {start: None}
    cost_so_far: dict[Pos, int] = {start: 0}

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current == goal:
            return _reconstruct(came_from, goal)
        for nxt in maze.neighbors(current, matrix=matrix, blocked=blocked_set):
            new_cost = cost_so_far[current] + 1
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                counter += 1
                priority = new_cost + manhattan(nxt, goal)
                heapq.heappush(frontier, (priority, counter, nxt))
                came_from[nxt] = current
    return []


def dijkstra_path(
    maze: Maze,
    start: Pos,
    goal: Pos,
    matrix: list[list[int]] | None = None,
    trap_penalty: int = 25,
    blocked: Iterable[Pos] | None = None,
) -> list[Pos]:
    if start == goal:
        return [start]
    blocked_set = set(blocked or ())
    blocked_set.discard(start)
    blocked_set.discard(goal)
    frontier: list[tuple[int, int, Pos]] = [(0, 0, start)]
    came_from: dict[Pos, Pos | None] = {start: None}
    cost_so_far: dict[Pos, int] = {start: 0}
    counter = 0

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current == goal:
            return _reconstruct(came_from, goal)
        for nxt in maze.neighbors(current, matrix=matrix, blocked=blocked_set):
            tile = maze.tile_at(nxt, matrix)
            step_cost = 1 + (trap_penalty if tile == TRAP else 0)
            new_cost = cost_so_far[current] + step_cost
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                came_from[nxt] = current
                counter += 1
                heapq.heappush(frontier, (new_cost, counter, nxt))
    return []


def next_step_towards(
    maze: Maze,
    start: Pos,
    goal: Pos,
    matrix: list[list[int]] | None = None,
    blocked: Iterable[Pos] | None = None,
    prefer_astar: bool = True,
) -> tuple[Pos, list[Pos]]:
    path = (
        astar_path(maze, start, goal, matrix=matrix, blocked=blocked)
        if prefer_astar
        else bfs_path(maze, start, goal, matrix=matrix, blocked=blocked)
    )
    if len(path) > 1:
        return path[1], path
    return start, path
