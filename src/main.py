import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from ui.main_window import MainWindow


def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(14, 17, 23))
    palette.setColor(QPalette.WindowText, QColor(240, 244, 255))
    palette.setColor(QPalette.Base, QColor(18, 22, 30))
    palette.setColor(QPalette.AlternateBase, QColor(24, 29, 39))
    palette.setColor(QPalette.ToolTipBase, QColor(28, 34, 45))
    palette.setColor(QPalette.ToolTipText, QColor(245, 248, 255))
    palette.setColor(QPalette.Text, QColor(236, 240, 248))
    palette.setColor(QPalette.Button, QColor(245, 245, 245))
    palette.setColor(QPalette.ButtonText, QColor(18, 22, 30))
    palette.setColor(QPalette.BrightText, QColor(255, 120, 120))
    palette.setColor(QPalette.Link, QColor(180, 200, 255))
    palette.setColor(QPalette.Highlight, QColor(90, 90, 90))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    app.setStyleSheet("""
        QWidget {
            background-color: #0e1117;
            color: #f2f6ff;
            font-size: 13px;
            font-family: "Segoe UI", "Inter", "Ubuntu", sans-serif;
        }

        QLabel {
            color: #f2f6ff;
            background: transparent;
        }

        QPushButton {
            background-color: #f5f5f5;
            color: #11161f;
            border: none;
            border-radius: 12px;
            padding: 12px 16px;
            font-weight: 700;
        }

        QPushButton:hover {
            background-color: #ffffff;
        }

        QPushButton:pressed {
            background-color: #dcdcdc;
        }

        QPushButton:disabled {
            background-color: #2a3140;
            color: #8892a6;
        }

        QListWidget {
            background-color: #131924;
            color: #eef3ff;
            border: 1px solid #232b39;
            border-radius: 14px;
            padding: 8px;
            outline: none;
        }

        QListWidget::item {
            background: transparent;
            padding: 8px 10px;
            margin: 3px 0;
            border-radius: 8px;
        }

        QListWidget::item:selected {
            background-color: #273247;
            color: #ffffff;
        }

        QFrame {
            background-color: #151b26;
            border: 1px solid #232b39;
            border-radius: 16px;
        }

        QSlider {
            background: transparent;
        }

        QSlider::groove:horizontal {
            height: 8px;
            background: #242d3c;
            border-radius: 4px;
        }

        QSlider::sub-page:horizontal {
            background: #f5f5f5;
            border-radius: 4px;
        }

        QSlider::handle:horizontal {
            background: #ffffff;
            width: 18px;
            height: 18px;
            margin: -6px 0;
            border-radius: 9px;
            border: 2px solid #d9d9d9;
        }

        QMessageBox {
            background-color: #0e1117;
        }

        QMessageBox QLabel {
            color: #f2f6ff;
        }
    """)


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()