from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar


class ConversionProgressDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing")
        self.setModal(True)
        self.resize(460, 220)

        self.layout = QVBoxLayout(self)

        self.title_label = QLabel("Processing Conversion")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.step_label = QLabel("Step 1 of 1")
        self.step_label.setStyleSheet("font-size: 14px;")

        self.status_label = QLabel("Preparing...")
        self.status_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(16)

        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignCenter)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.clicked.connect(self._handle_cancel_clicked)

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.step_label)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.percent_label)
        self.layout.addWidget(self.cancel_button)

    def _handle_cancel_clicked(self):
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.percent_label.setText("Stopping...")
        self.cancel_requested.emit()

    def set_step(self, current_step: int, total_steps: int, title: str):
        self.step_label.setText(f"Step {current_step} of {total_steps} — {title}")
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")

    def update_progress(self, message: str, percent: int):
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")

    def set_status(self, message: str):
        self.status_label.setText(message)

    def set_finished(self):
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")