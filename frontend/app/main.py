import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.resources.style import load_stylesheet
from app.state.session import session_store
from app.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ProjectsControl")
    app.setFont(QFont("Manrope", 10))

    app.setStyleSheet(load_stylesheet(session_store.theme, session_store.background_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
