from __future__ import annotations

from .exploration import run_full
from .model import CompareResult, Maze
from .strategies import STRATEGY_FACTORIES, ExplorationStrategy


def run_compare(
    maze: Maze,
    strategies: list[ExplorationStrategy] | None = None,
) -> CompareResult:
    strategy_list = strategies or [factory() for factory in STRATEGY_FACTORIES.values()]
    results = [run_full(maze.clone(), strategy=strategy) for strategy in strategy_list]
    return CompareResult(maze.name, results)


def format_compare_table(compare: CompareResult) -> str:
    rows = [
        "算法 | 是否到达 | 剩余资源价值 | 金币余额 | 迷宫步数 | BOSS回合 | 总步数 | 金币 | 陷阱 | BOSS | 资源/步数比",
        "--- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---:",
    ]
    for result in compare.results:
        rows.append(
            " | ".join(
                [
                    result.strategy_name,
                    "是" if result.reached_end else "否",
                    str(result.remaining_resource_value),
                    str(result.coin_balance),
                    str(result.maze_steps),
                    str(result.boss_rounds),
                    str(result.total_steps),
                    str(result.coins_collected),
                    str(result.traps_triggered),
                    str(result.boss_defeated),
                    f"{result.resource_step_ratio:.2f}",
                ]
            )
        )
    return "\n".join(rows)


def analysis_text(compare: CompareResult) -> str:
    best_score = compare.best_score
    best_steps = compare.best_steps
    best_efficiency = compare.best_efficiency
    parts: list[str] = [
        "评分口径：优先比较资源/步数比，即剩余资源价值除以总步数；不是单纯步数最少，也不是金币最少。"
    ]
    if best_score:
        parts.append(f"资源收益最高：{best_score.strategy_name}，得分 {best_score.total_score}。")
    if best_steps:
        parts.append(
            f"通关步数最少：{best_steps.strategy_name}，总行动 {best_steps.maze_steps + best_steps.boss_rounds}。"
        )
    if best_efficiency:
        parts.append(f"资源/步数比最高：{best_efficiency.strategy_name}，比值 {best_efficiency.resource_step_ratio:.2f}。")
    failed = [item.strategy_name for item in compare.results if not item.reached_end]
    if failed:
        parts.append(f"未通关策略：{', '.join(failed)}。")
    return "\n".join(parts) if parts else "暂无可分析结果。"
