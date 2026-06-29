from __future__ import annotations

import random
from dataclasses import dataclass

from .exploration import run_full
from .model import BOSS, COIN, END, TRAP, WALL, AlgorithmResult, Decision, Maze, Pos
from .pathfinding import astar_path
from .strategies import ExplorationStrategy

Action = tuple[int, int]
QTable = dict[Pos, dict[Action, float]]

ACTIONS: tuple[Action, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


@dataclass(frozen=True)
class QLearningConfig:
    episodes: int = 800
    alpha: float = 0.25
    gamma: float = 0.90
    epsilon: float = 0.25
    max_steps_per_episode: int = 500
    seed: int = 7


class QLearningPolicyStrategy(ExplorationStrategy):
    name = "Q-Learning"

    def __init__(self, q_table: QTable) -> None:
        self.q_table = q_table
        self.visit_count: dict[Pos, int] = {}

    def decide(
        self,
        maze: Maze,
        position: Pos,
        collected_coins: set[Pos],
        triggered_traps: set[Pos],
        matrix: list[list[int]] | None = None,
        coin_balance: int = 0,
    ) -> Decision:
        self.visit_count[position] = self.visit_count.get(position, 0) + 1
        if self.visit_count[position] > 2:
            return self._fallback(maze, position, matrix, "当前位置访问超过2次，回退到A*避免Q表循环")

        action_values = self.q_table.get(position, {})
        if action_values and max(action_values.values()) > 0:
            ranked = sorted(action_values.items(), key=lambda item: item[1], reverse=True)
            for action, value in ranked:
                next_pos = (position[0] + action[0], position[1] + action[1])
                if maze.is_walkable(next_pos, matrix) and self.visit_count.get(next_pos, 0) <= 2:
                    return Decision(
                        next_pos=next_pos,
                        strategy=self.name,
                        reason=f"Q表选择动作{action}，估值{value:.2f}",
                    )

        return self._fallback(maze, position, matrix, "Q表在当前位置没有可用正估值动作，回退到A*保证可达")

    def _fallback(self, maze: Maze, position: Pos, matrix: list[list[int]] | None, reason: str) -> Decision:
        path = astar_path(maze, position, maze.end, matrix=matrix)
        return Decision(
            next_pos=path[1] if len(path) > 1 else position,
            planned_path=path,
            strategy=self.name,
            reason=reason,
        )


def train_q_table(maze: Maze, config: QLearningConfig | None = None) -> QTable:
    cfg = config or QLearningConfig()
    rng = random.Random(cfg.seed)
    q_table: QTable = {
        (r, c): {action: 0.0 for action in ACTIONS}
        for r, row in enumerate(maze.matrix)
        for c, tile in enumerate(row)
        if tile != WALL
    }

    for episode in range(cfg.episodes):
        pos = maze.start
        epsilon = max(0.02, cfg.epsilon * (1 - episode / max(1, cfg.episodes)))
        for _ in range(cfg.max_steps_per_episode):
            action = _choose_action(q_table, pos, rng, epsilon)
            next_pos, reward, done = _step_reward(maze, pos, action)
            current = q_table[pos][action]
            best_next = max(q_table.get(next_pos, {action: 0.0 for action in ACTIONS}).values())
            q_table[pos][action] = current + cfg.alpha * (reward + cfg.gamma * best_next - current)
            pos = next_pos
            if done:
                break
    return q_table


def run_q_learning(maze: Maze, config: QLearningConfig | None = None) -> AlgorithmResult:
    q_table = train_q_table(maze, config)
    return run_full(maze, strategy=QLearningPolicyStrategy(q_table))


def _choose_action(q_table: QTable, pos: Pos, rng: random.Random, epsilon: float) -> Action:
    if rng.random() < epsilon:
        return rng.choice(ACTIONS)
    values = q_table.get(pos)
    if not values:
        return rng.choice(ACTIONS)
    return max(values, key=values.get)


def _step_reward(maze: Maze, pos: Pos, action: Action) -> tuple[Pos, float, bool]:
    next_pos = (pos[0] + action[0], pos[1] + action[1])
    if not maze.in_bounds(next_pos) or maze.tile_at(next_pos) == WALL:
        return pos, -5.0, False

    tile = maze.tile_at(next_pos)
    if tile == END:
        return next_pos, 200.0, True
    if tile == COIN:
        return next_pos, 50.0, False
    if tile == TRAP:
        return next_pos, -30.0, False
    if tile == BOSS:
        return next_pos, -5.0, False
    return next_pos, -1.0, False
