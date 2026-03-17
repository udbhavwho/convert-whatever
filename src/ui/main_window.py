from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
)

from dependency_manager.checker import get_dependency_status
from converters.ffmpeg_converter import FFmpegConverter


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Convert Whatever")
        self.resize(700, 400)

        self.input_file = None

        self.layout = QVBoxLayout(self)

        self.title = QLabel("Convert Whatever")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold;")

        self.status_label = QLabel("Checking dependencies...")
        self.file_label = QLabel("No file selected.")

        self.select_button = QPushButton("Select Video File")
        self.select_button.clicked.connect(self.select_file)

        self.convert_button = QPushButton("Convert Video to MP3")
        self.convert_button.clicked.connect(self.convert_file)
        self.convert_button.setEnabled(False)

        self.layout.addWidget(self.title)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.file_label)
        self.layout.addWidget(self.select_button)
        self.layout.addWidget(self.convert_button)

        self.refresh_dependencies()

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

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.mkv *.mov *.avi *.webm);;All Files (*)",
        )

        if file_path:
            self.input_file = file_path
            self.file_label.setText(f"Selected: {file_path}")
            self.convert_button.setEnabled(True)

    def convert_file(self):
        if not self.input_file:
            QMessageBox.warning(self, "No file", "Please select a file first.")
            return

        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Audio File",
            "",
            "MP3 Files (*.mp3);;WAV Files (*.wav);;All Files (*)",
        )

        if not output_file:
            return

        ok, message = FFmpegConverter.video_to_audio(self.input_file, output_file)

        if ok:
            QMessageBox.information(self, "Success", "Conversion completed.")
        else:
            QMessageBox.critical(self, "Error", message)