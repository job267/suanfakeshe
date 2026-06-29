from __future__ import annotations

from .boss_battle import boss_battle_optimal
from .model import (
    BOSS,
    COIN,
    COIN_VALUE,
    ROAD,
    START,
    TRAP,
    TRAP_COIN_COST,
    TRAP_VALUE,
    AlgorithmResult,
    BattleEvent,
    Boss,
    BossResult,
    Decision,
    Maze,
    Pos,
    Skill,
    StepSnapshot,
)
from .strategies import AstarStrategy, BfsStrategy, ExplorationStrategy, GreedyStrategy


class ExplorationRunner:
    def __init__(
        self,
        maze: Maze,
        strategy: ExplorationStrategy | None = None,
        max_steps: int | None = None,
    ) -> None:
        self.maze = maze.clone()
        self.strategy = strategy or GreedyStrategy()
        self.active_strategy: ExplorationStrategy = self.strategy
        self.degrade_level = 1
        self.no_resource_steps = 0
        self.degrade_threshold = max(8, self.maze.width // 2)
        self.max_steps = max_steps or max(50, self.maze.height * self.maze.width * 8)
        self.matrix = self.maze.copy_matrix()
        self.position = self.maze.start
        self.score = 0
        self.coin_balance = 0
        self.maze_steps = 0
        self.boss_rounds = 0
        self.boss_defeated = 0
        self.collected_coins: set[Pos] = set()
        self.triggered_traps: set[Pos] = set()
        self.cleared_bosses: set[Pos] = set()
        self.path: list[Pos] = [self.position]
        self.snapshots: list[StepSnapshot] = []
        self.boss_results: list[BossResult] = []
        self.failed = False
        self.message = "准备开始"
        self._snapshot(None, self.message)

    def run(self) -> AlgorithmResult:
        while self.position != self.maze.end and not self.failed and self.maze_steps < self.max_steps:
            decision = self._decide_with_degradation()
            self._apply_decision(decision)

        reached = self.position == self.maze.end and not self.failed
        if reached:
            self.message = "已到达终点"
        elif self.maze_steps >= self.max_steps:
            self.failed = True
            self.message = f"超过最大步数{self.max_steps}，终止探险"

        self._snapshot(None, self.message, reached_end=reached, failed=self.failed)
        return AlgorithmResult(
            maze_name=self.maze.name,
            strategy_name=self._result_strategy_name(),
            reached_end=reached,
            total_score=self.score,
            coin_balance=self.coin_balance,
            maze_steps=self.maze_steps,
            boss_rounds=self.boss_rounds,
            coins_collected=len(self.collected_coins),
            traps_triggered=len(self.triggered_traps),
            boss_defeated=self.boss_defeated,
            path=list(self.path),
            snapshots=list(self.snapshots),
            message=self.message,
            boss_results=list(self.boss_results),
        )

    def _decide_with_degradation(self) -> Decision:
        if (
            self.degrade_level == 1
            and self.no_resource_steps >= self.degrade_threshold
            and not isinstance(self.strategy, GreedyStrategy)
        ):
            self._activate_degradation(2, AstarStrategy(), f"连续{self.no_resource_steps}步资源无增长，降级为A*直通终点")

        decision = self.active_strategy.decide(
            self.maze,
            self.position,
            self.collected_coins,
            self.triggered_traps,
            matrix=self.matrix,
            coin_balance=self.coin_balance,
        )
        if decision.next_pos == self.position and self.degrade_level < 3:
            self._activate_degradation(3, BfsStrategy(), "当前策略无法移动，降级为BFS兜底路径")
            decision = self.active_strategy.decide(
                self.maze,
                self.position,
                self.collected_coins,
                self.triggered_traps,
                matrix=self.matrix,
                coin_balance=self.coin_balance,
            )
        return decision

    def _activate_degradation(self, level: int, strategy: ExplorationStrategy, message: str) -> None:
        self.degrade_level = level
        self.active_strategy = strategy
        self._snapshot(None, f"Layer {level} 自动降级：{message}")

    def _result_strategy_name(self) -> str:
        if self.degrade_level <= 1:
            return self.strategy.name
        return f"{self.strategy.name}+Layer{self.degrade_level}"

    def _apply_decision(self, decision: Decision) -> None:
        score_before = self.score
        next_pos = decision.next_pos
        if next_pos == self.position:
            self.failed = True
            self.message = "策略未给出可移动下一步，终止探险"
            self._snapshot(decision, self.message, failed=True)
            return
        if not self.maze.is_walkable(next_pos, self.matrix):
            self.failed = True
            self.message = f"策略尝试进入不可通行格子{next_pos}"
            self._snapshot(decision, self.message, failed=True)
            return

        self.position = next_pos
        self.maze_steps += 1
        self.path.append(next_pos)
        tile = self.maze.tile_at(next_pos, self.matrix)

        if tile == COIN:
            self.score += COIN_VALUE
            self.coin_balance += 1
            self.collected_coins.add(next_pos)
            self.maze.set_tile(next_pos, ROAD, self.matrix)
            self.message = f"拾取金币 +{COIN_VALUE}，金币余额 {self.coin_balance}"
        elif tile == TRAP:
            self.score += TRAP_VALUE
            coin_loss = min(self.coin_balance, TRAP_COIN_COST)
            if coin_loss:
                self.coin_balance -= coin_loss
                self.score -= coin_loss * COIN_VALUE
            self.triggered_traps.add(next_pos)
            self.maze.set_tile(next_pos, ROAD, self.matrix)
            if coin_loss:
                self.message = f"触发陷阱 {TRAP_VALUE}，扣除金币 {coin_loss}，金币余额 {self.coin_balance}"
            else:
                self.message = f"触发陷阱 {TRAP_VALUE}，无金币可扣"
        elif tile == BOSS and next_pos not in self.cleared_bosses:
            self.message = self._handle_boss(next_pos)
        elif tile == START:
            self.message = "返回起点"
        else:
            self.message = decision.reason or "移动"

        if self.score > score_before:
            self.no_resource_steps = 0
        else:
            self.no_resource_steps += 1
        self._snapshot(decision, self.message, reached_end=self.position == self.maze.end, failed=self.failed)

    def _handle_boss(self, pos: Pos) -> str:
        group = self.maze.bosses.get(pos, [])
        if not group:
            self.failed = True
            return f"BOSS位置{pos}缺少配置"

        messages: list[str] = []
        for boss in group:
            result = self._fight_boss_with_revival(boss)
            self.boss_results.append(result)
            if not result.success:
                self.failed = True
                self.degrade_level = max(self.degrade_level, 3)
                messages.append("Layer 3 兜底失败：" + self._boss_failure_message(boss, result))
                break
            self.boss_defeated += 1
            revive_text = f"，复活{result.revive_count}次" if result.revive_count else ""
            messages.append(f"{boss.boss_id} {result.rounds}回合击败{revive_text}，技能序列: {' -> '.join(result.skill_sequence)}")

        if not self.failed:
            self.cleared_bosses.add(pos)
            self.maze.set_tile(pos, ROAD, self.matrix)
        return "；".join(messages)

    def _fight_boss_with_revival(self, boss: Boss) -> BossResult:
        solved = boss_battle_optimal(boss, self.maze.skills)
        sequence = solved.skill_sequence
        if not sequence:
            return BossResult(False, 0, [], message=f"{boss.boss_id} 无可用技能序列")

        revive_count = 0
        total_rounds = 0
        all_used: list[str] = []
        all_history: list[int] = []

        while True:
            attempt_no = revive_count + 1
            executed = self._execute_boss_sequence(boss, self.maze.skills, sequence, attempt_no=attempt_no)
            total_rounds += executed.rounds
            all_used.extend(executed.skill_sequence)
            all_history.extend(executed.hp_history)

            if executed.success:
                return BossResult(
                    True,
                    total_rounds,
                    all_used,
                    revive_count=revive_count,
                    hp_history=all_history,
                    message=f"{boss.boss_id} 已击败",
                )
            if not self._consume_revive_if_possible(boss):
                return BossResult(
                    False,
                    total_rounds,
                    all_used,
                    revive_count=revive_count,
                    hp_history=all_history,
                    message=executed.message,
                )
            revive_count += 1

    def _execute_boss_sequence(
        self,
        boss: Boss,
        skills: list[Skill],
        sequence: list[str],
        attempt_no: int = 1,
    ) -> BossResult:
        skill_by_name = {skill.name: skill for skill in skills}
        cooldowns = {skill.name: 0 for skill in skills}
        hp = boss.hp
        history: list[int] = []
        used: list[str] = []

        for round_no, skill_name in enumerate(sequence, start=1):
            if round_no > boss.max_rounds:
                return BossResult(False, round_no - 1, used, hp_history=history, message=f"{boss.boss_id} 超过限定回合")
            skill = skill_by_name.get(skill_name)
            if skill is None:
                return BossResult(False, round_no - 1, used, hp_history=history, message=f"未知技能 {skill_name}")
            if cooldowns[skill.name] > 0:
                return BossResult(False, round_no - 1, used, hp_history=history, message=f"{skill.name} 冷却未结束")

            hp_before = hp
            hp = max(0, hp - skill.damage)
            history.append(hp)
            used.append(skill.name)
            for name in list(cooldowns):
                cooldowns[name] = max(0, cooldowns[name] - 1)
            cooldowns[skill.name] = skill.cooldown
            self.boss_rounds += 1
            event = BattleEvent(
                boss_id=boss.boss_id,
                round_no=round_no,
                skill_name=skill.name,
                damage=skill.damage,
                hp_before=hp_before,
                hp_after=hp,
                max_hp=boss.hp,
                cooldown=skill.cooldown,
                revive_count=attempt_no - 1,
                message=(
                    f"{boss.boss_id} 第{attempt_no}次挑战 第{round_no}回合使用{skill.name}，"
                    f"造成{skill.damage}伤害，剩余HP {hp}/{boss.hp}"
                ),
            )
            self._snapshot(None, event.message, battle_event=event, reached_end=False, failed=False)
            if hp <= 0:
                return BossResult(True, round_no, used, hp_history=history, message=f"{boss.boss_id} 已击败")

        return BossResult(False, len(used), used, hp_history=history, message=f"{boss.boss_id} 未被击败")

    def _consume_revive_if_possible(self, boss: Boss) -> bool:
        if boss.revive_cost <= 0:
            return False
        if self.coin_balance < boss.revive_cost:
            return False
        self.coin_balance -= boss.revive_cost
        self.score -= boss.revive_cost * COIN_VALUE
        self._snapshot(
            None,
            f"{boss.boss_id} 战斗失败，消耗 {boss.revive_cost} 枚金币复活；金币余额 {self.coin_balance}",
        )
        return True

    def _boss_failure_message(self, boss: Boss, result: BossResult) -> str:
        if result.revive_count:
            return f"{result.message}；已复活{result.revive_count}次，金币余额{self.coin_balance}不足，GAME OVER"
        if boss.revive_cost > 0:
            return f"{result.message}；金币余额{self.coin_balance}不足以支付复活消耗{boss.revive_cost}，GAME OVER"
        return f"{result.message}；无复活消耗配置，GAME OVER"

    def _snapshot(
        self,
        decision: Decision | None,
        message: str,
        battle_event: BattleEvent | None = None,
        reached_end: bool = False,
        failed: bool = False,
    ) -> None:
        self.snapshots.append(
            StepSnapshot(
                step=len(self.snapshots),
                position=self.position,
                score=self.score,
                coin_balance=self.coin_balance,
                maze_steps=self.maze_steps,
                boss_rounds=self.boss_rounds,
                coins_collected=len(self.collected_coins),
                traps_triggered=len(self.triggered_traps),
                boss_defeated=self.boss_defeated,
                path=list(self.path),
                matrix=self.maze.copy_matrix(self.matrix),
                decision=decision,
                battle_event=battle_event,
                message=message,
                reached_end=reached_end,
                failed=failed,
            )
        )


def run_full(
    maze: Maze,
    strategy: ExplorationStrategy | None = None,
    max_steps: int | None = None,
) -> AlgorithmResult:
    return ExplorationRunner(maze, strategy=strategy, max_steps=max_steps).run()
