from __future__ import annotations

from pathlib import Path

from ai_player import MazeLoader, available_strategy_names, get_strategy, run_full
from ai_player.batch_test import run_batch_tests
from ai_player.boss_battle import boss_battle_optimal, brute_force_optimal
from ai_player.evaluate import evaluate_maze
from ai_player.local_greedy import run_local_greedy_cases
from ai_player.model import Boss, Skill
from ai_player.pathfinding import astar_path, bfs_path, dijkstra_path
from ai_player.visualize import export_boss_battle_png, export_compare_png, export_heatmap_png, export_path_png


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_parse_external_json() -> None:
    maze = MazeLoader.load(ROOT_DIR / "map" / "maze_15_15.json")
    assert maze.height == 15
    assert maze.width == 15
    assert maze.start == (1, 1)
    assert maze.end == (13, 13)
    assert maze.total_coins == 5
    assert maze.boss_count() == 2
    assert len(maze.skills) == 4


def test_pathfinding_reaches_end() -> None:
    maze = MazeLoader.load(ROOT_DIR / "map" / "maze_15_15.json")
    bfs = bfs_path(maze, maze.start, maze.end)
    astar = astar_path(maze, maze.start, maze.end)
    dijkstra = dijkstra_path(maze, maze.start, maze.end)
    assert bfs[0] == maze.start and bfs[-1] == maze.end
    assert astar[0] == maze.start and astar[-1] == maze.end
    assert dijkstra[0] == maze.start and dijkstra[-1] == maze.end
    assert len(astar) == len(bfs)


def test_boss_branch_and_bound_matches_bruteforce() -> None:
    skills = [Skill("技能-0", 5, 0), Skill("技能-1", 9, 2)]
    boss = Boss("BOSS-test", (1, 1), hp=18, max_rounds=8, revive_cost=5)
    solved = boss_battle_optimal(boss, skills)
    brute = brute_force_optimal(boss, skills)
    assert solved.success
    assert solved.rounds == brute.rounds


def test_full_exploration_runs_to_end() -> None:
    maze = MazeLoader.load(ROOT_DIR / "map" / "maze_15_15.json")
    result = run_full(maze, strategy=get_strategy("Greedy"))
    assert result.reached_end
    assert result.maze_steps > 0
    assert result.boss_defeated == 2
    assert result.boss_rounds == 12
    assert result.coin_balance == 1
    assert len(result.boss_results) == 2
    assert any(snapshot.battle_event for snapshot in result.snapshots)


def test_boss_revive_retries_until_coin_shortage() -> None:
    maze = MazeLoader.from_layout(
        "revive_retry",
        [
            "#######",
            "#SGGBE#",
            "#######",
        ],
        boss_hps=[5],
        skills=[Skill("技能-0", 1, 0)],
        min_rounds=1,
        coin_consumption=1,
    )
    result = run_full(maze, strategy=get_strategy("Greedy"))
    assert not result.reached_end
    assert result.boss_rounds == 3
    assert result.coin_balance == 0
    assert result.boss_results[-1].revive_count == 2


def test_local_3x3_greedy_cases() -> None:
    summary = run_local_greedy_cases(ROOT_DIR / "map" / "local_greedy_cases.json")
    assert len(summary.results) == 3
    assert [item.picked_value for item in summary.results] == [50, 50, 0]
    assert round(summary.average_picked_value, 2) == 33.33


def test_batch_boundary_maps() -> None:
    output_csv = ROOT_DIR / "outputs" / "test_reports" / "batch_results.csv"
    summary = run_batch_tests(ROOT_DIR / "map" / "test_cases", output_csv=output_csv)
    assert len(summary.rows) == 6
    assert output_csv.exists()
    assert any(not row.reached_end for row in summary.rows)
    assert any(row.map_name == "no_coins.json" and row.reached_end for row in summary.rows)


def test_adaptive_strategy_runs_to_end() -> None:
    maze = MazeLoader.load(ROOT_DIR / "map" / "maze_15_15.json")
    result = run_full(maze, strategy=get_strategy("Adaptive"))
    assert result.reached_end


def test_adaptive_keeps_3x3_vision() -> None:
    maze = MazeLoader.from_layout(
        "adaptive_vision",
        [
            "#######",
            "#  G  #",
            "#     #",
            "#  S E#",
            "#     #",
            "#######",
        ],
    )
    decision = get_strategy("Adaptive").decide(maze, maze.start, set(), set())
    assert decision.selected_target == ""


def test_q_learning_registered_as_strategy() -> None:
    assert "Q-Learning" in available_strategy_names()
    maze = MazeLoader.from_layout(
        "q_learning_small",
        [
            "#######",
            "#S   E#",
            "#######",
        ],
    )
    result = run_full(maze, strategy=get_strategy("Q-Learning"))
    assert result.reached_end


def test_auto_degrades_after_no_resource_growth() -> None:
    maze = MazeLoader.from_layout(
        "long_no_resource",
        [
            "######################",
            "#S                  E#",
            "######################",
        ],
    )
    result = run_full(maze, strategy=get_strategy("Greedy"))
    assert result.reached_end
    assert "Layer2" in result.strategy_name


def test_evaluate_maze() -> None:
    maze = MazeLoader.load(ROOT_DIR / "map" / "maze_15_15.json")
    difficulty = evaluate_maze(maze)
    assert difficulty.shortest_path_length > 0
    assert difficulty.boss_count == 2
    assert difficulty.level in {"简单", "中等", "困难"}


def test_report_exports() -> None:
    maze = MazeLoader.load(ROOT_DIR / "map" / "maze_15_15.json")
    result = run_full(maze, strategy=get_strategy("Greedy"))
    output_dir = ROOT_DIR / "outputs" / "test_reports"
    outputs = [
        export_path_png(result, output_dir),
        export_heatmap_png(result, output_dir),
        export_boss_battle_png(result, output_dir),
        export_compare_png([result], output_dir),
    ]
    for output in outputs:
        assert output.exists()
        assert output.stat().st_size > 0
