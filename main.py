from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_player import MazeLoader, available_strategy_names, format_compare_table, get_strategy, run_compare, run_full
from ai_player.batch_test import all_strategy_names, format_batch_summary, run_batch_tests
from ai_player.evaluate import evaluate_maze
from ai_player.local_greedy import format_local_greedy_summary, run_local_greedy_cases
from ai_player.rl_agent import QLearningConfig, run_q_learning
from ai_player.visualize import (
    decision_summary,
    export_compare_png,
    export_boss_battle_png,
    export_heatmap_png,
    export_path_png,
    print_result,
    render_console,
)

DEFAULT_MAP = ROOT_DIR / "map" / "maze_15_15.json"
DEFAULT_LOCAL_CASES = ROOT_DIR / "map" / "local_greedy_cases.json"
DEFAULT_BATCH_DIR = ROOT_DIR / "map" / "test_cases"


def run_console(map_path: Path, strategy_name: str) -> int:
    maze = MazeLoader.load(map_path)
    result = run_full(maze, strategy=get_strategy(strategy_name))
    print_result(result)
    last_decision = next((snapshot.decision for snapshot in reversed(result.snapshots) if snapshot.decision), None)
    if last_decision:
        print()
        print("最后一步决策:")
        print(decision_summary(last_decision))
    return 0 if result.reached_end else 2


def run_compare_mode(map_path: Path) -> int:
    maze = MazeLoader.load(map_path)
    compare = run_compare(maze)
    print(format_compare_table(compare))
    return 0 if any(result.reached_end for result in compare.results) else 2


def run_local_greedy_mode(cases_path: Path) -> int:
    summary = run_local_greedy_cases(cases_path)
    print(format_local_greedy_summary(summary))
    return 0


def run_batch_mode(batch_dir: Path, batch_all: bool) -> int:
    strategies = all_strategy_names() if batch_all else ["Greedy"]
    summary = run_batch_tests(batch_dir, strategy_names=strategies)
    print(format_batch_summary(summary))
    return 0


def run_evaluate_mode(map_path: Path) -> int:
    maze = MazeLoader.load(map_path)
    difficulty = evaluate_maze(maze)
    print("\n".join(difficulty.as_lines()))
    return 0


def run_export_report_mode(map_path: Path, strategy_name: str) -> int:
    maze = MazeLoader.load(map_path)
    result = run_full(maze, strategy=get_strategy(strategy_name))
    compare = run_compare(maze)
    outputs = [
        export_path_png(result),
        export_heatmap_png(result),
        export_boss_battle_png(result),
        export_compare_png(compare.results),
    ]
    for path in outputs:
        print(path)
    return 0 if result.reached_end else 2


def run_qlearning_mode(map_path: Path) -> int:
    maze = MazeLoader.load(map_path)
    result = run_q_learning(maze, QLearningConfig(episodes=1000))
    print_result(result)
    return 0 if result.reached_end else 2


def run_preview(map_path: Path) -> int:
    maze = MazeLoader.load(map_path)
    print(render_console(maze))
    print(f"地图: {maze.name}  尺寸: {maze.height}x{maze.width}  金币: {maze.total_coins}  BOSS: {maze.boss_count()}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI迷宫玩家")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="迷宫JSON路径")
    parser.add_argument("--local-cases", type=Path, default=DEFAULT_LOCAL_CASES, help="3x3局部贪心用例JSON路径")
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR, help="批量地图测试目录")
    parser.add_argument("--strategy", default="Greedy", choices=available_strategy_names(), help="运行策略")
    parser.add_argument("--gui", action="store_true", help="启动PyQt图形界面")
    parser.add_argument("--console", action="store_true", help="控制台运行完整探险")
    parser.add_argument("--compare", action="store_true", help="控制台运行算法对比")
    parser.add_argument("--local-greedy", action="store_true", help="运行3x3局部贪心测试并统计平均拾取价值")
    parser.add_argument("--batch", action="store_true", help="批量运行map/test_cases并导出CSV")
    parser.add_argument("--batch-all", action="store_true", help="批量测试时运行全部策略")
    parser.add_argument("--evaluate", action="store_true", help="评估迷宫难度")
    parser.add_argument("--export-report", action="store_true", help="导出路径图、热力图和算法对比图")
    parser.add_argument("--qlearn", action="store_true", help="训练并运行表格型Q-Learning对比")
    parser.add_argument("--preview", action="store_true", help="只打印地图预览")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    map_path = args.map
    if args.console:
        return run_console(map_path, args.strategy)
    if args.compare:
        return run_compare_mode(map_path)
    if args.local_greedy:
        return run_local_greedy_mode(args.local_cases)
    if args.batch:
        return run_batch_mode(args.batch_dir, args.batch_all)
    if args.evaluate:
        return run_evaluate_mode(map_path)
    if args.export_report:
        return run_export_report_mode(map_path, args.strategy)
    if args.qlearn:
        return run_qlearning_mode(map_path)
    if args.preview:
        return run_preview(map_path)

    from gui.qt_app import run_gui

    return run_gui(map_path)


if __name__ == "__main__":
    raise SystemExit(main())
