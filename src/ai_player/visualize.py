from __future__ import annotations

import os
from pathlib import Path

from .model import BOSS, COIN, END, START, TRAP, WALL, AlgorithmResult, Decision, Maze, Pos


def render_console(
    maze: Maze,
    matrix: list[list[int]] | None = None,
    player: Pos | None = None,
    path: set[Pos] | None = None,
) -> str:
    source = matrix or maze.matrix
    path = path or set()
    symbols = {
        WALL: "#",
        START: "S",
        END: "E",
        COIN: "G",
        TRAP: "T",
        BOSS: "B",
    }
    rows: list[str] = []
    for r, row in enumerate(source):
        chars: list[str] = []
        for c, tile in enumerate(row):
            pos = (r, c)
            if player == pos:
                chars.append("P")
            elif pos in path and tile not in (WALL, START, END):
                chars.append(".")
            else:
                chars.append(symbols.get(tile, " "))
        rows.append("".join(chars))
    return "\n".join(rows)


def decision_summary(decision: Decision | None) -> str:
    if decision is None:
        return ""
    coins = " > ".join(item.label for item in sorted(decision.coins_in_view, key=lambda item: -item.ratio))
    traps = " > ".join(item.label for item in decision.traps_in_view)
    selected = decision.selected_target or "无"
    parts = []
    if coins:
        parts.append(f"金币候选: {coins}")
    if traps:
        parts.append(f"陷阱: {traps}")
    parts.append(f"选中: {selected}")
    parts.append(f"原因: {decision.reason}")
    return " | ".join(parts)


def print_result(result: AlgorithmResult) -> None:
    final_snapshot = result.snapshots[-1]
    print(render_console(Maze(result.maze_name, final_snapshot.matrix), final_snapshot.matrix, final_snapshot.position, set(result.path)))
    print()
    print(f"算法: {result.strategy_name}")
    print(f"结果: {'到达终点' if result.reached_end else '未到达终点'}")
    print(f"剩余资源价值: {result.remaining_resource_value}")
    print(f"迷宫步数: {result.maze_steps}")
    print(f"BOSS回合: {result.boss_rounds}")
    print(f"总步数: {result.total_steps}")
    print(f"金币/金币余额/陷阱/BOSS: {result.coins_collected}/{result.coin_balance}/{result.traps_triggered}/{result.boss_defeated}")
    print(f"资源/步数比: {result.resource_step_ratio:.2f}")
    if result.boss_results:
        print("BOSS战:")
        for boss_result in result.boss_results:
            sequence = " -> ".join(boss_result.skill_sequence)
            print(f"  {boss_result.message}；回合={boss_result.rounds}；技能序列={sequence}")
    print(f"消息: {result.message}")


def export_path_png(result: AlgorithmResult, output_dir: str | Path = "outputs/reports") -> Path:
    plt = _prepare_matplotlib(output_dir)
    import numpy as np
    from matplotlib.colors import ListedColormap

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    final_snapshot = result.snapshots[-1]
    matrix = np.array(final_snapshot.matrix)
    cmap = ListedColormap(["#263238", "#fbfaf5", "#dff4df", "#f6d2ce", "#ffd95a", "#e98b39", "#8e63ce"])
    fig, ax = plt.subplots(figsize=(7, 7), dpi=160)
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=6)
    if result.path:
        rows = [pos[0] for pos in result.path]
        cols = [pos[1] for pos in result.path]
        ax.plot(cols, rows, color="#1f77b4", linewidth=2.2, marker="o", markersize=2.5)
    ax.set_title(f"{_safe_name(result.maze_name)} - {_safe_name(result.strategy_name)} path")
    ax.set_xticks(range(matrix.shape[1]))
    ax.set_yticks(range(matrix.shape[0]))
    ax.grid(color="#cfd8dc", linewidth=0.5)
    ax.tick_params(labelbottom=False, labelleft=False, length=0)
    path = output / f"{_safe_name(result.maze_name)}_{_safe_name(result.strategy_name)}_path.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def export_heatmap_png(result: AlgorithmResult, output_dir: str | Path = "outputs/reports") -> Path:
    plt = _prepare_matplotlib(output_dir)
    import numpy as np

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    final_snapshot = result.snapshots[-1]
    heat = np.zeros((len(final_snapshot.matrix), len(final_snapshot.matrix[0])), dtype=float)
    for row, col in result.path:
        heat[row, col] += 1
    for r, row in enumerate(final_snapshot.matrix):
        for c, tile in enumerate(row):
            if tile == WALL:
                heat[r, c] = -1
    masked = np.ma.masked_where(heat < 0, heat)
    fig, ax = plt.subplots(figsize=(7, 7), dpi=160)
    ax.imshow(masked, cmap="YlOrRd")
    ax.imshow(heat < 0, cmap=ListedWall(), alpha=0.8)
    ax.set_title(f"{_safe_name(result.maze_name)} - visit heatmap")
    ax.tick_params(labelbottom=False, labelleft=False, length=0)
    path = output / f"{_safe_name(result.maze_name)}_{_safe_name(result.strategy_name)}_heatmap.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def export_compare_png(results: list[AlgorithmResult], output_dir: str | Path = "outputs/reports") -> Path:
    plt = _prepare_matplotlib(output_dir)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    names = [item.strategy_name for item in results]
    metrics = [
        ("resource", [item.remaining_resource_value for item in results]),
        ("total steps", [item.total_steps for item in results]),
        ("resource/step", [item.resource_step_ratio for item in results]),
        ("coins", [item.coins_collected for item in results]),
        ("traps", [item.traps_triggered for item in results]),
        ("boss rounds", [item.boss_rounds for item in results]),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), dpi=160)
    palette = ["#2b6cb0", "#2f855a", "#b7791f", "#805ad5", "#c53030", "#319795", "#718096"]
    for ax, (title, values) in zip(axes.flat, metrics, strict=True):
        ax.bar(names, values, color=palette[: len(names)])
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=25)
    fig.suptitle(f"{_safe_name(results[0].maze_name)} algorithm comparison" if results else "algorithm comparison")
    fig.tight_layout()
    path = output / f"{_safe_name(results[0].maze_name) if results else 'maze'}_compare.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def export_boss_battle_png(result: AlgorithmResult, output_dir: str | Path = "outputs/reports") -> Path:
    plt = _prepare_matplotlib(output_dir)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=160)
    if not result.boss_results:
        ax.text(0.5, 0.5, "No boss battle", ha="center", va="center", fontsize=14)
        ax.set_axis_off()
    else:
        cursor = 0
        xticks: list[int] = []
        labels: list[str] = []
        for idx, boss_result in enumerate(result.boss_results, start=1):
            xs = list(range(cursor + 1, cursor + len(boss_result.hp_history) + 1))
            ax.plot(xs, boss_result.hp_history, marker="o", linewidth=2, label=f"BOSS-{idx}")
            for x, skill in zip(xs, boss_result.skill_sequence, strict=False):
                xticks.append(x)
                labels.append(skill.replace("技能-", "S"))
            cursor += len(boss_result.hp_history)
        ax.set_title(f"{_safe_name(result.maze_name)} boss battle")
        ax.set_xlabel("round")
        ax.set_ylabel("hp remaining")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right")
        if xticks:
            ax.set_xticks(xticks)
            ax.set_xticklabels(labels, rotation=45, ha="right")
    path = output / f"{_safe_name(result.maze_name)}_{_safe_name(result.strategy_name)}_boss.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _safe_name(name: str) -> str:
    safe = "".join(ch if ch.isascii() and (ch.isalnum() or ch in ("-", "_")) else "_" for ch in name)
    return safe.strip("_") or "maze"


def _prepare_matplotlib(output_dir: str | Path):
    cache_dir = Path(output_dir).parent / "mpl_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def ListedWall():
    from matplotlib.colors import ListedColormap

    return ListedColormap(["#00000000", "#263238"])
