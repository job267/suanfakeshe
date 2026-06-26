from __future__ import annotations

from .model import COIN, COIN_VALUE, TRAP, TRAP_VALUE, Candidate, Decision, Maze, Pos
from .pathfinding import astar_path, bfs_path, manhattan


def decide(
    maze: Maze,
    position: Pos,
    collected_coins: set[Pos] | None = None,
    triggered_traps: set[Pos] | None = None,
    radius: int = 1,
    matrix: list[list[int]] | None = None,
) -> Decision:
    collected_coins = collected_coins or set()
    triggered_traps = triggered_traps or set()
    source = matrix or maze.matrix
    traps_to_avoid = {
        pos
        for row_idx, row in enumerate(source)
        for col_idx, tile in enumerate(row)
        if tile == TRAP and (pos := (row_idx, col_idx)) not in triggered_traps
    }

    coin_candidates: list[Candidate] = []
    trap_candidates: list[Candidate] = []

    for pos in maze.view_positions(position, radius=radius):
        tile = maze.tile_at(pos, source)
        if tile == COIN and pos not in collected_coins:
            path = bfs_path(maze, position, pos, matrix=source, blocked=traps_to_avoid)
            reachable = bool(path)
            distance = len(path) - 1 if path else manhattan(position, pos)
            ratio = COIN_VALUE / (distance + 1)
            coin_candidates.append(
                Candidate(pos, COIN, COIN_VALUE, distance, ratio, reachable=reachable)
            )
        elif tile == TRAP and pos not in triggered_traps:
            distance = manhattan(position, pos)
            ratio = TRAP_VALUE / (distance + 1)
            trap_candidates.append(
                Candidate(pos, TRAP, TRAP_VALUE, distance, ratio, reachable=True, excluded=True)
            )

    reachable_coins = [item for item in coin_candidates if item.reachable and item.ratio > 0]
    reachable_coins.sort(
        key=lambda item: (-item.ratio, item.distance, manhattan(item.position, maze.end), item.position)
    )

    if reachable_coins:
        target = reachable_coins[0]
        path = bfs_path(maze, position, target.position, matrix=source, blocked=traps_to_avoid)
        next_pos = path[1] if len(path) > 1 else position
        return Decision(
            next_pos=next_pos,
            coins_in_view=coin_candidates,
            traps_in_view=trap_candidates,
            selected_target=f"金币{target.position} 性价比={target.ratio:.1f}",
            planned_path=path,
            strategy="Greedy",
            reason="视野内存在正收益金币，选择性价比最高目标",
        )

    path_to_end = astar_path(maze, position, maze.end, matrix=source, blocked=traps_to_avoid)
    reason = "视野内无正收益资源，沿A*路径向终点推进"
    if len(path_to_end) <= 1:
        path_to_end = astar_path(maze, position, maze.end, matrix=source)
        reason = "避开陷阱后无路，使用可通行路径向终点推进"

    next_pos = path_to_end[1] if len(path_to_end) > 1 else position
    return Decision(
        next_pos=next_pos,
        coins_in_view=coin_candidates,
        traps_in_view=trap_candidates,
        selected_target="",
        planned_path=path_to_end,
        strategy="Greedy",
        reason=reason,
    )
