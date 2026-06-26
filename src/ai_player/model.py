from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

Pos = tuple[int, int]

WALL = 0
ROAD = 1
START = 2
END = 3
COIN = 4
TRAP = 5
BOSS = 6

SYMBOL_TO_TILE = {
    "#": WALL,
    " ": ROAD,
    "S": START,
    "E": END,
    "G": COIN,
    "T": TRAP,
    "B": BOSS,
}

TILE_TO_SYMBOL = {value: key for key, value in SYMBOL_TO_TILE.items()}
TILE_NAMES = {
    WALL: "墙壁",
    ROAD: "通路",
    START: "起点",
    END: "终点",
    COIN: "金币",
    TRAP: "陷阱",
    BOSS: "BOSS",
}

COIN_VALUE = 50
TRAP_VALUE = -30


@dataclass(frozen=True)
class Skill:
    name: str
    damage: int
    cooldown: int


DEFAULT_SKILLS = [
    Skill("普通攻击", damage=5, cooldown=0),
    Skill("重击", damage=12, cooldown=2),
]


@dataclass(frozen=True)
class Boss:
    boss_id: str
    position: Pos
    hp: int
    max_rounds: int
    revive_cost: int


@dataclass(frozen=True)
class Candidate:
    position: Pos
    tile: int
    value: int
    distance: int
    ratio: float
    reachable: bool = True
    excluded: bool = False

    @property
    def label(self) -> str:
        name = TILE_NAMES.get(self.tile, str(self.tile))
        if self.excluded:
            return f"{name}{self.position}:排除"
        if not self.reachable:
            return f"{name}{self.position}:不可达"
        return f"{name}{self.position}:{self.ratio:.1f}"


@dataclass(frozen=True)
class Decision:
    next_pos: Pos
    coins_in_view: list[Candidate] = field(default_factory=list)
    traps_in_view: list[Candidate] = field(default_factory=list)
    selected_target: str = ""
    planned_path: list[Pos] = field(default_factory=list)
    strategy: str = "Greedy"
    reason: str = ""


@dataclass(frozen=True)
class BossResult:
    success: bool
    rounds: int
    skill_sequence: list[str]
    revive_count: int = 0
    hp_history: list[int] = field(default_factory=list)
    message: str = ""


@dataclass(frozen=True)
class BattleEvent:
    boss_id: str
    round_no: int
    skill_name: str
    damage: int
    hp_before: int
    hp_after: int
    max_hp: int
    cooldown: int
    revive_count: int = 0
    message: str = ""


@dataclass(frozen=True)
class StepSnapshot:
    step: int
    position: Pos
    score: int
    coin_balance: int
    maze_steps: int
    boss_rounds: int
    coins_collected: int
    traps_triggered: int
    boss_defeated: int
    path: list[Pos]
    matrix: list[list[int]]
    decision: Optional[Decision] = None
    battle_event: Optional[BattleEvent] = None
    message: str = ""
    reached_end: bool = False
    failed: bool = False


@dataclass(frozen=True)
class AlgorithmResult:
    maze_name: str
    strategy_name: str
    reached_end: bool
    total_score: int
    coin_balance: int
    maze_steps: int
    boss_rounds: int
    coins_collected: int
    traps_triggered: int
    boss_defeated: int
    path: list[Pos]
    snapshots: list[StepSnapshot]
    message: str
    boss_results: list[BossResult] = field(default_factory=list)

    @property
    def efficiency(self) -> float:
        return self.resource_step_ratio

    @property
    def remaining_resource_value(self) -> int:
        return self.total_score

    @property
    def total_steps(self) -> int:
        return self.maze_steps + self.boss_rounds

    @property
    def resource_step_ratio(self) -> float:
        return self.remaining_resource_value / max(1, self.total_steps)


@dataclass(frozen=True)
class CompareResult:
    maze_name: str
    results: list[AlgorithmResult]

    @property
    def best_score(self) -> Optional[AlgorithmResult]:
        return max(self.results, key=lambda item: item.total_score, default=None)

    @property
    def best_steps(self) -> Optional[AlgorithmResult]:
        reached = [item for item in self.results if item.reached_end]
        return min(reached, key=lambda item: item.maze_steps + item.boss_rounds, default=None)

    @property
    def best_efficiency(self) -> Optional[AlgorithmResult]:
        return max(self.results, key=lambda item: item.efficiency, default=None)


@dataclass
class Maze:
    name: str
    matrix: list[list[int]]
    bosses: dict[Pos, list[Boss]] = field(default_factory=dict)
    skills: list[Skill] = field(default_factory=lambda: list(DEFAULT_SKILLS))
    min_rounds: int = 20
    coin_consumption: int = 5

    @property
    def height(self) -> int:
        return len(self.matrix)

    @property
    def width(self) -> int:
        return len(self.matrix[0]) if self.matrix else 0

    @property
    def start(self) -> Pos:
        return self._find_unique(START)

    @property
    def end(self) -> Pos:
        return self._find_unique(END)

    @property
    def total_coins(self) -> int:
        return sum(1 for row in self.matrix for tile in row if tile == COIN)

    def _find_unique(self, tile_type: int) -> Pos:
        matches = [
            (row_idx, col_idx)
            for row_idx, row in enumerate(self.matrix)
            for col_idx, tile in enumerate(row)
            if tile == tile_type
        ]
        if len(matches) != 1:
            raise ValueError(f"{TILE_NAMES[tile_type]}数量应为1，实际为{len(matches)}")
        return matches[0]

    def clone(self, name: str | None = None) -> "Maze":
        return Maze(
            name=name or self.name,
            matrix=self.copy_matrix(),
            bosses={pos: list(group) for pos, group in self.bosses.items()},
            skills=list(self.skills),
            min_rounds=self.min_rounds,
            coin_consumption=self.coin_consumption,
        )

    def copy_matrix(self, matrix: list[list[int]] | None = None) -> list[list[int]]:
        source = self.matrix if matrix is None else matrix
        return [list(row) for row in source]

    def in_bounds(self, pos: Pos) -> bool:
        row, col = pos
        return 0 <= row < self.height and 0 <= col < self.width

    def tile_at(self, pos: Pos, matrix: list[list[int]] | None = None) -> int:
        source = self.matrix if matrix is None else matrix
        row, col = pos
        return source[row][col]

    def set_tile(self, pos: Pos, tile: int, matrix: list[list[int]] | None = None) -> None:
        source = self.matrix if matrix is None else matrix
        row, col = pos
        source[row][col] = tile

    def is_walkable(self, pos: Pos, matrix: list[list[int]] | None = None) -> bool:
        return self.in_bounds(pos) and self.tile_at(pos, matrix) != WALL

    def neighbors(
        self,
        pos: Pos,
        matrix: list[list[int]] | None = None,
        blocked: Iterable[Pos] | None = None,
    ) -> list[Pos]:
        blocked_set = set(blocked or ())
        row, col = pos
        result: list[Pos] = []
        for next_pos in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if next_pos in blocked_set:
                continue
            if self.is_walkable(next_pos, matrix):
                result.append(next_pos)
        return result

    def view_positions(self, center: Pos, radius: int = 1) -> list[Pos]:
        row, col = center
        positions: list[Pos] = []
        for r in range(row - radius, row + radius + 1):
            for c in range(col - radius, col + radius + 1):
                pos = (r, c)
                if self.in_bounds(pos):
                    positions.append(pos)
        return positions

    def boss_count(self) -> int:
        return sum(len(group) for group in self.bosses.values())
