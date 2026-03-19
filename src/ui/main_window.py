from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QListWidget,
    QFrame,
    QSlider,
    QHBoxLayout,
    QComboBox,
    QProgressBar,
)

from dependency_manager.checker import get_dependency_status
from core.file_types import validate_same_family, get_operations_for_family
from workers.image_compress_worker import ImageCompressWorker
from workers.video_to_audio_worker import VideoToAudioWorker
from workers.video_to_gif_worker import VideoToGifWorker


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Convert Whatever")
        self.resize(760, 620)

        self.selected_files: list[str] = []
        self.selected_family: str | None = None
        self.current_operation: str | None = None
        self.operation_running: bool = False

        self.worker_thread: QThread | None = None
        self.image_worker: ImageCompressWorker | None = None
        self.video_audio_worker: VideoToAudioWorker | None = None
        self.video_gif_worker: VideoToGifWorker | None = None

        self.running_info_label: QLabel | None = None
        self.progress_bar: QProgressBar | None = None
        self.progress_percent_label: QLabel | None = None
        self.cancel_button: QPushButton | None = None

        self.pending_finish_status: str | None = None
        self.pending_finish_message: str = ""
        self.pending_finish_title: str = "Operation Complete"

        self.main_layout = QVBoxLayout(self)

        self.title_label = QLabel("Convert Whatever")
        self.title_label.setStyleSheet("font-size: 26px; font-weight: bold;")

        self.status_label = QLabel("Checking dependencies...")

        self.add_files_button = QPushButton("Add Files")
        self.add_files_button.setMinimumHeight(48)
        self.add_files_button.clicked.connect(self.select_files)

        self.family_label = QLabel("Detected type: None")
        self.family_label.setStyleSheet("font-size: 15px;")

        self.files_list = QListWidget()
        self.files_list.setMinimumHeight(180)

        self.operations_title = QLabel("Available Operations")
        self.operations_title.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.operations_container = QFrame()
        self.operations_layout = QVBoxLayout(self.operations_container)

        self.config_title = QLabel("Operation Panel")
        self.config_title.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.config_container = QFrame()
        self.config_layout = QVBoxLayout(self.config_container)

        self.main_layout.addWidget(self.title_label)
        self.main_layout.addWidget(self.status_label)
        self.main_layout.addWidget(self.add_files_button)
        self.main_layout.addWidget(self.family_label)
        self.main_layout.addWidget(self.files_list)
        self.main_layout.addWidget(self.operations_title)
        self.main_layout.addWidget(self.operations_container)
        self.main_layout.addWidget(self.config_title)
        self.main_layout.addWidget(self.config_container)

        self.refresh_dependencies()
        self.show_empty_operations_message()
        self.show_idle_config_panel()

    def refresh_dependencies(self):
        status = get_dependency_status()
        ffmpeg_ok = status["ffmpeg"]
        ffprobe_ok = status["ffprobe"]

        if ffmpeg_ok and ffprobe_ok:
            self.status_label.setText("Dependencies OK: ffmpeg and ffprobe found.")
        else:
            missing = []
            if not ffmpeg_ok:
                missing.append("ffmpeg")
            if not ffprobe_ok:
                missing.append("ffprobe")
            self.status_label.setText(f"Missing dependencies: {', '.join(missing)}")

    def select_files(self):
        if self.operation_running:
            QMessageBox.warning(
                self,
                "Operation Running",
                "Cancel the current operation before selecting new files.",
            )
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
            self.clear_selection()
            return

        self.selected_files = file_paths
        self.selected_family = result
        self.current_operation = None

        self.update_files_list()
        self.update_family_label()
        self.show_operations_for_current_family()
        self.show_idle_config_panel()

    def clear_selection(self):
        self.selected_files = []
        self.selected_family = None
        self.current_operation = None
        self.files_list.clear()
        self.family_label.setText("Detected type: None")
        self.clear_operations()
        self.show_empty_operations_message()
        self.show_idle_config_panel()

    def update_files_list(self):
        self.files_list.clear()
        for file_path in self.selected_files:
            self.files_list.addItem(file_path)

    def update_family_label(self):
        if self.selected_family:
            self.family_label.setText(
                f"Detected type: {self.selected_family.capitalize()}"
            )
        else:
            self.family_label.setText("Detected type: None")

    def clear_operations(self):
        while self.operations_layout.count():
            item = self.operations_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def clear_config_panel(self):
        self.running_info_label = None
        self.progress_bar = None
        self.progress_percent_label = None
        self.cancel_button = None

        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            layout = item.layout()
            if layout is not None:
                self._clear_nested_layout(layout)

    def _clear_nested_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_nested_layout(child_layout)

    def show_empty_operations_message(self):
        self.clear_operations()
        info_label = QLabel("No file selected yet. Add files to see allowed operations.")
        self.operations_layout.addWidget(info_label)

    def show_operations_for_current_family(self):
        self.clear_operations()

        if not self.selected_family:
            self.show_empty_operations_message()
            return

        operations = get_operations_for_family(self.selected_family)

        if not operations:
            info_label = QLabel("No operations available for this file type yet.")
            self.operations_layout.addWidget(info_label)
            return

        for operation_name in operations:
            button = QPushButton(operation_name)
            button.setMinimumHeight(40)
            button.setEnabled(not self.operation_running)
            button.clicked.connect(
                lambda checked=False, op=operation_name: self.handle_operation_click(op)
            )
            self.operations_layout.addWidget(button)

    def handle_operation_click(self, operation_name: str):
        if not self.selected_files or not self.selected_family:
            QMessageBox.warning(self, "No files", "Please add files first.")
            return

        self.current_operation = operation_name

        if operation_name == "Compress":
            self.show_compress_panel()
        elif operation_name == "Convert to Audio":
            self.show_video_to_audio_panel()
        elif operation_name == "Convert to GIF":
            self.show_video_to_gif_panel()
        else:
            self.show_standard_operation_panel(operation_name)

    def show_idle_config_panel(self):
        self.clear_config_panel()
        label = QLabel("Choose an operation to configure it here.")
        self.config_layout.addWidget(label)

    def show_standard_operation_panel(self, operation_name: str):
        self.clear_config_panel()

        title = QLabel(f"Selected Operation: {operation_name}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")

        info = QLabel(
            f"Family: {self.selected_family}\n"
            f"Files selected: {len(self.selected_files)}\n\n"
            f"This operation will be connected to the real backend next."
        )
        info.setWordWrap(True)

        button_row = QHBoxLayout()

        start_button = QPushButton("Start")
        start_button.setMinimumHeight(40)
        start_button.clicked.connect(self.start_operation)

        back_button = QPushButton("Back")
        back_button.setMinimumHeight(40)
        back_button.clicked.connect(self.show_idle_config_panel)

        button_row.addWidget(start_button)
        button_row.addWidget(back_button)

        self.config_layout.addWidget(title)
        self.config_layout.addWidget(info)
        self.config_layout.addLayout(button_row)

    def show_compress_panel(self):
        self.clear_config_panel()

        title = QLabel("Selected Operation: Compress")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")

        info = QLabel(
            f"Family: {self.selected_family}\n"
            f"Files selected: {len(self.selected_files)}\n\n"
            f"Choose compression strength before starting."
        )
        info.setWordWrap(True)

        slider_title = QLabel("Compression Level")
        slider_title.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.compression_slider = QSlider(Qt.Horizontal)
        self.compression_slider.setRange(0, 100)
        self.compression_slider.setValue(40)
        self.compression_slider.valueChanged.connect(self.update_compression_label)

        self.compression_value_label = QLabel()
        self.compression_value_label.setAlignment(Qt.AlignCenter)

        self.update_compression_label(self.compression_slider.value())

        button_row = QHBoxLayout()

        start_button = QPushButton("Start Compression")
        start_button.setMinimumHeight(40)
        start_button.clicked.connect(self.start_operation)

        back_button = QPushButton("Back")
        back_button.setMinimumHeight(40)
        back_button.clicked.connect(self.show_idle_config_panel)

        button_row.addWidget(start_button)
        button_row.addWidget(back_button)

        self.config_layout.addWidget(title)
        self.config_layout.addWidget(info)
        self.config_layout.addWidget(slider_title)
        self.config_layout.addWidget(self.compression_slider)
        self.config_layout.addWidget(self.compression_value_label)
        self.config_layout.addLayout(button_row)

    def show_video_to_audio_panel(self):
        self.clear_config_panel()

        title = QLabel("Selected Operation: Convert to Audio")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")

        info = QLabel(
            f"Family: {self.selected_family}\n"
            f"Files selected: {len(self.selected_files)}\n\n"
            f"Choose the output audio format before starting."
        )
        info.setWordWrap(True)

        format_title = QLabel("Output Audio Format")
        format_title.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["mp3", "wav", "aac", "flac"])
        self.audio_format_combo.setMinimumHeight(40)

        button_row = QHBoxLayout()

        start_button = QPushButton("Start Conversion")
        start_button.setMinimumHeight(40)
        start_button.clicked.connect(self.start_operation)

        back_button = QPushButton("Back")
        back_button.setMinimumHeight(40)
        back_button.clicked.connect(self.show_idle_config_panel)

        button_row.addWidget(start_button)
        button_row.addWidget(back_button)

        self.config_layout.addWidget(title)
        self.config_layout.addWidget(info)
        self.config_layout.addWidget(format_title)
        self.config_layout.addWidget(self.audio_format_combo)
        self.config_layout.addLayout(button_row)

    def show_video_to_gif_panel(self):
        self.clear_config_panel()

        title = QLabel("Selected Operation: Convert to GIF")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")

        info = QLabel(
            f"Family: {self.selected_family}\n"
            f"Files selected: {len(self.selected_files)}\n\n"
            f"Choose GIF quality settings before starting."
        )
        info.setWordWrap(True)

        fps_title = QLabel("GIF FPS")
        fps_title.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.gif_fps_combo = QComboBox()
        self.gif_fps_combo.addItems(["5", "8", "10", "12", "15", "24", "30", "45", "60"])
        self.gif_fps_combo.setCurrentText("10")
        self.gif_fps_combo.setMinimumHeight(40)

        width_title = QLabel("GIF Width")
        width_title.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.gif_width_combo = QComboBox()
        self.gif_width_combo.addItems(["Original", "320", "480", "640", "800", "1280"])
        self.gif_width_combo.setCurrentText("Original")
        self.gif_width_combo.setMinimumHeight(40)

        note = QLabel(
            "Higher FPS and width make larger GIF files. "
            "Long videos can create very large outputs."
        )
        note.setWordWrap(True)

        button_row = QHBoxLayout()

        start_button = QPushButton("Start GIF Conversion")
        start_button.setMinimumHeight(40)
        start_button.clicked.connect(self.start_operation)

        back_button = QPushButton("Back")
        back_button.setMinimumHeight(40)
        back_button.clicked.connect(self.show_idle_config_panel)

        button_row.addWidget(start_button)
        button_row.addWidget(back_button)

        self.config_layout.addWidget(title)
        self.config_layout.addWidget(info)
        self.config_layout.addWidget(fps_title)
        self.config_layout.addWidget(self.gif_fps_combo)
        self.config_layout.addWidget(width_title)
        self.config_layout.addWidget(self.gif_width_combo)
        self.config_layout.addWidget(note)
        self.config_layout.addLayout(button_row)

    def update_compression_label(self, value: int):
        if value <= 25:
            level = "Light"
        elif value <= 50:
            level = "Medium"
        elif value <= 75:
            level = "Strong"
        else:
            level = "Extreme"

        self.compression_value_label.setText(f"{level} compression ({value}%)")

    def start_operation(self):
        if not self.current_operation:
            QMessageBox.warning(self, "No Operation", "Please select an operation first.")
            return

        if self.current_operation == "Compress" and self.selected_family == "image":
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder", "")
            if not output_dir:
                return
            self.start_image_compression(output_dir)
            return

        if self.current_operation == "Convert to Audio" and self.selected_family == "video":
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder", "")
            if not output_dir:
                return
            self.start_video_to_audio_conversion(output_dir)
            return

        if self.current_operation == "Convert to GIF" and self.selected_family == "video":
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder", "")
            if not output_dir:
                return
            self.start_video_to_gif_conversion(output_dir)
            return

        self.operation_running = True
        self.add_files_button.setEnabled(False)
        self.show_operations_for_current_family()
        self.show_running_panel("This is a UI simulation for now.")

    def start_image_compression(self, output_dir: str):
        self.operation_running = True
        self.add_files_button.setEnabled(False)
        self.show_operations_for_current_family()

        self.worker_thread = QThread(self)
        self.image_worker = ImageCompressWorker(
            input_files=self.selected_files,
            output_dir=output_dir,
            strength=self.compression_slider.value(),
        )
        self.image_worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.image_worker.run)
        self.image_worker.progress.connect(self.on_worker_progress)
        self.image_worker.finished.connect(self.on_image_compression_finished)
        self.image_worker.finished.connect(self.worker_thread.quit)
        self.image_worker.finished.connect(self.image_worker.deleteLater)

        self.worker_thread.finished.connect(self.cleanup_after_worker)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.show_running_panel("Starting image compression...")
        self.worker_thread.start()

    def start_video_to_audio_conversion(self, output_dir: str):
        self.operation_running = True
        self.add_files_button.setEnabled(False)
        self.show_operations_for_current_family()

        selected_format = self.audio_format_combo.currentText()

        self.worker_thread = QThread(self)
        self.video_audio_worker = VideoToAudioWorker(
            input_files=self.selected_files,
            output_dir=output_dir,
            output_format=selected_format,
        )
        self.video_audio_worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.video_audio_worker.run)
        self.video_audio_worker.progress.connect(self.on_worker_progress)
        self.video_audio_worker.finished.connect(self.on_video_audio_finished)
        self.video_audio_worker.finished.connect(self.worker_thread.quit)
        self.video_audio_worker.finished.connect(self.video_audio_worker.deleteLater)

        self.worker_thread.finished.connect(self.cleanup_after_worker)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.show_running_panel("Starting video to audio conversion...")
        self.worker_thread.start()

    def start_video_to_gif_conversion(self, output_dir: str):
        self.operation_running = True
        self.add_files_button.setEnabled(False)
        self.show_operations_for_current_family()

        fps = int(self.gif_fps_combo.currentText())
        width_text = self.gif_width_combo.currentText()
        width = None if width_text == "Original" else int(width_text)

        self.worker_thread = QThread(self)
        self.video_gif_worker = VideoToGifWorker(
            input_files=self.selected_files,
            output_dir=output_dir,
            fps=fps,
            width=width,
        )
        self.video_gif_worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.video_gif_worker.run)
        self.video_gif_worker.progress.connect(self.on_worker_progress)
        self.video_gif_worker.finished.connect(self.on_video_gif_finished)
        self.video_gif_worker.finished.connect(self.worker_thread.quit)
        self.video_gif_worker.finished.connect(self.video_gif_worker.deleteLater)

        self.worker_thread.finished.connect(self.cleanup_after_worker)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.show_running_panel("Starting video to GIF conversion...")
        self.worker_thread.start()

    def show_running_panel(self, status_text: str):
        self.clear_config_panel()

        title = QLabel("Operation Running")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")

        details = (
            f"Operation: {self.current_operation}\n"
            f"Family: {self.selected_family}\n"
            f"Files selected: {len(self.selected_files)}\n"
        )

        if self.current_operation == "Compress" and hasattr(self, "compression_slider"):
            details += f"Compression level: {self.compression_slider.value()}%\n"

        if self.current_operation == "Convert to Audio" and hasattr(self, "audio_format_combo"):
            details += f"Output format: {self.audio_format_combo.currentText().upper()}\n"

        if self.current_operation == "Convert to GIF":
            if hasattr(self, "gif_fps_combo"):
                details += f"GIF FPS: {self.gif_fps_combo.currentText()}\n"
            if hasattr(self, "gif_width_combo"):
                details += f"GIF width: {self.gif_width_combo.currentText()}\n"

        info = QLabel(details)
        info.setWordWrap(True)

        self.running_info_label = QLabel(status_text)
        self.running_info_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(14)

        self.progress_percent_label = QLabel("0%")
        self.progress_percent_label.setAlignment(Qt.AlignCenter)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.clicked.connect(self.cancel_operation)

        self.config_layout.addWidget(title)
        self.config_layout.addWidget(info)
        self.config_layout.addWidget(self.running_info_label)
        self.config_layout.addWidget(self.progress_bar)
        self.config_layout.addWidget(self.progress_percent_label)
        self.config_layout.addWidget(self.cancel_button)

    def on_worker_progress(self, message: str, percent: int):
        if self.running_info_label is not None:
            self.running_info_label.setText(message)

        if self.progress_bar is not None:
            self.progress_bar.setValue(percent)

        if self.progress_percent_label is not None:
            self.progress_percent_label.setText(f"{percent}%")

    def on_image_compression_finished(self, status: str, message: str):
        self.pending_finish_status = status
        self.pending_finish_message = message
        self.pending_finish_title = "Compression Complete"

        if self.progress_bar is not None:
            self.progress_bar.setValue(100)

        if self.progress_percent_label is not None:
            self.progress_percent_label.setText("100%")

        if self.running_info_label is not None:
            self.running_info_label.setText("Finishing up...")

    def on_video_audio_finished(self, status: str, message: str):
        self.pending_finish_status = status
        self.pending_finish_message = message
        self.pending_finish_title = "Conversion Complete"

        if self.progress_bar is not None:
            self.progress_bar.setValue(100)

        if self.progress_percent_label is not None:
            self.progress_percent_label.setText("100%")

        if self.running_info_label is not None:
            self.running_info_label.setText("Finishing up...")

    def on_video_gif_finished(self, status: str, message: str):
        self.pending_finish_status = status
        self.pending_finish_message = message
        self.pending_finish_title = "GIF Conversion Complete"

        if self.progress_bar is not None:
            self.progress_bar.setValue(100)

        if self.progress_percent_label is not None:
            self.progress_percent_label.setText("100%")

        if self.running_info_label is not None:
            self.running_info_label.setText("Finishing up...")

    def cleanup_after_worker(self):
        self.operation_running = False
        self.current_operation = None
        self.add_files_button.setEnabled(True)
        self.show_operations_for_current_family()
        self.show_idle_config_panel()

        self.image_worker = None
        self.video_audio_worker = None
        self.video_gif_worker = None
        self.worker_thread = None

        status = self.pending_finish_status
        message = self.pending_finish_message
        title = self.pending_finish_title

        self.pending_finish_status = None
        self.pending_finish_message = ""
        self.pending_finish_title = "Operation Complete"

        if status == "success":
            QMessageBox.information(self, title, message)
        elif status == "partial":
            QMessageBox.warning(self, f"{title} (Partial)", message)
        elif status == "cancelled":
            QMessageBox.warning(self, f"{title} (Cancelled)", message)
        elif status == "error":
            QMessageBox.critical(self, f"{title} (Failed)", message)

    def cancel_operation(self):
        if self.cancel_button is not None:
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("Cancelling...")

        if self.progress_percent_label is not None:
            self.progress_percent_label.setText("Stopping...")

        if self.operation_running and self.image_worker is not None:
            self.image_worker.cancel()
            if self.running_info_label is not None:
                self.running_info_label.setText("Cancelling now...")
            return

        if self.operation_running and self.video_audio_worker is not None:
            self.video_audio_worker.cancel()
            if self.running_info_label is not None:
                self.running_info_label.setText("Cancelling now... stopping FFmpeg.")
            return

        if self.operation_running and self.video_gif_worker is not None:
            self.video_gif_worker.cancel()
            if self.running_info_label is not None:
                self.running_info_label.setText("Cancelling now... stopping FFmpeg.")
            return

        self.operation_running = False
        self.current_operation = None
        self.add_files_button.setEnabled(True)
        self.show_operations_for_current_family()
        self.show_idle_config_panel()