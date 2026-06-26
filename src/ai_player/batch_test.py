from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .exploration import run_full
from .maze_parser import MazeLoader
from .model import AlgorithmResult
from .strategies import available_strategy_names, get_strategy


@dataclass(frozen=True)
class BatchRow:
    map_name: str
    strategy_name: str
    reached_end: bool
    remaining_resource_value: int
    maze_steps: int
    boss_rounds: int
    total_steps: int
    resource_step_ratio: float
    coins_collected: int
    traps_triggered: int
    boss_defeated: int
    message: str


@dataclass(frozen=True)
class BatchSummary:
    rows: list[BatchRow]
    output_csv: Path | None = None

    @property
    def pass_count(self) -> int:
        return sum(1 for row in self.rows if row.reached_end)

    @property
    def average_ratio(self) -> float:
        if not self.rows:
            return 0.0
        return sum(row.resource_step_ratio for row in self.rows) / len(self.rows)


def run_batch_tests(
    map_dir: str | Path,
    strategy_names: list[str] | None = None,
    output_csv: str | Path | None = "outputs/reports/batch_results.csv",
) -> BatchSummary:
    directory = Path(map_dir)
    maps = sorted(directory.glob("*.json"))
    strategies = strategy_names or ["Greedy"]
    rows: list[BatchRow] = []

    for map_path in maps:
        maze = MazeLoader.load(map_path)
        for strategy_name in strategies:
            result = run_full(maze, strategy=get_strategy(strategy_name))
            rows.append(_row_from_result(map_path.name, result))

    csv_path = Path(output_csv) if output_csv else None
    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(csv_path, rows)
    return BatchSummary(rows, csv_path)


def format_batch_summary(summary: BatchSummary) -> str:
    lines = [
        "地图 | 策略 | 到达 | 剩余资源价值 | 总步数 | 资源/步数比 | 金币 | 陷阱 | BOSS",
        "--- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---:",
    ]
    for row in summary.rows:
        lines.append(
            " | ".join(
                [
                    row.map_name,
                    row.strategy_name,
                    "是" if row.reached_end else "否",
                    str(row.remaining_resource_value),
                    str(row.total_steps),
                    f"{row.resource_step_ratio:.2f}",
                    str(row.coins_collected),
                    str(row.traps_triggered),
                    str(row.boss_defeated),
                ]
            )
        )
    lines.append("")
    lines.append(f"通关数: {summary.pass_count}/{len(summary.rows)}")
    lines.append(f"平均资源/步数比: {summary.average_ratio:.2f}")
    if summary.output_csv:
        lines.append(f"CSV: {summary.output_csv}")
    return "\n".join(lines)


def all_strategy_names() -> list[str]:
    return available_strategy_names()


def _row_from_result(map_name: str, result: AlgorithmResult) -> BatchRow:
    return BatchRow(
        map_name=map_name,
        strategy_name=result.strategy_name,
        reached_end=result.reached_end,
        remaining_resource_value=result.remaining_resource_value,
        maze_steps=result.maze_steps,
        boss_rounds=result.boss_rounds,
        total_steps=result.total_steps,
        resource_step_ratio=result.resource_step_ratio,
        coins_collected=result.coins_collected,
        traps_triggered=result.traps_triggered,
        boss_defeated=result.boss_defeated,
        message=result.message,
    )


def _write_csv(path: Path, rows: list[BatchRow]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "map_name",
                "strategy_name",
                "reached_end",
                "remaining_resource_value",
                "maze_steps",
                "boss_rounds",
                "total_steps",
                "resource_step_ratio",
                "coins_collected",
                "traps_triggered",
                "boss_defeated",
                "message",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.map_name,
                    row.strategy_name,
                    row.reached_end,
                    row.remaining_resource_value,
                    row.maze_steps,
                    row.boss_rounds,
                    row.total_steps,
                    f"{row.resource_step_ratio:.6f}",
                    row.coins_collected,
                    row.traps_triggered,
                    row.boss_defeated,
                    row.message,
                ]
            )
