from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtCore import QPointF, QRectF, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai_player import (
    BOSS,
    COIN,
    END,
    ROAD,
    START,
    TRAP,
    WALL,
    AlgorithmResult,
    Maze,
    MazeLoader,
    StepSnapshot,
    analysis_text,
    available_strategy_names,
    get_strategy,
    run_compare,
    run_full,
)
from ai_player.batch_test import format_batch_summary, run_batch_tests
from ai_player.evaluate import evaluate_maze
from ai_player.model import TILE_NAMES
from ai_player.visualize import export_boss_battle_png, export_compare_png, export_heatmap_png, export_path_png


class ExplorationWorker(QThread):
    snapshot_ready = pyqtSignal(object)
    finished_result = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, maze: Maze, strategy_name: str, delay_ms: int) -> None:
        super().__init__()
        self.maze = maze.clone()
        self.strategy_name = strategy_name
        self.delay_ms = delay_ms
        self._paused = False
        self._stopped = False

    def run(self) -> None:
        try:
            result = run_full(self.maze, strategy=get_strategy(self.strategy_name))
            for snapshot in result.snapshots:
                if self._stopped:
                    return
                while self._paused and not self._stopped:
                    self.msleep(50)
                if self._stopped:
                    return
                self.snapshot_ready.emit(snapshot)
                self.msleep(self.delay_ms)
            self.finished_result.emit(result)
        except Exception as exc:  # pragma: no cover - GUI safety net
            self.failed.emit(str(exc))

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stopped = True
        self._paused = False

    def set_delay(self, delay_ms: int) -> None:
        self.delay_ms = delay_ms


class MazeCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.maze: Maze | None = None
        self.snapshot: StepSnapshot | None = None
        self.setMinimumSize(520, 520)
        self.setAutoFillBackground(True)
        self.pixmaps = self._load_pixmaps()

    def _load_pixmaps(self) -> dict[int, QPixmap]:
        image_dir = ROOT_DIR / "gui" / "images"
        mapping = {
            COIN: image_dir / "coin.png",
            TRAP: image_dir / "trap.png",
            BOSS: image_dir / "boss.png",
            START: image_dir / "player.png",
        }
        pixmaps: dict[int, QPixmap] = {}
        for tile, path in mapping.items():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmaps[tile] = pixmap
        return pixmaps

    def set_maze(self, maze: Maze) -> None:
        self.maze = maze
        self.snapshot = None
        self.update()

    def set_snapshot(self, snapshot: StepSnapshot) -> None:
        self.snapshot = snapshot
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f6f7f2"))

        if self.maze is None:
            painter.setPen(QColor("#394047"))
            painter.setFont(QFont("Microsoft YaHei", 14))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "请加载迷宫 JSON")
            return

        matrix = self.snapshot.matrix if self.snapshot else self.maze.matrix
        rows = len(matrix)
        cols = len(matrix[0]) if rows else 0
        if rows == 0 or cols == 0:
            return

        margin = 18
        cell = min((self.width() - margin * 2) / cols, (self.height() - margin * 2) / rows)
        cell = max(10.0, cell)
        grid_w = cell * cols
        grid_h = cell * rows
        x0 = (self.width() - grid_w) / 2
        y0 = (self.height() - grid_h) / 2
        font = QFont("Microsoft YaHei", max(7, int(cell * 0.22)))

        path = set(self.snapshot.path if self.snapshot else [])
        player = self.snapshot.position if self.snapshot else self.maze.start
        for r, row in enumerate(matrix):
            for c, tile in enumerate(row):
                rect = QRectF(x0 + c * cell, y0 + r * cell, cell, cell)
                self._draw_tile(painter, rect, tile, font)
                if (r, c) in path and tile != WALL:
                    painter.setBrush(QColor(55, 130, 185, 72))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(rect.center(), cell * 0.15, cell * 0.15)

        self._draw_player(painter, QRectF(x0 + player[1] * cell, y0 + player[0] * cell, cell, cell))

        painter.setPen(QPen(QColor("#d0d5d8"), 1))
        for r in range(rows + 1):
            y = y0 + r * cell
            painter.drawLine(QPointF(x0, y), QPointF(x0 + grid_w, y))
        for c in range(cols + 1):
            x = x0 + c * cell
            painter.drawLine(QPointF(x, y0), QPointF(x, y0 + grid_h))

    def _draw_tile(self, painter: QPainter, rect: QRectF, tile: int, font: QFont) -> None:
        colors = {
            WALL: QColor("#263238"),
            ROAD: QColor("#fbfaf5"),
            START: QColor("#dff4df"),
            END: QColor("#f6d2ce"),
            COIN: QColor("#fff2a6"),
            TRAP: QColor("#f2c078"),
            BOSS: QColor("#d8c6ec"),
        }
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(colors.get(tile, QColor("#fbfaf5")))
        painter.drawRect(rect)

        if tile in (COIN, TRAP, BOSS) and tile in self.pixmaps:
            pad = rect.width() * 0.12
            pixmap = self.pixmaps[tile]
            painter.drawPixmap(rect.adjusted(pad, pad, -pad, -pad), pixmap, QRectF(pixmap.rect()))
            return

        if tile == END:
            painter.setPen(QColor("#8b2f2b"))
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "E")
        elif tile == START:
            painter.setPen(QColor("#1d6b3a"))
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "S")
        elif tile == COIN:
            painter.setBrush(QColor("#d69e00"))
            painter.drawEllipse(rect.center(), rect.width() * 0.22, rect.height() * 0.22)
        elif tile == TRAP:
            painter.setBrush(QColor("#c05621"))
            points = [
                rect.center() + QPointF(0, -rect.height() * 0.24),
                rect.center() + QPointF(-rect.width() * 0.24, rect.height() * 0.2),
                rect.center() + QPointF(rect.width() * 0.24, rect.height() * 0.2),
            ]
            painter.drawPolygon(QPolygonF(points))
        elif tile == BOSS:
            painter.setBrush(QColor("#805ad5"))
            painter.drawRoundedRect(rect.adjusted(rect.width() * 0.2, rect.height() * 0.2, -rect.width() * 0.2, -rect.height() * 0.2), 3, 3)

    def _draw_player(self, painter: QPainter, rect: QRectF) -> None:
        if START in self.pixmaps:
            pad = rect.width() * 0.08
            pixmap = self.pixmaps[START]
            painter.drawPixmap(rect.adjusted(pad, pad, -pad, -pad), pixmap, QRectF(pixmap.rect()))
            return
        painter.setPen(QPen(QColor("#0f5132"), 2))
        painter.setBrush(QColor("#2f9e44"))
        painter.drawEllipse(rect.center(), rect.width() * 0.32, rect.height() * 0.32)


class MainWindow(QMainWindow):
    def __init__(self, map_path: str | Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("AI迷宫玩家")
        self.resize(1180, 760)
        self.worker: ExplorationWorker | None = None
        self.current_result: AlgorithmResult | None = None
        self.compare_result = None
        self.step_snapshots: list[StepSnapshot] = []
        self.step_index = 0
        self.maze_path = Path(map_path) if map_path else ROOT_DIR / "map" / "maze_15_15.json"
        self.maze = MazeLoader.load(self.maze_path)
        self._build_ui()
        self._refresh_maze()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        self.setCentralWidget(central)

        controls = self._build_controls()
        controls.setFixedWidth(285)
        root.addWidget(controls)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        explore_tab = QWidget()
        explore_layout = QHBoxLayout(explore_tab)
        explore_layout.setContentsMargins(8, 8, 8, 8)
        explore_layout.setSpacing(12)
        self.canvas = MazeCanvas()
        explore_layout.addWidget(self.canvas, 1)

        info_box = QGroupBox("实时状态")
        info_box.setMinimumWidth(300)
        info_layout = QVBoxLayout(info_box)
        self.status_label = QLabel()
        self.metrics_label = QLabel()
        self.metrics_label.setWordWrap(True)
        self.skill_table = QTableWidget(0, 3)
        self.skill_table.setHorizontalHeaderLabels(["技能", "伤害", "冷却"])
        self.skill_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.skill_table.verticalHeader().setVisible(False)
        self.skill_table.setMaximumHeight(130)
        self.boss_hp_bar = QProgressBar()
        self.boss_hp_bar.setFormat("BOSS HP")
        self.boss_hp_bar.setValue(0)
        self.decision_text = QTextEdit()
        self.decision_text.setReadOnly(True)
        self.decision_text.setMinimumHeight(210)
        self.decision_text.setPlaceholderText("运行后显示贪心候选、路径和事件")
        info_layout.addWidget(self.status_label)
        info_layout.addWidget(self.metrics_label)
        info_layout.addWidget(QLabel("技能配置"))
        info_layout.addWidget(self.skill_table)
        info_layout.addWidget(self.boss_hp_bar)
        info_layout.addWidget(QLabel("决策与事件"))
        info_layout.addWidget(self.decision_text, 1)
        explore_layout.addWidget(info_box)
        self.tabs.addTab(explore_tab, "实时探险")

        compare_tab = QWidget()
        compare_layout = QVBoxLayout(compare_tab)
        compare_layout.setContentsMargins(8, 8, 8, 8)
        compare_bar = QHBoxLayout()
        self.compare_button = QPushButton("运行算法对比")
        self.compare_button.clicked.connect(self._run_compare)
        self.evaluate_button = QPushButton("评估地图")
        self.evaluate_button.clicked.connect(self._evaluate_maze)
        self.batch_button = QPushButton("批量测试")
        self.batch_button.clicked.connect(self._run_batch_tests)
        self.export_button = QPushButton("导出报告图表")
        self.export_button.clicked.connect(self._export_report)
        compare_bar.addWidget(self.compare_button)
        compare_bar.addWidget(self.evaluate_button)
        compare_bar.addWidget(self.batch_button)
        compare_bar.addWidget(self.export_button)
        compare_bar.addStretch(1)
        compare_layout.addLayout(compare_bar)
        self.compare_table = QTableWidget(0, 11)
        self.compare_table.setHorizontalHeaderLabels(["算法", "到达", "剩余资源", "金币余额", "迷宫步数", "BOSS回合", "总步数", "金币", "陷阱", "BOSS", "资源/步数"])
        self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.compare_table.verticalHeader().setVisible(False)
        self.compare_text = QTextEdit()
        self.compare_text.setReadOnly(True)
        self.compare_text.setMinimumHeight(120)
        compare_layout.addWidget(self.compare_table, 1)
        compare_layout.addWidget(self.compare_text)
        self.tabs.addTab(compare_tab, "算法对比")

    def _build_controls(self) -> QGroupBox:
        box = QGroupBox("控制")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        self.map_label = QLabel()
        self.map_label.setWordWrap(True)
        load_button = QPushButton("加载迷宫 JSON")
        load_button.clicked.connect(self._choose_maze)
        layout.addWidget(self.map_label)
        layout.addWidget(load_button)

        grid = QGridLayout()
        grid.addWidget(QLabel("策略"), 0, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(available_strategy_names())
        grid.addWidget(self.strategy_combo, 0, 1)
        grid.addWidget(QLabel("速度"), 1, 0)
        self.delay_slider = QSlider(Qt.Orientation.Horizontal)
        self.delay_slider.setRange(40, 900)
        self.delay_slider.setValue(180)
        self.delay_slider.valueChanged.connect(self._delay_changed)
        grid.addWidget(self.delay_slider, 1, 1)
        layout.addLayout(grid)

        self.start_button = QPushButton("开始")
        self.step_button = QPushButton("单步执行")
        self.pause_button = QPushButton("暂停")
        self.stop_button = QPushButton("终止")
        self.reset_button = QPushButton("重置")
        self.start_button.clicked.connect(self._start)
        self.step_button.clicked.connect(self._step_once)
        self.pause_button.clicked.connect(self._toggle_pause)
        self.stop_button.clicked.connect(self._stop)
        self.reset_button.clicked.connect(self._reset)
        for button in (self.start_button, self.step_button, self.pause_button, self.stop_button, self.reset_button):
            button.setMinimumHeight(34)
            layout.addWidget(button)
        layout.addStretch(1)
        return box

    def _refresh_maze(self) -> None:
        self.canvas.set_maze(self.maze)
        self.map_label.setText(f"当前地图：{self.maze_path.name}\n尺寸：{self.maze.height} x {self.maze.width}")
        self.status_label.setText("状态：未开始")
        self.metrics_label.setText(
            f"起点：{self.maze.start}  终点：{self.maze.end}\n"
            f"金币：{self.maze.total_coins}  BOSS：{self.maze.boss_count()}  技能：{len(self.maze.skills)}"
        )
        self._populate_skill_table()
        self.boss_hp_bar.setRange(0, 1)
        self.boss_hp_bar.setValue(0)
        self.boss_hp_bar.setFormat("BOSS HP")
        self.decision_text.clear()

    def _populate_skill_table(self) -> None:
        self.skill_table.setRowCount(len(self.maze.skills))
        for row, skill in enumerate(self.maze.skills):
            for col, value in enumerate((skill.name, str(skill.damage), str(skill.cooldown))):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.skill_table.setItem(row, col, item)

    def _choose_maze(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择迷宫 JSON", str(ROOT_DIR / "map"), "JSON Files (*.json)")
        if not path:
            return
        try:
            self._stop()
            self._clear_step_state()
            self.maze_path = Path(path)
            self.maze = MazeLoader.load(self.maze_path)
            self._refresh_maze()
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", str(exc))

    def _start(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self._clear_step_state()
        self.current_result = None
        self.worker = ExplorationWorker(self.maze, self.strategy_combo.currentText(), self.delay_slider.value())
        self.worker.snapshot_ready.connect(self._on_snapshot)
        self.worker.finished_result.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()
        self.status_label.setText("状态：运行中")
        self.decision_text.clear()
        self.start_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.pause_button.setText("暂停")

    def _step_once(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        try:
            if not self.step_snapshots:
                self.current_result = run_full(self.maze, strategy=get_strategy(self.strategy_combo.currentText()))
                self.step_snapshots = list(self.current_result.snapshots)
                self.step_index = 0
                self.decision_text.clear()
        except Exception as exc:
            QMessageBox.critical(self, "单步运行失败", str(exc))
            return

        if self.step_index >= len(self.step_snapshots):
            if self.current_result:
                self._on_finished(self.current_result)
            return

        snapshot = self.step_snapshots[self.step_index]
        self._on_snapshot(snapshot)
        self.status_label.setText(f"状态：单步 {self.step_index + 1}/{len(self.step_snapshots)}  位置：{snapshot.position}")
        self.step_index += 1
        if self.step_index >= len(self.step_snapshots) and self.current_result:
            self._on_finished(self.current_result)

    def _toggle_pause(self) -> None:
        if not self.worker or not self.worker.isRunning():
            return
        if self.pause_button.text() == "暂停":
            self.worker.pause()
            self.pause_button.setText("继续")
            self.status_label.setText("状态：已暂停")
        else:
            self.worker.resume()
            self.pause_button.setText("暂停")
            self.status_label.setText("状态：运行中")

    def _stop(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1500)
        self.start_button.setEnabled(True)
        self.step_button.setEnabled(True)
        self.pause_button.setText("暂停")

    def _reset(self) -> None:
        self._stop()
        self._clear_step_state()
        self._refresh_maze()

    def _clear_step_state(self) -> None:
        self.step_snapshots = []
        self.step_index = 0

    def _delay_changed(self, value: int) -> None:
        if self.worker:
            self.worker.set_delay(value)

    def _on_snapshot(self, snapshot: StepSnapshot) -> None:
        self.canvas.set_snapshot(snapshot)
        state = "失败" if snapshot.failed else ("到达终点" if snapshot.reached_end else "运行中")
        self.status_label.setText(f"状态：{state}  位置：{snapshot.position}")
        self.metrics_label.setText(
            f"剩余资源价值：{snapshot.score}\n"
            f"金币余额：{snapshot.coin_balance}\n"
            f"迷宫步数：{snapshot.maze_steps}  BOSS回合：{snapshot.boss_rounds}\n"
            f"金币：{snapshot.coins_collected}  陷阱：{snapshot.traps_triggered}  BOSS：{snapshot.boss_defeated}"
        )
        detail = [f"[{snapshot.step}] {snapshot.message}"]
        if snapshot.battle_event:
            event = snapshot.battle_event
            self.boss_hp_bar.setRange(0, event.max_hp)
            self.boss_hp_bar.setValue(event.hp_after)
            self.boss_hp_bar.setFormat(f"{event.boss_id} HP {event.hp_after}/{event.max_hp}")
            detail.append(
                f"BOSS战：第{event.round_no}回合 | 技能 {event.skill_name} | "
                f"伤害 {event.damage} | HP {event.hp_before}->{event.hp_after} | 冷却 {event.cooldown}"
            )
        if snapshot.decision:
            decision = snapshot.decision
            if decision.coins_in_view:
                detail.append("金币候选：" + " > ".join(item.label for item in decision.coins_in_view))
            if decision.traps_in_view:
                detail.append("陷阱：" + " > ".join(item.label for item in decision.traps_in_view))
            detail.append(f"选中：{decision.selected_target or '无'}")
            detail.append(f"原因：{decision.reason}")
        self.decision_text.append("\n".join(detail))

    def _on_finished(self, result: AlgorithmResult) -> None:
        self.current_result = result
        self.status_label.setText(f"状态：{'通关' if result.reached_end else '未通关'}")
        self.start_button.setEnabled(True)
        self.step_button.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self.status_label.setText("状态：运行异常")
        QMessageBox.critical(self, "运行异常", message)
        self.start_button.setEnabled(True)
        self.step_button.setEnabled(True)

    def _on_worker_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.step_button.setEnabled(True)
        self.pause_button.setText("暂停")

    def _run_compare(self) -> None:
        try:
            compare = run_compare(self.maze)
            self.compare_result = compare
        except Exception as exc:
            QMessageBox.critical(self, "对比失败", str(exc))
            return
        self.compare_table.setRowCount(len(compare.results))
        for row, result in enumerate(compare.results):
            values = [
                result.strategy_name,
                "是" if result.reached_end else "否",
                str(result.remaining_resource_value),
                str(result.coin_balance),
                str(result.maze_steps),
                str(result.boss_rounds),
                str(result.total_steps),
                str(result.coins_collected),
                str(result.traps_triggered),
                str(result.boss_defeated),
                f"{result.resource_step_ratio:.2f}",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.compare_table.setItem(row, col, item)
        self.compare_text.setPlainText(analysis_text(compare))

    def _evaluate_maze(self) -> None:
        difficulty = evaluate_maze(self.maze)
        self.compare_text.setPlainText("\n".join(difficulty.as_lines()))
        self.tabs.setCurrentIndex(1)

    def _run_batch_tests(self) -> None:
        try:
            summary = run_batch_tests(ROOT_DIR / "map" / "test_cases")
        except Exception as exc:
            QMessageBox.critical(self, "批量测试失败", str(exc))
            return
        self.compare_text.setPlainText(format_batch_summary(summary))
        self.tabs.setCurrentIndex(1)

    def _export_report(self) -> None:
        try:
            result = self.current_result or run_full(self.maze, strategy=get_strategy(self.strategy_combo.currentText()))
            compare = self.compare_result or run_compare(self.maze)
            outputs = [
                export_path_png(result, ROOT_DIR / "outputs" / "reports"),
                export_heatmap_png(result, ROOT_DIR / "outputs" / "reports"),
                export_boss_battle_png(result, ROOT_DIR / "outputs" / "reports"),
                export_compare_png(compare.results, ROOT_DIR / "outputs" / "reports"),
            ]
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        self.compare_text.setPlainText("已导出报告图表：\n" + "\n".join(str(path) for path in outputs))
        self.tabs.setCurrentIndex(1)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop()
        event.accept()


def run_gui(map_path: str | Path | None = None) -> int:
    app = QApplication(sys.argv)
    window = MainWindow(map_path)
    window.show()
    return app.exec()
