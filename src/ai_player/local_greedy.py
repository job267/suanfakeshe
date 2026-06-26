from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .greedy_pick import decide
from .maze_parser import MazeLoader
from .model import COIN, Candidate, Maze, Pos
from .pathfinding import manhattan
from .visualize import render_console


@dataclass(frozen=True)
class LocalGreedyCase:
    name: str
    maze: Maze


@dataclass(frozen=True)
class LocalGreedyResult:
    case_name: str
    position: Pos
    next_pos: Pos
    selected_target: str
    picked_value: int
    candidate_labels: list[str]
    path_visualization: str


@dataclass(frozen=True)
class LocalGreedySummary:
    results: list[LocalGreedyResult]

    @property
    def average_picked_value(self) -> float:
        if not self.results:
            return 0.0
        return sum(item.picked_value for item in self.results) / len(self.results)


DEFAULT_LOCAL_CASES = [
    {
        "name": "single_coin",
        "maze": [
            [" ", "E", " "],
            [" ", "S", "G"],
            [" ", " ", " "],
        ],
    },
    {
        "name": "multi_coin_with_trap",
        "maze": [
            ["G", "E", " "],
            ["T", "S", "G"],
            [" ", " ", "G"],
        ],
    },
    {
        "name": "trap_only",
        "maze": [
            [" ", "E", " "],
            ["T", "S", " "],
            [" ", " ", " "],
        ],
    },
]


def load_local_cases(path: str | Path | None = None) -> list[LocalGreedyCase]:
    payload = _load_payload(path)
    cases: list[LocalGreedyCase] = []
    for idx, item in enumerate(payload):
        name = str(item.get("name") or f"case_{idx + 1}")
        raw_maze = item.get("maze")
        if not isinstance(raw_maze, list):
            raise ValueError(f"{name} 缺少 maze 字段")
        layout = ["".join(row) for row in raw_maze]
        cases.append(LocalGreedyCase(name, MazeLoader.from_layout(name, layout)))
    return cases


def run_local_greedy_cases(path: str | Path | None = None) -> LocalGreedySummary:
    results: list[LocalGreedyResult] = []
    for case in load_local_cases(path):
        position = case.maze.start
        decision = decide(case.maze, position, radius=1)
        selected = _selected_candidate(decision.coins_in_view, case.maze)
        picked_value = selected.value if selected is not None else 0
        candidates = [item.label for item in sorted(decision.coins_in_view + decision.traps_in_view, key=lambda item: (-item.ratio, item.position))]
        path = set(decision.planned_path)
        results.append(
            LocalGreedyResult(
                case_name=case.name,
                position=position,
                next_pos=decision.next_pos,
                selected_target=decision.selected_target or "无",
                picked_value=picked_value,
                candidate_labels=candidates,
                path_visualization=render_console(case.maze, player=position, path=path),
            )
        )
    return LocalGreedySummary(results)


def format_local_greedy_summary(summary: LocalGreedySummary) -> str:
    lines: list[str] = []
    for result in summary.results:
        lines.append(f"[{result.case_name}]")
        lines.append(result.path_visualization)
        lines.append(f"当前位置: {result.position}  下一步: {result.next_pos}")
        lines.append(f"候选: {' > '.join(result.candidate_labels) if result.candidate_labels else '无'}")
        lines.append(f"选中: {result.selected_target}  拾取资源价值: {result.picked_value}")
        lines.append("")
    lines.append(f"平均拾取资源价值: {summary.average_picked_value:.2f}")
    return "\n".join(lines)


def _load_payload(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return list(DEFAULT_LOCAL_CASES)
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        payload = payload.get("cases", [])
    if not isinstance(payload, list):
        raise ValueError("局部贪心用例文件必须是数组，或包含 cases 数组")
    return payload


def _selected_candidate(candidates: list[Candidate], maze: Maze) -> Candidate | None:
    reachable = [item for item in candidates if item.tile == COIN and item.reachable and item.ratio > 0]
    if not reachable:
        return None
    # Local test mirrors greedy_pick's deterministic ordering except that the
    # caller only needs the value, not a second path search.
    return sorted(reachable, key=lambda item: (-item.ratio, item.distance, manhattan(item.position, maze.end), item.position))[0]
