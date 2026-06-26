from __future__ import annotations

from dataclasses import dataclass

from .model import BOSS, COIN, TRAP, WALL, Maze
from .pathfinding import bfs_path, manhattan


@dataclass(frozen=True)
class MazeDifficulty:
    maze_name: str
    width: int
    height: int
    walkable_cells: int
    shortest_path_length: int
    coin_count: int
    trap_count: int
    boss_count: int
    coin_density: float
    trap_density: float
    dead_end_count: int
    dead_end_ratio: float
    boss_blocking: bool
    score: float
    level: str

    def as_lines(self) -> list[str]:
        return [
            f"地图: {self.maze_name}",
            f"尺寸: {self.height} x {self.width}",
            f"可通行格子: {self.walkable_cells}",
            f"起终点最短路径长度: {self.shortest_path_length}",
            f"金币/陷阱/BOSS: {self.coin_count}/{self.trap_count}/{self.boss_count}",
            f"金币密度: {self.coin_density:.2%}",
            f"陷阱密度: {self.trap_density:.2%}",
            f"死胡同比例: {self.dead_end_ratio:.2%}",
            f"BOSS是否位于最短路径: {'是' if self.boss_blocking else '否'}",
            f"综合难度分: {self.score:.1f} ({self.level})",
        ]


def evaluate_maze(maze: Maze) -> MazeDifficulty:
    walkable = [
        (r, c)
        for r, row in enumerate(maze.matrix)
        for c, tile in enumerate(row)
        if tile != WALL
    ]
    walkable_count = len(walkable)
    shortest = bfs_path(maze, maze.start, maze.end)
    shortest_len = max(0, len(shortest) - 1)
    shortest_set = set(shortest)
    coin_positions = [pos for pos in walkable if maze.tile_at(pos) == COIN]
    trap_positions = [pos for pos in walkable if maze.tile_at(pos) == TRAP]
    boss_positions = [pos for pos in walkable if maze.tile_at(pos) == BOSS]
    dead_ends = [pos for pos in walkable if pos not in (maze.start, maze.end) and len(maze.neighbors(pos)) <= 1]
    boss_blocking = any(pos in shortest_set for pos in boss_positions)

    coin_density = len(coin_positions) / max(1, walkable_count)
    trap_density = len(trap_positions) / max(1, walkable_count)
    dead_end_ratio = len(dead_ends) / max(1, walkable_count)
    path_ratio = shortest_len / max(1, maze.height * maze.width)
    spread = _resource_spread(maze, coin_positions + trap_positions)
    score = (
        path_ratio * 35
        + trap_density * 120
        + dead_end_ratio * 80
        + (18 if boss_blocking else 0)
        + min(20, len(boss_positions) * 8)
        + spread * 18
    )
    if score >= 45:
        level = "困难"
    elif score >= 25:
        level = "中等"
    else:
        level = "简单"

    return MazeDifficulty(
        maze_name=maze.name,
        width=maze.width,
        height=maze.height,
        walkable_cells=walkable_count,
        shortest_path_length=shortest_len,
        coin_count=len(coin_positions),
        trap_count=len(trap_positions),
        boss_count=maze.boss_count(),
        coin_density=coin_density,
        trap_density=trap_density,
        dead_end_count=len(dead_ends),
        dead_end_ratio=dead_end_ratio,
        boss_blocking=boss_blocking,
        score=score,
        level=level,
    )


def _resource_spread(maze: Maze, positions: list[tuple[int, int]]) -> float:
    if not positions:
        return 0.0
    distances = [min(manhattan(pos, maze.start), manhattan(pos, maze.end)) for pos in positions]
    return min(1.0, sum(distances) / max(1, len(distances) * (maze.height + maze.width) / 3))
