from __future__ import annotations

from abc import ABC, abstractmethod

from .greedy_pick import decide as greedy_decide
from .model import Decision, Maze, Pos
from .pathfinding import astar_path, bfs_path, dijkstra_path


class ExplorationStrategy(ABC):
    name: str

    @abstractmethod
    def decide(
        self,
        maze: Maze,
        position: Pos,
        collected_coins: set[Pos],
        triggered_traps: set[Pos],
        matrix: list[list[int]] | None = None,
        coin_balance: int = 0,
    ) -> Decision:
        raise NotImplementedError


class GreedyStrategy(ExplorationStrategy):
    name = "Greedy"

    def __init__(self, radius: int = 1) -> None:
        self.radius = radius

    def decide(
        self,
        maze: Maze,
        position: Pos,
        collected_coins: set[Pos],
        triggered_traps: set[Pos],
        matrix: list[list[int]] | None = None,
        coin_balance: int = 0,
    ) -> Decision:
        return greedy_decide(
            maze,
            position,
            collected_coins=collected_coins,
            triggered_traps=triggered_traps,
            radius=self.radius,
            matrix=matrix,
            coin_balance=coin_balance,
        )


class AstarStrategy(ExplorationStrategy):
    name = "A*"

    def decide(
        self,
        maze: Maze,
        position: Pos,
        collected_coins: set[Pos],
        triggered_traps: set[Pos],
        matrix: list[list[int]] | None = None,
        coin_balance: int = 0,
    ) -> Decision:
        path = astar_path(maze, position, maze.end, matrix=matrix)
        return Decision(
            next_pos=path[1] if len(path) > 1 else position,
            planned_path=path,
            strategy=self.name,
            reason="A*按曼哈顿启发式寻找终点最短方向",
        )


class BfsStrategy(ExplorationStrategy):
    name = "BFS"

    def decide(
        self,
        maze: Maze,
        position: Pos,
        collected_coins: set[Pos],
        triggered_traps: set[Pos],
        matrix: list[list[int]] | None = None,
        coin_balance: int = 0,
    ) -> Decision:
        path = bfs_path(maze, position, maze.end, matrix=matrix)
        return Decision(
            next_pos=path[1] if len(path) > 1 else position,
            planned_path=path,
            strategy=self.name,
            reason="BFS寻找到终点的无权最短路径",
        )


class DijkstraStrategy(ExplorationStrategy):
    name = "Dijkstra"

    def decide(
        self,
        maze: Maze,
        position: Pos,
        collected_coins: set[Pos],
        triggered_traps: set[Pos],
        matrix: list[list[int]] | None = None,
        coin_balance: int = 0,
    ) -> Decision:
        path = dijkstra_path(maze, position, maze.end, matrix=matrix)
        return Decision(
            next_pos=path[1] if len(path) > 1 else position,
            planned_path=path,
            strategy=self.name,
            reason="Dijkstra按步数+陷阱惩罚规划低风险路径",
        )


class AdaptiveStrategy(ExplorationStrategy):
    name = "Adaptive"

    def decide(
        self,
        maze: Maze,
        position: Pos,
        collected_coins: set[Pos],
        triggered_traps: set[Pos],
        matrix: list[list[int]] | None = None,
        coin_balance: int = 0,
    ) -> Decision:
        greedy = greedy_decide(
            maze,
            position,
            collected_coins=collected_coins,
            triggered_traps=triggered_traps,
            radius=1,
            matrix=matrix,
            coin_balance=coin_balance,
        )
        if greedy.selected_target:
            return Decision(
                **{
                    **greedy.__dict__,
                    "strategy": self.name,
                    "reason": "Adaptive保持3x3视野，优先选择高性价比资源",
                }
            )

        path = dijkstra_path(maze, position, maze.end, matrix=matrix, trap_penalty=40)
        return Decision(
            next_pos=path[1] if len(path) > 1 else position,
            coins_in_view=greedy.coins_in_view,
            traps_in_view=greedy.traps_in_view,
            planned_path=path,
            strategy=self.name,
            reason="Adaptive视野内无正收益资源，改用高陷阱惩罚路径冲终点",
        )


class QLearningStrategy(ExplorationStrategy):
    name = "Q-Learning"

    def __init__(self) -> None:
        self._policy: ExplorationStrategy | None = None
        self._trained_key: tuple[str, int, int] | None = None

    def decide(
        self,
        maze: Maze,
        position: Pos,
        collected_coins: set[Pos],
        triggered_traps: set[Pos],
        matrix: list[list[int]] | None = None,
        coin_balance: int = 0,
    ) -> Decision:
        key = (maze.name, maze.height, maze.width)
        if self._policy is None or self._trained_key != key:
            from .rl_agent import QLearningConfig, QLearningPolicyStrategy, train_q_table

            q_table = train_q_table(maze, QLearningConfig(episodes=800))
            self._policy = QLearningPolicyStrategy(q_table)
            self._trained_key = key
        return self._policy.decide(
            maze,
            position,
            collected_coins,
            triggered_traps,
            matrix=matrix,
            coin_balance=coin_balance,
        )


STRATEGY_FACTORIES = {
    GreedyStrategy.name: GreedyStrategy,
    AstarStrategy.name: AstarStrategy,
    BfsStrategy.name: BfsStrategy,
    DijkstraStrategy.name: DijkstraStrategy,
    AdaptiveStrategy.name: AdaptiveStrategy,
    QLearningStrategy.name: QLearningStrategy,
}


def get_strategy(name: str | None) -> ExplorationStrategy:
    factory = STRATEGY_FACTORIES.get(name or "", GreedyStrategy)
    return factory()


def available_strategy_names() -> list[str]:
    return list(STRATEGY_FACTORIES)
