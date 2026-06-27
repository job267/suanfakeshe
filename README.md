# AI迷宫玩家

本项目实现算法课设中的 AI 玩家任务：AI 从起点出发，在有限视野下拾取金币、避开陷阱、挑战 BOSS，并到达终点。标准评分口径使用 `Greedy` 策略，视野为 `3x3`。

## 目录结构

```text
.
├── main.py                  # 程序入口
├── run_ai_player.bat        # 统一启动脚本
├── clean_cache.bat          # 缓存清理脚本
├── src/ai_player/           # 后端算法与数据模型
├── gui/                     # PyQt 图形界面与图片资源
├── map/                     # 主地图、3x3用例、边界地图
├── outputs/reports/         # 报告图表和CSV输出
└── tests/                   # pytest 自检
```

## 运行方式

推荐直接使用脚本：

配置好对应环境后：
配置环境方法：
pip install -r "requirements.txt"

```bat
run_ai_player.bat
```


venv 环境：
run_ai_player_venv.bat


常用模式：

```bat
run_ai_player.bat gui        # 启动图形界面
run_ai_player.bat console    # 控制台完整探险
run_ai_player.bat compare    # 单地图多策略对比
run_ai_player.bat local      # 3x3局部贪心测试
run_ai_player.bat batch      # 批量边界地图测试并导出CSV
run_ai_player.bat report     # 导出路径图、热力图、BOSS图、对比图
run_ai_player.bat evaluate   # 地图难度评估
run_ai_player.bat qlearn     # Q-Learning对比入口
run_ai_player.bat clean      # 清理缓存文件
```

## AI玩家任务对应关系

| PDF任务要求 | 当前实现 |
| --- | --- |
| 3x3实时资源拾取 | `run_ai_player.bat local`，输出候选、选中目标、路径和平均拾取价值 |
| 完整迷宫探险 | GUI/console 模式展示过程 |
| 剩余资源价值、步数、比值 | 输出 `剩余资源价值`、`总步数`、`资源/步数比` |
| BOSS最少回合和技能序列 | 分支限界求解，GUI显示逐回合技能、伤害和HP |
| BOSS失败金币复活 | 失败后按 `CoinConsumption` 扣金币并重新挑战，金币不足则 GAME OVER |
| 过程可视化 | PyQt GUI、路径图、热力图、BOSS血量图 |

## 策略说明

- `Greedy`：标准评分策略，`3x3` 视野，按资源价值/距离贪心选择目标。
- `A*`：按曼哈顿启发式冲终点。
- `BFS`：无权最短路径。
- `Dijkstra`：把陷阱作为高代价格子，走低风险路径。
- `Adaptive`：增强对比策略，仍保持 `3x3` 视野；视野内无正收益资源时使用高陷阱惩罚路径冲终点。
- `Q-Learning`：表格型强化学习策略，已注册为普通算法，可在 GUI 下拉框、`--strategy Q-Learning` 和算法对比中直接调用。

完整探险内置自动降级：

- Layer 1：当前选择策略正常决策。
- Layer 2：连续多步资源无增长时，自动切换到 A* 直通终点，保证通关分。
- Layer 3：策略无法移动或 BOSS 兜底失败时明确终止，避免假死循环。

## 评分口径

当前项目按 PDF 中 AI 玩家任务的输出要求计算成绩：

```text
资源/步数比 = 抵达终点时的剩余资源价值 / 总步数
总步数 = 迷宫移动步数 + BOSS战回合数
```

因此当前不是“步数最少优先”，也不是“金币最少优先”。标准排序应先看是否通关，再看资源/步数比；同等情况下，剩余资源价值更高、总步数更少的结果更好。

## 地图和测试数据

- 主地图：`map/maze_15_15.json`
- 3x3局部贪心用例：`map/local_greedy_cases.json`
- 边界地图：`map/test_cases/`

边界地图覆盖：

- 无金币
- 无陷阱
- 密集金币
- 陷阱夹心
- BOSS金币不足
- 死胡同金币

## 报告输出

```bat
run_ai_player.bat report
```

生成文件位于 `outputs/reports/`，包括：

- 路径图
- 访问热力图
- BOSS血量变化图
- 算法对比柱状图：`2x3` 子图，包括剩余资源、总步数、资源/步数比、金币数、陷阱数、BOSS回合
- 批量测试 CSV：`batch_results.csv`

## 自检

当前测试覆盖解析、路径规划、BOSS最优性、复活重试、3x3贪心、批量地图、报告导出和完整探险。

## 输入格式

地图 JSON 使用字符矩阵：

- `#`：墙
- 空格：通路
- `S`：起点
- `E`：终点
- `G`：金币，价值 +50
- `T`：陷阱，价值 -30
- `B`：BOSS

BOSS 和技能字段：

```json
{
  "B": [36, 25],
  "PlayerSkills": [[8, 4], [2, 0], [4, 2], [6, 3]],
  "minRouds": 20,
  "CoinConsumption": 5
}
```
