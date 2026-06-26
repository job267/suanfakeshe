from __future__ import annotations

from math import ceil
from typing import Callable

from .model import Boss, BossResult, Skill

ProgressCallback = Callable[[int, int, str], bool]


def _tick_cooldowns(cooldowns: tuple[int, ...]) -> list[int]:
    return [max(0, value - 1) for value in cooldowns]


def boss_battle_optimal(boss: Boss, skills: list[Skill]) -> BossResult:
    if not skills:
        return BossResult(False, 0, [], message="没有可用技能")

    max_damage = max(skill.damage for skill in skills)
    no_cooldown_skills = [skill for skill in skills if skill.cooldown == 0]
    if not no_cooldown_skills:
        return BossResult(False, 0, [], message="缺少无冷却技能")

    fallback_skill = max(no_cooldown_skills, key=lambda item: item.damage)
    best_rounds = ceil(boss.hp / fallback_skill.damage)
    best_sequence = [fallback_skill.name] * best_rounds
    best_history = [max(0, boss.hp - fallback_skill.damage * (idx + 1)) for idx in range(best_rounds)]
    seen: dict[tuple[int, tuple[int, ...]], int] = {}

    skills_by_damage = sorted(enumerate(skills), key=lambda item: item[1].damage, reverse=True)

    def search(hp: int, cooldowns: tuple[int, ...], rounds: int, seq: list[str], history: list[int]) -> None:
        nonlocal best_rounds, best_sequence, best_history
        if hp <= 0:
            if rounds < best_rounds:
                best_rounds = rounds
                best_sequence = list(seq)
                best_history = list(history)
            return
        if rounds >= best_rounds:
            return
        lower_bound = ceil(hp / max_damage)
        if rounds + lower_bound >= best_rounds:
            return
        state = (hp, cooldowns)
        if seen.get(state, 10**9) <= rounds:
            return
        seen[state] = rounds

        for skill_idx, skill in skills_by_damage:
            if cooldowns[skill_idx] != 0:
                continue
            next_hp = max(0, hp - skill.damage)
            next_cooldowns = _tick_cooldowns(cooldowns)
            next_cooldowns[skill_idx] = skill.cooldown
            search(
                next_hp,
                tuple(next_cooldowns),
                rounds + 1,
                [*seq, skill.name],
                [*history, next_hp],
            )

    search(boss.hp, tuple(0 for _ in skills), 0, [], [])
    success = best_rounds <= boss.max_rounds
    message = (
        f"{boss.boss_id} 最优{best_rounds}回合击败"
        if success
        else f"{boss.boss_id} 最优需{best_rounds}回合，超过限制{boss.max_rounds}回合"
    )
    return BossResult(success, best_rounds, best_sequence, hp_history=best_history, message=message)


def boss_battle_execute(
    boss: Boss,
    skills: list[Skill],
    sequence: list[str] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> BossResult:
    if sequence is None:
        solved = boss_battle_optimal(boss, skills)
        sequence = solved.skill_sequence

    skill_by_name = {skill.name: skill for skill in skills}
    cooldowns = {skill.name: 0 for skill in skills}
    hp = boss.hp
    hp_history: list[int] = []
    used: list[str] = []

    for round_idx, skill_name in enumerate(sequence, start=1):
        if round_idx > boss.max_rounds:
            return BossResult(
                False,
                round_idx - 1,
                used,
                hp_history=hp_history,
                message=f"{boss.boss_id} 超过限定回合",
            )
        skill = skill_by_name.get(skill_name)
        if skill is None:
            return BossResult(False, round_idx - 1, used, hp_history=hp_history, message=f"未知技能: {skill_name}")
        if cooldowns[skill.name] > 0:
            return BossResult(False, round_idx - 1, used, hp_history=hp_history, message=f"{skill.name} 冷却未结束")

        hp = max(0, hp - skill.damage)
        hp_history.append(hp)
        used.append(skill.name)
        for key in list(cooldowns):
            cooldowns[key] = max(0, cooldowns[key] - 1)
        cooldowns[skill.name] = skill.cooldown

        if progress_callback and not progress_callback(round_idx, hp, skill.name):
            return BossResult(False, round_idx, used, hp_history=hp_history, message="用户终止BOSS战")
        if hp <= 0:
            return BossResult(True, round_idx, used, hp_history=hp_history, message=f"{boss.boss_id} 已击败")

    return BossResult(False, len(used), used, hp_history=hp_history, message=f"{boss.boss_id} 未被击败")


def brute_force_optimal(boss: Boss, skills: list[Skill], max_rounds: int | None = None) -> BossResult:
    limit = max_rounds or boss.max_rounds
    best: BossResult | None = None

    def walk(hp: int, cooldowns: tuple[int, ...], rounds: int, seq: list[str], history: list[int]) -> None:
        nonlocal best
        if hp <= 0:
            candidate = BossResult(True, rounds, list(seq), hp_history=list(history), message="暴力枚举命中")
            if best is None or candidate.rounds < best.rounds:
                best = candidate
            return
        if rounds >= limit or (best is not None and rounds >= best.rounds):
            return
        for idx, skill in enumerate(skills):
            if cooldowns[idx] != 0:
                continue
            next_hp = max(0, hp - skill.damage)
            next_cooldowns = _tick_cooldowns(cooldowns)
            next_cooldowns[idx] = skill.cooldown
            walk(next_hp, tuple(next_cooldowns), rounds + 1, [*seq, skill.name], [*history, next_hp])

    walk(boss.hp, tuple(0 for _ in skills), 0, [], [])
    return best or BossResult(False, limit, [], message="暴力枚举未找到可行解")
