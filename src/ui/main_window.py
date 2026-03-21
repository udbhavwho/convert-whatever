from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, QSize
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QSlider,
    QHBoxLayout,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QStackedLayout,
)

from dependency_manager.checker import get_dependency_status
from core.file_types import validate_same_family
from ui.progress_dialog import ConversionProgressDialog
from workers.extract_frames_worker import ExtractFramesWorker
from workers.gif_to_video_worker import GifToVideoWorker
from workers.image_compress_worker import ImageCompressWorker
from workers.image_convert_worker import ImageConvertWorker
from workers.media_convert_worker import MediaConvertWorker
from workers.video_to_audio_worker import VideoToAudioWorker
from workers.video_to_gif_worker import VideoToGifWorker


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Convert Whatever")
        self.resize(1120, 720)

        self.selected_files: list[str] = []
        self.selected_family: str | None = None

        self.action_cards: dict[str, dict[str, Any]] = {}

        self.task_queue: list[dict[str, Any]] = []
        self.current_task_index: int = -1
        self.current_task: dict[str, Any] | None = None

        self.current_thread: QThread | None = None
        self.current_worker: Any | None = None

        self.pending_status: str | None = None
        self.pending_message: str = ""

        self.progress_dialog: ConversionProgressDialog | None = None
        self.output_root_dir: str | None = None

        self.pipeline_mode: str | None = None
        self.pipeline_temp_dir: str | None = None
        self.pipeline_final_dir: str | None = None
        self.pipeline_output_format: str | None = None
        self.pipeline_strength: int | None = None

        self._apply_base_style()
        self._build_ui()
        self.refresh_dependencies()
        self.update_file_area()
        self.rebuild_actions_panel()
        self.update_right_panel_state()
        self.update_start_button_state()

    def _apply_base_style(self):
        self.setStyleSheet(
            """
            QWidget {
                background-color: #05080f;
                color: #f3f5f8;
                border: none;
            }

            QLabel {
                background: transparent;
                border: none;
            }

            QPushButton {
                background-color: rgba(255,255,255,0.90);
                color: #111318;
                border: none;
                border-radius: 18px;
                padding: 10px 18px;
                font-size: 14px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: rgba(255,255,255,0.97);
            }

            QPushButton:disabled {
                background-color: rgba(255,255,255,0.18);
                color: rgba(255,255,255,0.58);
            }

            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 0;
            }

            QListWidget::item {
                border: none;
                margin: 0;
                padding: 0;
            }

            QScrollArea {
                background: transparent;
                border: none;
            }

            QComboBox {
                background-color: rgba(255,255,255,0.06);
                color: #f3f5f8;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 12px;
                padding: 8px 12px;
                min-height: 18px;
            }

            QComboBox::drop-down {
                border: none;
                width: 28px;
                background: transparent;
            }

            QComboBox QAbstractItemView {
                background-color: #0b1220;
                color: #f3f5f8;
                border: 1px solid rgba(255,255,255,0.10);
                selection-background-color: rgba(255,255,255,0.10);
            }

            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255,255,255,0.10);
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
                background: rgba(255,255,255,0.92);
            }

            QCheckBox {
                background: transparent;
                border: none;
                font-size: 15px;
                font-weight: 700;
                spacing: 10px;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 1px solid rgba(255,255,255,0.24);
                background: rgba(255,255,255,0.04);
            }

            QCheckBox::indicator:checked {
                background: rgba(255,255,255,0.92);
            }

            QScrollBar:vertical {
                width: 10px;
                background: transparent;
            }

            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.18);
                border-radius: 5px;
                min-height: 30px;
            }
            """
        )

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("background: transparent;")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(16)

        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background: transparent;")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)

        self.divider = QFrame()
        self.divider.setFixedWidth(1)
        self.divider.setStyleSheet("background-color: rgba(255,255,255,0.22);")

        root.addWidget(self.left_panel, 5)
        root.addWidget(self.divider)
        root.addWidget(self.right_panel, 6)

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        self.title_label = QLabel("Convert Whatever")
        self.title_label.setStyleSheet("font-size: 31px; font-weight: 800;")

        self.status_label = QLabel("Checking dependencies...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.68); font-size: 12px;")

        add_row = QHBoxLayout()
        add_row.setContentsMargins(0, 4, 0, 8)

        self.add_files_button = QPushButton("Add Files")
        self.add_files_button.setFixedWidth(165)
        self.add_files_button.setMinimumHeight(48)
        self.add_files_button.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255,255,255,0.98);
                color: #0b0d12;
                border: none;
                border-radius: 20px;
                padding: 12px 20px;
                font-size: 15px;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: #ffffff;
            }

            QPushButton:disabled {
                background-color: rgba(255,255,255,0.22);
                color: rgba(255,255,255,0.45);
            }
            """
        )
        self.add_files_button.clicked.connect(self.select_files)

        add_row.addWidget(self.add_files_button)
        add_row.addStretch(1)

        self.file_box = QFrame()
        self.file_box.setStyleSheet(
            """
            QFrame {
                background-color: rgba(255,255,255,0.025);
                border-radius: 20px;
            }
            """
        )
        self.file_box_layout = QVBoxLayout(self.file_box)
        self.file_box_layout.setContentsMargins(18, 18, 18, 18)
        self.file_box_layout.setSpacing(10)

        self.file_stack_host = QWidget()
        self.file_stack = QStackedLayout(self.file_stack_host)
        self.file_stack.setContentsMargins(0, 0, 0, 0)

        self.empty_label = QLabel("Empty")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(
            "font-size: 30px; font-weight: 600; color: rgba(255,255,255,0.22);"
        )

        self.files_list = QListWidget()
        self.files_list.setSpacing(10)

        self.file_stack.addWidget(self.empty_label)
        self.file_stack.addWidget(self.files_list)
        self.file_box_layout.addWidget(self.file_stack_host, 1)

        start_row = QHBoxLayout()
        start_row.setContentsMargins(0, 6, 0, 0)

        self.start_button = QPushButton("Start Conversion")
        self.start_button.setFixedWidth(235)
        self.start_button.setMinimumHeight(48)
        self.start_button.setEnabled(False)
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255,255,255,0.90);
                color: #111318;
                border: none;
                border-radius: 18px;
                padding: 10px 18px;
                font-size: 14px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: rgba(255,255,255,0.97);
            }

            QPushButton:disabled {
                background-color: rgba(255,255,255,0.18);
                color: rgba(255,255,255,0.60);
            }
            """
        )
        self.start_button.clicked.connect(self.start_conversion)

        start_row.addWidget(self.start_button)
        start_row.addStretch(1)

        self.left_layout.addWidget(self.title_label)
        self.left_layout.addWidget(self.status_label)
        self.left_layout.addLayout(add_row)
        self.left_layout.addWidget(self.file_box, 1)
        self.left_layout.addLayout(start_row)

    def _build_right_panel(self):
        self.right_stack_host = QWidget()
        self.right_stack = QStackedLayout(self.right_stack_host)
        self.right_stack.setContentsMargins(0, 0, 0, 0)

        self._build_info_page()
        self._build_actions_page()

        self.right_stack.addWidget(self.info_page)
        self.right_stack.addWidget(self.actions_page)

        self.right_layout.addWidget(self.right_stack_host)

    def _build_info_page(self):
        self.info_page = QWidget()
        self.info_layout = QVBoxLayout(self.info_page)
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_layout.setSpacing(16)

        watermark_row = QHBoxLayout()
        watermark_row.addStretch(1)

        self.info_watermark_label = QLabel("Made by: udbhavwho")
        self.info_watermark_label.setStyleSheet("color: rgba(255,255,255,0.50); font-size: 12px;")
        watermark_row.addWidget(self.info_watermark_label)

        self.rules_title = QLabel("Rules")
        self.rules_title.setStyleSheet("font-size: 22px; font-weight: 800;")

        self.rule_1 = QLabel(
            "1. This tool supports a wide range of file formats and conversion workflows."
        )
        self.rule_2 = QLabel(
            "2. Batch conversion only works with files from the same data family. Mixed file types cannot be grouped together."
        )
        self.rule_3 = QLabel(
            "3. You can choose one or multiple compatible actions before starting a conversion."
        )
        self.rule_4 = QLabel(
            "4. Unsupported or unidentified files will be blocked before processing begins."
        )

        for label in (self.rule_1, self.rule_2, self.rule_3, self.rule_4):
            label.setWordWrap(True)
            label.setStyleSheet("color: rgba(255,255,255,0.86); font-size: 15px;")

        self.future_note = QLabel(
            "More formats, tools, and advanced conversion options will be added in future updates."
        )
        self.future_note.setWordWrap(True)
        self.future_note.setStyleSheet("color: rgba(255,255,255,0.52); font-size: 12px;")

        self.info_layout.addLayout(watermark_row)
        self.info_layout.addSpacing(4)
        self.info_layout.addWidget(self.rules_title)
        self.info_layout.addWidget(self.rule_1)
        self.info_layout.addWidget(self.rule_2)
        self.info_layout.addWidget(self.rule_3)
        self.info_layout.addWidget(self.rule_4)
        self.info_layout.addStretch(1)
        self.info_layout.addWidget(self.future_note)

    def _build_actions_page(self):
        self.actions_page = QWidget()
        self.actions_page_layout = QVBoxLayout(self.actions_page)
        self.actions_page_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_page_layout.setSpacing(14)

        actions_header = QHBoxLayout()

        self.actions_title = QLabel("Available Actions")
        self.actions_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        actions_header.addWidget(self.actions_title)
        actions_header.addStretch(1)

        self.actions_watermark_label = QLabel("Made by: udbhavwho")
        self.actions_watermark_label.setStyleSheet("color: rgba(255,255,255,0.42); font-size: 12px;")
        actions_header.addWidget(self.actions_watermark_label)

        self.actions_placeholder = QLabel("Add files to see supported actions for that file type.")
        self.actions_placeholder.setWordWrap(True)
        self.actions_placeholder.setStyleSheet("color: rgba(255,255,255,0.56);")

        self.actions_scroll = QScrollArea()
        self.actions_scroll.setWidgetResizable(True)
        self.actions_scroll.setFrameShape(QFrame.NoFrame)

        self.actions_scroll_content = QWidget()
        self.actions_layout = QVBoxLayout(self.actions_scroll_content)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(14)
        self.actions_scroll.setWidget(self.actions_scroll_content)

        self.actions_summary_label = QLabel("Choose one or more actions to continue.")
        self.actions_summary_label.setWordWrap(True)
        self.actions_summary_label.setStyleSheet("color: rgba(255,255,255,0.72); font-size: 13px;")

        self.actions_page_layout.addLayout(actions_header)
        self.actions_page_layout.addWidget(self.actions_placeholder)
        self.actions_page_layout.addWidget(self.actions_scroll, 1)
        self.actions_page_layout.addWidget(self.actions_summary_label)

    def refresh_dependencies(self):
        status = get_dependency_status()
        ffmpeg_ok = status.get("ffmpeg", False)
        ffprobe_ok = status.get("ffprobe", False)

        if ffmpeg_ok and ffprobe_ok:
            self.status_label.setText("Dependencies ready: ffmpeg and ffprobe detected.")
        else:
            missing = []
            if not ffmpeg_ok:
                missing.append("ffmpeg")
            if not ffprobe_ok:
                missing.append("ffprobe")
            self.status_label.setText(f"Missing dependencies: {', '.join(missing)}")

    def select_files(self):
        if self.current_worker is not None:
            QMessageBox.warning(self, "Operation Running", "Cancel the current job before selecting new files.")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            "",
            "All Supported Files (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v "
            "*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.opus "
            "*.png *.jpg *.jpeg *.bmp *.webp *.tiff *.tif "
            "*.gif *.pdf *.docx *.txt *.md *.odt);;All Files (*)",
        )

        if not file_paths:
            return

        is_valid, result = validate_same_family(file_paths)
        if not is_valid:
            QMessageBox.warning(self, "Selection Error", result)
            return

        self.selected_files = file_paths
        self.selected_family = result
        self.update_file_area()
        self.rebuild_actions_panel()
        self.update_right_panel_state()
        self.update_start_button_state()

    def remove_file(self, file_path: str):
        if self.current_worker is not None:
            return

        self.selected_files = [path for path in self.selected_files if path != file_path]

        if not self.selected_files:
            self.selected_family = None
        else:
            is_valid, result = validate_same_family(self.selected_files)
            if is_valid:
                self.selected_family = result
            else:
                self.selected_files = []
                self.selected_family = None

        self.update_file_area()
        self.rebuild_actions_panel()
        self.update_right_panel_state()
        self.update_start_button_state()

    def update_file_area(self):
        self.files_list.clear()

        if not self.selected_files:
            self.file_stack.setCurrentWidget(self.empty_label)
            return

        self.file_stack.setCurrentWidget(self.files_list)

        for file_path in self.selected_files:
            item = QListWidgetItem()

            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(6, 4, 6, 4)
            row_layout.setSpacing(10)

            name_label = QLabel(Path(file_path).name)
            name_label.setStyleSheet(
                "font-size: 14px; color: rgba(255,255,255,0.90); background: transparent;"
            )
            name_label.setWordWrap(False)

            remove_button = QPushButton("×")
            remove_button.setFixedSize(26, 26)
            remove_button.setCursor(Qt.PointingHandCursor)
            remove_button.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.86);
                    border: none;
                    border-radius: 13px;
                    font-size: 15px;
                    font-weight: 700;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,0.16);
                }
                """
            )
            remove_button.clicked.connect(lambda checked=False, p=file_path: self.remove_file(p))

            row_layout.addWidget(name_label, 1)
            row_layout.addWidget(remove_button, 0, Qt.AlignRight)

            item.setSizeHint(QSize(0, 38))
            self.files_list.addItem(item)
            self.files_list.setItemWidget(item, row_widget)

    def update_right_panel_state(self):
        if self.selected_files:
            self.right_stack.setCurrentWidget(self.actions_page)
        else:
            self.right_stack.setCurrentWidget(self.info_page)

    def rebuild_actions_panel(self):
        self.action_cards.clear()

        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        has_family = self.selected_family is not None
        self.actions_placeholder.setVisible(not has_family)
        self.actions_scroll.setVisible(has_family)

        if not has_family:
            self.actions_summary_label.setText("Choose one or more actions to continue.")
            return

        if self.selected_family == "video":
            self._build_video_actions()
        elif self.selected_family == "audio":
            self._build_audio_actions()
        elif self.selected_family == "image":
            self._build_image_actions()
        elif self.selected_family == "gif":
            self._build_gif_actions()
        else:
            label = QLabel("No UI is wired yet for this file family.")
            label.setStyleSheet("color: rgba(255,255,255,0.56);")
            self.actions_layout.addWidget(label)

        self.actions_layout.addStretch(1)
        self.update_actions_summary()

    def _build_video_actions(self):
        self._create_action_card(
            key="video_convert_format",
            title="Convert Format",
            builder=self._build_video_convert_format_settings,
        )
        self._create_action_card(
            key="video_to_audio",
            title="Convert to Audio",
            builder=self._build_video_to_audio_settings,
        )
        self._create_action_card(
            key="video_to_gif",
            title="Convert to GIF",
            builder=self._build_video_to_gif_settings,
        )
        self._create_action_card(
            key="video_extract_frames",
            title="Extract Frames",
            builder=self._build_extract_frames_settings,
        )
        self._create_action_card(
            key="video_compress",
            title="Compress",
            enabled=False,
        )

    def _build_audio_actions(self):
        self._create_action_card(
            key="audio_convert_format",
            title="Convert Format",
            builder=self._build_audio_convert_format_settings,
        )
        self._create_action_card(
            key="audio_compress",
            title="Compress",
            enabled=False,
        )

    def _build_image_actions(self):
        self._create_action_card(
            key="image_convert_format",
            title="Convert Format",
            builder=self._build_image_convert_format_settings,
        )
        self._create_action_card(
            key="image_compress",
            title="Compress",
            builder=self._build_image_compress_settings,
        )
        self._create_action_card(
            key="image_to_pdf",
            title="Convert to PDF",
            enabled=False,
        )

    def _build_gif_actions(self):
        self._create_action_card(
            key="gif_to_video",
            title="Convert to Video",
            builder=self._build_gif_to_video_settings,
        )
        self._create_action_card(
            key="gif_extract_frames",
            title="Extract Frames",
            builder=self._build_extract_frames_settings,
        )
        self._create_action_card(
            key="gif_compress",
            title="Compress",
            enabled=False,
        )

    def _create_action_card(self, key: str, title: str, builder=None, enabled: bool = True, subtitle: str = ""):
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: rgba(255,255,255,0.03);
                border-radius: 16px;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()

        checkbox = QCheckBox(title)
        checkbox.setEnabled(enabled)
        top_row.addWidget(checkbox)

        badge = QLabel("" if enabled else "Coming soon")
        badge.setVisible(not enabled)
        badge.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px;")
        top_row.addStretch(1)
        top_row.addWidget(badge)

        layout.addLayout(top_row)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet("color: rgba(255,255,255,0.55); font-size: 12px;")
            layout.addWidget(subtitle_label)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(28, 2, 0, 0)
        content_layout.setSpacing(8)
        content_widget.setVisible(False)

        widgets: dict[str, Any] = {}
        if builder is not None:
            builder(content_layout, widgets)

        layout.addWidget(content_widget)

        if enabled:
            checkbox.toggled.connect(content_widget.setVisible)
            checkbox.toggled.connect(self.update_actions_summary)
            checkbox.toggled.connect(self.update_start_button_state)

        self.actions_layout.addWidget(card)
        self.action_cards[key] = {
            "checkbox": checkbox,
            "content": content_widget,
            "widgets": widgets,
            "enabled": enabled,
        }

    def _build_image_convert_format_settings(self, layout, widgets):
        label = QLabel("Output image format")
        combo = QComboBox()
        combo.addItems(["png", "jpg", "jpeg", "webp", "bmp", "tiff"])
        combo.setMinimumHeight(38)
        layout.addWidget(label)
        layout.addWidget(combo)
        widgets["format_combo"] = combo

    def _build_image_compress_settings(self, layout, widgets):
        label = QLabel("Compression strength")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(40)
        value_label = QLabel("Medium compression (40%)")
        value_label.setAlignment(Qt.AlignCenter)

        def update_label(value: int):
            if value <= 25:
                level = "Light"
            elif value <= 50:
                level = "Medium"
            elif value <= 75:
                level = "Strong"
            else:
                level = "Extreme"
            value_label.setText(f"{level} compression ({value}%)")

        slider.valueChanged.connect(update_label)
        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(value_label)
        widgets["strength_slider"] = slider

    def _build_video_convert_format_settings(self, layout, widgets):
        label = QLabel("Output video format")
        combo = QComboBox()
        combo.addItems(["mp4", "mkv", "mov", "avi"])
        combo.setMinimumHeight(38)
        layout.addWidget(label)
        layout.addWidget(combo)
        widgets["format_combo"] = combo

    def _build_audio_convert_format_settings(self, layout, widgets):
        label = QLabel("Output audio format")
        combo = QComboBox()
        combo.addItems(["mp3", "wav", "aac", "flac"])
        combo.setMinimumHeight(38)
        layout.addWidget(label)
        layout.addWidget(combo)
        widgets["format_combo"] = combo

    def _build_video_to_audio_settings(self, layout, widgets):
        label = QLabel("Output audio format")
        combo = QComboBox()
        combo.addItems(["mp3", "wav", "aac", "flac"])
        combo.setMinimumHeight(38)
        layout.addWidget(label)
        layout.addWidget(combo)
        widgets["format_combo"] = combo

    def _build_video_to_gif_settings(self, layout, widgets):
        fps_label = QLabel("GIF FPS")
        fps_combo = QComboBox()
        fps_combo.addItems(["5", "8", "10", "12", "15", "24", "30", "45", "60"])
        fps_combo.setCurrentText("10")
        fps_combo.setMinimumHeight(38)

        width_label = QLabel("GIF width")
        width_combo = QComboBox()
        width_combo.addItems(["Original", "320", "480", "640", "800", "1280"])
        width_combo.setCurrentText("Original")
        width_combo.setMinimumHeight(38)

        note = QLabel("Higher FPS and width create larger GIF files.")
        note.setWordWrap(True)
        note.setStyleSheet("color: rgba(255,255,255,0.55); font-size: 12px;")

        layout.addWidget(fps_label)
        layout.addWidget(fps_combo)
        layout.addWidget(width_label)
        layout.addWidget(width_combo)
        layout.addWidget(note)

        widgets["fps_combo"] = fps_combo
        widgets["width_combo"] = width_combo

    def _build_gif_to_video_settings(self, layout, widgets):
        label = QLabel("Output video format")
        combo = QComboBox()
        combo.addItems(["mp4", "mkv", "mov", "avi"])
        combo.setCurrentText("mp4")
        combo.setMinimumHeight(38)

        note = QLabel("GIF files do not contain audio, so the output video will be silent.")
        note.setWordWrap(True)
        note.setStyleSheet("color: rgba(255,255,255,0.55); font-size: 12px;")

        layout.addWidget(label)
        layout.addWidget(combo)
        layout.addWidget(note)
        widgets["format_combo"] = combo

    def _build_extract_frames_settings(self, layout, widgets):
        format_label = QLabel("Frame output format")
        format_combo = QComboBox()
        format_combo.addItems(["png", "jpg", "webp"])
        format_combo.setCurrentText("png")
        format_combo.setMinimumHeight(38)

        mode_label = QLabel("Frame extraction mode")
        mode_combo = QComboBox()
        mode_combo.addItems(["All Frames", "1 fps", "2 fps", "5 fps", "10 fps", "15 fps", "24 fps", "30 fps", "60 fps"])
        mode_combo.setCurrentText("All Frames")
        mode_combo.setMinimumHeight(38)

        layout.addWidget(format_label)
        layout.addWidget(format_combo)
        layout.addWidget(mode_label)
        layout.addWidget(mode_combo)

        widgets["format_combo"] = format_combo
        widgets["mode_combo"] = mode_combo

    def update_actions_summary(self):
        if self.selected_family is None:
            self.actions_summary_label.setText("Choose one or more actions to continue.")
            return

        tasks = self.build_task_queue(preview_only=True)

        if not tasks:
            self.actions_summary_label.setText("Choose one or more actions to enable Start Conversion.")
            return

        if self.selected_family == "image":
            convert_checked = self._is_checked("image_convert_format")
            compress_checked = self._is_checked("image_compress")

            if convert_checked and compress_checked:
                self.actions_summary_label.setText("1 processed image output per selected file will be created.")
            elif convert_checked or compress_checked:
                self.actions_summary_label.setText("1 image output per selected file will be created.")
            else:
                self.actions_summary_label.setText(
                    f"{len(tasks)} output{'s' if len(tasks) > 1 else ''} will be created."
                )
            return

        count = len(tasks)
        self.actions_summary_label.setText(
            f"{count} separate output{'s' if count > 1 else ''} will be created."
        )

    def update_start_button_state(self):
        enabled = bool(self.selected_files) and bool(self.build_task_queue(preview_only=True))
        self.start_button.setEnabled(enabled)

    def _is_checked(self, key: str) -> bool:
        card = self.action_cards.get(key)
        return bool(card and card["enabled"] and card["checkbox"].isChecked())

    def build_task_queue(self, preview_only: bool = False) -> list[dict[str, Any]]:
        if not self.selected_files or not self.selected_family:
            return []

        queue: list[dict[str, Any]] = []

        if self.selected_family == "image":
            convert_checked = self._is_checked("image_convert_format")
            compress_checked = self._is_checked("image_compress")

            if convert_checked and compress_checked:
                format_combo = self.action_cards["image_convert_format"]["widgets"]["format_combo"]
                strength_slider = self.action_cards["image_compress"]["widgets"]["strength_slider"]
                queue.append(
                    {
                        "type": "image_pipeline",
                        "title": "Convert Format + Compress",
                        "output_format": format_combo.currentText(),
                        "strength": strength_slider.value(),
                    }
                )
            elif convert_checked:
                format_combo = self.action_cards["image_convert_format"]["widgets"]["format_combo"]
                queue.append(
                    {
                        "type": "image_convert",
                        "title": "Convert Format",
                        "output_format": format_combo.currentText(),
                    }
                )
            elif compress_checked:
                strength_slider = self.action_cards["image_compress"]["widgets"]["strength_slider"]
                queue.append(
                    {
                        "type": "image_compress",
                        "title": "Compress Images",
                        "strength": strength_slider.value(),
                    }
                )

            return queue

        if self.selected_family == "audio":
            if self._is_checked("audio_convert_format"):
                format_combo = self.action_cards["audio_convert_format"]["widgets"]["format_combo"]
                queue.append(
                    {
                        "type": "media_convert",
                        "title": "Convert Format",
                        "media_family": "audio",
                        "output_format": format_combo.currentText(),
                    }
                )
            return queue

        if self.selected_family == "video":
            if self._is_checked("video_convert_format"):
                format_combo = self.action_cards["video_convert_format"]["widgets"]["format_combo"]
                queue.append(
                    {
                        "type": "media_convert",
                        "title": "Convert Format",
                        "media_family": "video",
                        "output_format": format_combo.currentText(),
                    }
                )

            if self._is_checked("video_to_audio"):
                format_combo = self.action_cards["video_to_audio"]["widgets"]["format_combo"]
                queue.append(
                    {
                        "type": "video_to_audio",
                        "title": "Convert to Audio",
                        "output_format": format_combo.currentText(),
                    }
                )

            if self._is_checked("video_to_gif"):
                fps_combo = self.action_cards["video_to_gif"]["widgets"]["fps_combo"]
                width_combo = self.action_cards["video_to_gif"]["widgets"]["width_combo"]
                width_text = width_combo.currentText()
                queue.append(
                    {
                        "type": "video_to_gif",
                        "title": "Convert to GIF",
                        "fps": int(fps_combo.currentText()),
                        "width": None if width_text == "Original" else int(width_text),
                    }
                )

            if self._is_checked("video_extract_frames"):
                queue.append(self._build_extract_frames_task("video_extract_frames"))

            return queue

        if self.selected_family == "gif":
            if self._is_checked("gif_to_video"):
                format_combo = self.action_cards["gif_to_video"]["widgets"]["format_combo"]
                queue.append(
                    {
                        "type": "gif_to_video",
                        "title": "Convert to Video",
                        "output_format": format_combo.currentText(),
                    }
                )

            if self._is_checked("gif_extract_frames"):
                queue.append(self._build_extract_frames_task("gif_extract_frames"))

            return queue

        return queue

    def _build_extract_frames_task(self, key: str) -> dict[str, Any]:
        widgets = self.action_cards[key]["widgets"]
        mode_text = widgets["mode_combo"].currentText()
        sample_fps = None if mode_text == "All Frames" else int(mode_text.split()[0])

        return {
            "type": "extract_frames",
            "title": "Extract Frames",
            "image_format": widgets["format_combo"].currentText(),
            "sample_fps": sample_fps,
        }

    def start_conversion(self):
        if self.current_worker is not None:
            return

        self.task_queue = self.build_task_queue()
        if not self.task_queue:
            QMessageBox.warning(self, "No Actions", "Choose at least one action before starting.")
            return

        self.output_root_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder", "")
        if not self.output_root_dir:
            return

        self.current_task_index = -1
        self.progress_dialog = ConversionProgressDialog(self)
        self.progress_dialog.cancel_requested.connect(self.cancel_current_operation)
        self.progress_dialog.show()

        self.add_files_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self._start_next_task()

    def _start_next_task(self):
        self.current_task_index += 1

        if self.current_task_index >= len(self.task_queue):
            self._finish_all_tasks()
            return

        self.current_task = self.task_queue[self.current_task_index]
        task = self.current_task
        total = len(self.task_queue)
        step_number = self.current_task_index + 1

        if self.progress_dialog is not None:
            self.progress_dialog.set_step(step_number, total, task["title"])
            self.progress_dialog.set_status(f"Preparing {task['title']}...")

        if not self.output_root_dir:
            self._cancel_remaining_tasks("No output folder selected.")
            return

        self._launch_task(task, self.output_root_dir)

    def _launch_task(self, task: dict[str, Any], output_dir: str):
        task_type = task["type"]

        if task_type == "image_pipeline":
            self.pipeline_mode = "image_pipeline"
            self.pipeline_temp_dir = tempfile.mkdtemp(prefix="cw_img_pipeline_")
            self.pipeline_final_dir = output_dir
            self.pipeline_output_format = task["output_format"]
            self.pipeline_strength = task["strength"]

            worker = ImageConvertWorker(
                input_files=self.selected_files,
                output_dir=self.pipeline_temp_dir,
                output_format=self.pipeline_output_format,
            )
            self._launch_worker(worker, "Stage 1/2: Converting images")
            return

        if task_type == "image_convert":
            worker = ImageConvertWorker(
                input_files=self.selected_files,
                output_dir=output_dir,
                output_format=task["output_format"],
            )
            self._launch_worker(worker, "Converting images")
            return

        if task_type == "image_compress":
            worker = ImageCompressWorker(
                input_files=self.selected_files,
                output_dir=output_dir,
                strength=task["strength"],
            )
            self._launch_worker(worker, "Compressing images")
            return

        if task_type == "media_convert":
            worker = MediaConvertWorker(
                input_files=self.selected_files,
                output_dir=output_dir,
                media_family=task["media_family"],
                output_format=task["output_format"],
            )
            self._launch_worker(worker, "Converting media")
            return

        if task_type == "video_to_audio":
            worker = VideoToAudioWorker(
                input_files=self.selected_files,
                output_dir=output_dir,
                output_format=task["output_format"],
            )
            self._launch_worker(worker, "Converting video to audio")
            return

        if task_type == "video_to_gif":
            worker = VideoToGifWorker(
                input_files=self.selected_files,
                output_dir=output_dir,
                fps=task["fps"],
                width=task["width"],
            )
            self._launch_worker(worker, "Converting video to GIF")
            return

        if task_type == "gif_to_video":
            worker = GifToVideoWorker(
                input_files=self.selected_files,
                output_dir=output_dir,
                output_format=task["output_format"],
            )
            self._launch_worker(worker, "Converting GIF to video")
            return

        if task_type == "extract_frames":
            worker = ExtractFramesWorker(
                input_files=self.selected_files,
                output_dir=output_dir,
                image_format=task["image_format"],
                sample_fps=task["sample_fps"],
            )
            self._launch_worker(worker, "Extracting frames")
            return

        QMessageBox.warning(self, "Unsupported Action", f"Task type not handled: {task_type}")
        self._start_next_task()

    def _launch_worker(self, worker, initial_status: str):
        self.current_worker = worker
        self.current_thread = QThread(self)

        worker.moveToThread(self.current_thread)
        self.current_thread.started.connect(worker.run)
        worker.progress.connect(self._on_worker_progress)
        worker.finished.connect(self._on_worker_finished)
        worker.finished.connect(self.current_thread.quit)
        worker.finished.connect(worker.deleteLater)

        self.current_thread.finished.connect(self.current_thread.deleteLater)
        self.current_thread.finished.connect(self._after_worker_cleanup)

        if self.progress_dialog is not None:
            self.progress_dialog.set_status(initial_status)

        self.current_thread.start()

    def _on_worker_progress(self, message: str, percent: int):
        if self.progress_dialog is not None:
            self.progress_dialog.update_progress(message, percent)

    def _on_worker_finished(self, status: str, message: str):
        self.pending_status = status
        self.pending_message = message

        if self.progress_dialog is not None:
            if status == "success":
                self.progress_dialog.set_finished()
            self.progress_dialog.set_status("Finishing up...")

    def _after_worker_cleanup(self):
        task = self.current_task
        status = self.pending_status
        message = self.pending_message

        self.current_worker = None
        self.current_thread = None
        self.pending_status = None
        self.pending_message = ""

        if task is None:
            return

        if self.pipeline_mode == "image_pipeline":
            self._continue_or_finish_image_pipeline(task, status, message)
            return

        self._handle_task_completion(task, status, message)

    def _continue_or_finish_image_pipeline(self, task: dict[str, Any], status: str | None, message: str):
        if self.pipeline_temp_dir is None or self.pipeline_final_dir is None:
            self._handle_task_completion(task, status, message)
            return

        temp_dir = Path(self.pipeline_temp_dir)
        converted_paths = [
            str(temp_dir / f"{Path(file_path).stem}.{self.pipeline_output_format}")
            for file_path in self.selected_files
            if (temp_dir / f"{Path(file_path).stem}.{self.pipeline_output_format}").exists()
        ]

        if status in {"success", "partial"} and converted_paths:
            worker = ImageCompressWorker(
                input_files=converted_paths,
                output_dir=self.pipeline_final_dir,
                strength=self.pipeline_strength or 40,
            )
            self.pipeline_mode = None
            self._launch_worker(worker, "Stage 2/2: Compressing converted images")
            return

        self._cleanup_pipeline_temp_dir()
        self.pipeline_mode = None
        self._handle_task_completion(task, status, message)

    def _cleanup_pipeline_temp_dir(self):
        if self.pipeline_temp_dir:
            shutil.rmtree(self.pipeline_temp_dir, ignore_errors=True)
        self.pipeline_temp_dir = None
        self.pipeline_final_dir = None
        self.pipeline_output_format = None
        self.pipeline_strength = None

    def _handle_task_completion(self, task: dict[str, Any], status: str | None, message: str):
        if task["type"] == "image_pipeline":
            self._cleanup_pipeline_temp_dir()

        if status == "cancelled":
            self._cancel_remaining_tasks(message or "Operation cancelled.")
            return

        if status == "error":
            self._cancel_remaining_tasks(message or "Operation failed.")
            return

        self._start_next_task()

    def cancel_current_operation(self):
        if self.progress_dialog is not None:
            self.progress_dialog.set_status("Cancelling now...")

        if self.current_worker is not None and hasattr(self.current_worker, "cancel"):
            self.current_worker.cancel()

    def _cancel_remaining_tasks(self, message: str):
        self.task_queue = []
        self.current_task = None
        self.current_task_index = -1
        self._cleanup_pipeline_temp_dir()

        if self.progress_dialog is not None:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.add_files_button.setEnabled(True)
        self.output_root_dir = None
        self.update_start_button_state()

        QMessageBox.warning(self, "Conversion Cancelled", message)

    def _finish_all_tasks(self):
        if self.progress_dialog is not None:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.current_task = None
        self.current_task_index = -1
        self._cleanup_pipeline_temp_dir()

        self.add_files_button.setEnabled(True)
        self.output_root_dir = None
        self.update_start_button_state()

        QMessageBox.information(self, "Done", "Selected actions finished successfully.")