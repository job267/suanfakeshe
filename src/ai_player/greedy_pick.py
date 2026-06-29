from __future__ import annotations

from .boss_battle import boss_battle_optimal
from .model import BOSS, COIN, COIN_VALUE, TRAP, TRAP_COIN_COST, TRAP_VALUE, Candidate, Decision, Maze, Pos
from .pathfinding import dijkstra_path, manhattan


TRAP_ROUTE_PENALTY = abs(TRAP_VALUE) + TRAP_COIN_COST * COIN_VALUE


def decide(
    maze: Maze,
    position: Pos,
    collected_coins: set[Pos] | None = None,
    triggered_traps: set[Pos] | None = None,
    radius: int = 1,
    matrix: list[list[int]] | None = None,
    coin_balance: int = 0,
) -> Decision:
    collected_coins = collected_coins or set()
    triggered_traps = triggered_traps or set()
    source = matrix or maze.matrix
    active_bosses = _active_boss_positions(maze, source)

    coin_candidates: list[Candidate] = []
    trap_candidates: list[Candidate] = []

    for pos in maze.view_positions(position, radius=radius):
        tile = maze.tile_at(pos, source)
        if tile == COIN and pos not in collected_coins:
            path = dijkstra_path(
                maze,
                position,
                pos,
                matrix=source,
                trap_penalty=TRAP_ROUTE_PENALTY,
                blocked=active_bosses,
            )
            reachable = bool(path)
            distance = len(path) - 1 if path else manhattan(position, pos)
            trap_penalty = _trap_penalty_on_path(maze, path, source, triggered_traps)
            ratio = (COIN_VALUE - trap_penalty) / (distance + 1)
            coin_candidates.append(
                Candidate(pos, COIN, COIN_VALUE, distance, ratio, reachable=reachable)
            )
        elif tile == TRAP and pos not in triggered_traps:
            distance = manhattan(position, pos)
            ratio = -(abs(TRAP_VALUE) + TRAP_COIN_COST * COIN_VALUE) / (distance + 1)
            trap_candidates.append(
                Candidate(pos, TRAP, TRAP_VALUE, distance, ratio, reachable=True, excluded=False)
            )

    reachable_coins = [item for item in coin_candidates if item.reachable and item.ratio > 0]
    reachable_coins.sort(
        key=lambda item: (-item.ratio, item.distance, manhattan(item.position, maze.end), item.position)
    )

    if reachable_coins:
        target = reachable_coins[0]
        path = dijkstra_path(
            maze,
            position,
            target.position,
            matrix=source,
            trap_penalty=TRAP_ROUTE_PENALTY,
            blocked=active_bosses,
        )
        next_pos = path[1] if len(path) > 1 else position
        return Decision(
            next_pos=next_pos,
            coins_in_view=coin_candidates,
            traps_in_view=trap_candidates,
            selected_target=f"金币{target.position} 性价比={target.ratio:.1f}",
            planned_path=path,
            strategy="Greedy",
            reason="视野内存在正收益金币，按金币收益扣除陷阱惩罚后选择最高目标",
        )

    path_avoiding_boss = dijkstra_path(
        maze,
        position,
        maze.end,
        matrix=source,
        trap_penalty=TRAP_ROUTE_PENALTY,
        blocked=active_bosses,
    )
    if path_avoiding_boss:
        path_to_end = path_avoiding_boss
        boss_reserve = 0
        reason = "视野内无正收益资源，绕开BOSS并按陷阱惩罚路径向终点推进"
    else:
        path_to_end = dijkstra_path(maze, position, maze.end, matrix=source, trap_penalty=TRAP_ROUTE_PENALTY)
        boss_reserve = _boss_revive_cost_on_path(maze, path_to_end, source)
        reason = "终点路径必须经过BOSS，按陷阱惩罚路径推进"

    if coin_balance < boss_reserve:
        reserve_decision = _reserve_coin_decision(
            maze,
            position,
            source,
            collected_coins,
            triggered_traps,
            active_bosses,
            coin_candidates,
            trap_candidates,
            coin_balance,
            boss_reserve,
        )
        if reserve_decision is not None:
            return reserve_decision

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


def _reserve_coin_decision(
    maze: Maze,
    position: Pos,
    source: list[list[int]],
    collected_coins: set[Pos],
    triggered_traps: set[Pos],
    active_bosses: set[Pos],
    coin_candidates: list[Candidate],
    trap_candidates: list[Candidate],
    coin_balance: int,
    boss_reserve: int,
) -> Decision | None:
    reserve_candidates: list[tuple[float, int, Pos, list[Pos]]] = []
    for row_idx, row in enumerate(source):
        for col_idx, tile in enumerate(row):
            pos = (row_idx, col_idx)
            if tile != COIN or pos in collected_coins:
                continue
            path = dijkstra_path(
                maze,
                position,
                pos,
                matrix=source,
                trap_penalty=TRAP_ROUTE_PENALTY,
                blocked=active_bosses,
            )
            if len(path) <= 1:
                continue
            distance = len(path) - 1
            trap_penalty = _trap_penalty_on_path(maze, path, source, triggered_traps)
            net_value = COIN_VALUE - trap_penalty
            if net_value <= 0:
                continue
            ratio = net_value / (distance + 1)
            reserve_candidates.append((ratio, distance, pos, path))

    if not reserve_candidates:
        return None

    ratio, _, target_pos, path = sorted(
        reserve_candidates,
        key=lambda item: (-item[0], item[1], manhattan(item[2], maze.end), item[2]),
    )[0]
    shortage = max(0, boss_reserve - coin_balance)
    return Decision(
        next_pos=path[1],
        coins_in_view=coin_candidates,
        traps_in_view=trap_candidates,
        selected_target=f"储备金币{target_pos} 性价比={ratio:.1f}",
        planned_path=path,
        strategy="Greedy",
        reason=f"BOSS复活储备不足{shortage}枚，优先补金币后再推进",
    )


def _active_boss_positions(maze: Maze, source: list[list[int]]) -> set[Pos]:
    return {
        boss_pos
        for boss_pos in maze.bosses
        if maze.tile_at(boss_pos, source) == BOSS
    }


def _boss_revive_cost_on_path(maze: Maze, path: list[Pos], source: list[list[int]]) -> int:
    return sum(
        boss.revive_cost
        for pos in path
        if pos in maze.bosses and maze.tile_at(pos, source) == BOSS
        for boss in maze.bosses[pos]
        if not boss_battle_optimal(boss, maze.skills).success
    )


def _trap_penalty_on_path(
    maze: Maze,
    path: list[Pos],
    source: list[list[int]],
    triggered_traps: set[Pos],
) -> int:
    trap_count = sum(
        1
        for pos in path[1:]
        if pos not in triggered_traps and maze.tile_at(pos, source) == TRAP
    )
    return trap_count * TRAP_ROUTE_PENALTY
