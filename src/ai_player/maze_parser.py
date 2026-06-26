from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .model import (
    BOSS,
    DEFAULT_SKILLS,
    END,
    START,
    SYMBOL_TO_TILE,
    Boss,
    Maze,
    Pos,
    Skill,
)


class MazeValidationError(ValueError):
    pass


class MazeParser(ABC):
    @abstractmethod
    def parse(self, path: str | Path) -> Maze:
        raise NotImplementedError


class JsonMazeParser(MazeParser):
    def parse(self, path: str | Path) -> Maze:
        file_path = Path(path)
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        char_matrix = payload.get("maze")
        if not isinstance(char_matrix, list):
            raise MazeValidationError("JSON必须包含 maze 二维字符矩阵")

        matrix = self._convert_matrix(char_matrix)
        boss_hps = payload.get("B", [])
        if boss_hps is None:
            boss_hps = []
        if not isinstance(boss_hps, list):
            raise MazeValidationError("字段 B 必须是数组")

        min_rounds = int(payload.get("minRouds", payload.get("minRounds", 20)))
        coin_consumption = int(payload.get("CoinConsumption", 5))
        skills = self._parse_skills(payload.get("PlayerSkills"))
        bosses = self._parse_bosses(matrix, boss_hps, min_rounds, coin_consumption)

        maze = Maze(
            name=str(payload.get("name") or file_path.stem),
            matrix=matrix,
            bosses=bosses,
            skills=skills,
            min_rounds=min_rounds,
            coin_consumption=coin_consumption,
        )
        APIValidator.validate(maze)
        return maze

    def _convert_matrix(self, char_matrix: list[Any]) -> list[list[int]]:
        matrix: list[list[int]] = []
        for row_idx, row in enumerate(char_matrix):
            if not isinstance(row, list):
                raise MazeValidationError(f"maze第{row_idx}行必须是数组")
            converted_row: list[int] = []
            for col_idx, symbol in enumerate(row):
                if symbol not in SYMBOL_TO_TILE:
                    raise MazeValidationError(f"非法字符 {symbol!r} 位于({row_idx},{col_idx})")
                converted_row.append(SYMBOL_TO_TILE[symbol])
            matrix.append(converted_row)
        return matrix

    def _parse_skills(self, raw_skills: Any) -> list[Skill]:
        if raw_skills is None:
            return list(DEFAULT_SKILLS)
        if not isinstance(raw_skills, list) or not raw_skills:
            raise MazeValidationError("PlayerSkills 必须是非空数组")

        skills: list[Skill] = []
        for idx, item in enumerate(raw_skills):
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], int)
                or not isinstance(item[1], int)
            ):
                raise MazeValidationError(f"PlayerSkills[{idx}] 必须为 [伤害, 冷却] 整数数组")
            damage, cooldown = item
            if damage <= 0 or cooldown < 0:
                raise MazeValidationError(f"PlayerSkills[{idx}] 伤害需>0，冷却需>=0")
            skills.append(Skill(f"技能-{idx}", damage=damage, cooldown=cooldown))
        return skills

    def _parse_bosses(
        self,
        matrix: list[list[int]],
        boss_hps: list[Any],
        min_rounds: int,
        coin_consumption: int,
    ) -> dict[Pos, list[Boss]]:
        positions = [
            (row_idx, col_idx)
            for row_idx, row in enumerate(matrix)
            for col_idx, tile in enumerate(row)
            if tile == BOSS
        ]
        for idx, hp in enumerate(boss_hps):
            if not isinstance(hp, int) or hp <= 0:
                raise MazeValidationError(f"B[{idx}] 必须为正整数血量")

        if not positions and boss_hps:
            raise MazeValidationError("B数组有血量，但迷宫中没有 BOSS 标记")
        if positions and not boss_hps:
            raise MazeValidationError("迷宫中存在 BOSS，但 B 数组为空")

        bosses: dict[Pos, list[Boss]] = {}
        if len(positions) == 1:
            pos = positions[0]
            bosses[pos] = [
                Boss(f"BOSS-{idx + 1}", pos, int(hp), min_rounds, coin_consumption)
                for idx, hp in enumerate(boss_hps)
            ]
            return bosses

        if len(positions) != len(boss_hps):
            raise MazeValidationError("多个BOSS位置时，BOSS位置数量必须与B数组长度一致")

        for idx, (pos, hp) in enumerate(zip(positions, boss_hps, strict=True)):
            bosses[pos] = [Boss(f"BOSS-{idx + 1}", pos, int(hp), min_rounds, coin_consumption)]
        return bosses


class MazeLoader:
    _parsers: dict[str, MazeParser] = {".json": JsonMazeParser()}

    @classmethod
    def load(cls, path: str | Path) -> Maze:
        file_path = Path(path)
        parser = cls._parsers.get(file_path.suffix.lower())
        if parser is None:
            raise MazeValidationError(f"不支持的迷宫文件类型: {file_path.suffix}")
        return parser.parse(file_path)

    @classmethod
    def from_layout(
        cls,
        name: str,
        layout: list[str],
        boss_hps: list[int] | None = None,
        skills: list[Skill] | None = None,
        min_rounds: int = 20,
        coin_consumption: int = 5,
    ) -> Maze:
        matrix = JsonMazeParser()._convert_matrix([list(row) for row in layout])
        raw_skills = skills or list(DEFAULT_SKILLS)
        bosses = JsonMazeParser()._parse_bosses(matrix, boss_hps or [], min_rounds, coin_consumption)
        maze = Maze(
            name=name,
            matrix=matrix,
            bosses=bosses,
            skills=raw_skills,
            min_rounds=min_rounds,
            coin_consumption=coin_consumption,
        )
        APIValidator.validate(maze)
        return maze


class APIValidator:
    @staticmethod
    def validate(maze: Maze) -> None:
        APIValidator._validate_matrix(maze)
        APIValidator._validate_required_points(maze)
        APIValidator._validate_bosses(maze)
        APIValidator._validate_skills(maze)
        APIValidator._validate_connectivity(maze)

    @staticmethod
    def _validate_matrix(maze: Maze) -> None:
        if not maze.matrix or not maze.matrix[0]:
            raise MazeValidationError("迷宫矩阵不能为空")
        width = len(maze.matrix[0])
        for row_idx, row in enumerate(maze.matrix):
            if len(row) != width:
                raise MazeValidationError(f"迷宫第{row_idx}行长度不一致")

    @staticmethod
    def _validate_required_points(maze: Maze) -> None:
        for tile, name in ((START, "起点"), (END, "终点")):
            count = sum(1 for row in maze.matrix for item in row if item == tile)
            if count != 1:
                raise MazeValidationError(f"{name}必须有且仅有一个，实际为{count}")

    @staticmethod
    def _validate_bosses(maze: Maze) -> None:
        if maze.min_rounds <= 0:
            raise MazeValidationError("minRouds 必须大于0")
        if maze.coin_consumption < 0:
            raise MazeValidationError("CoinConsumption 必须大于等于0")
        boss_positions = {
            (row_idx, col_idx)
            for row_idx, row in enumerate(maze.matrix)
            for col_idx, tile in enumerate(row)
            if tile == BOSS
        }
        if set(maze.bosses) != boss_positions:
            raise MazeValidationError("BOSS对象位置必须与矩阵中的 B 标记一致")
        for pos, group in maze.bosses.items():
            if not group:
                raise MazeValidationError(f"BOSS位置{pos}没有血量配置")
            for boss in group:
                if boss.position != pos or boss.hp <= 0:
                    raise MazeValidationError(f"BOSS配置非法: {boss}")

    @staticmethod
    def _validate_skills(maze: Maze) -> None:
        if not maze.skills:
            raise MazeValidationError("技能列表不能为空")
        if not any(skill.cooldown == 0 for skill in maze.skills):
            raise MazeValidationError("至少需要一个冷却为0的技能")
        for skill in maze.skills:
            if skill.damage <= 0 or skill.cooldown < 0:
                raise MazeValidationError(f"技能配置非法: {skill}")

    @staticmethod
    def _validate_connectivity(maze: Maze) -> None:
        start = maze.start
        end = maze.end
        queue = [start]
        visited = {start}
        while queue:
            pos = queue.pop(0)
            if pos == end:
                return
            for nxt in maze.neighbors(pos):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        raise MazeValidationError("起点到终点之间不存在通路")
