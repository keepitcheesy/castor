"""Main entry point for Castor application."""

import sys

from PySide6.QtWidgets import QApplication

from castor.ui import MainWindow


def main():
    """Run the Castor application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
