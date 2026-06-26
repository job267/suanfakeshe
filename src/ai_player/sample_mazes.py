from __future__ import annotations

from .maze_parser import MazeLoader
from .model import Maze, Skill


def resource_corridor() -> Maze:
    return MazeLoader.from_layout(
        "资源回廊",
        [
            "#######",
            "#S G E#",
            "# ### #",
            "# G G #",
            "#######",
        ],
    )


def trap_demo() -> Maze:
    return MazeLoader.from_layout(
        "陷阱绕行",
        [
            "#########",
            "#S G T E#",
            "# ### # #",
            "#   G   #",
            "#########",
        ],
    )


def boss_demo() -> Maze:
    return MazeLoader.from_layout(
        "BOSS关卡",
        [
            "#########",
            "#S G B E#",
            "#       #",
            "#########",
        ],
        boss_hps=[20],
        skills=[Skill("技能-0", 6, 0), Skill("技能-1", 14, 2)],
        min_rounds=8,
    )


def all_samples() -> list[Maze]:
    return [resource_corridor(), trap_demo(), boss_demo()]
