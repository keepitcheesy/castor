"""UI components for Castor."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from castor.engine import CastorEngine
from castor.models import ItemStatus


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.engine = CastorEngine()
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Castor - RSS Content Aggregator")
        self.setMinimumSize(800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)

        # Control panel
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        # Status bar
        self.status_label = QLabel("Status: Stopped")
        layout.addWidget(self.status_label)

        # Tab widget for different views
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Queue tab
        self.queue_list = QListWidget()
        self.tabs.addTab(self.queue_list, "Queue")

        # Programs tab
        self.programs_list = QListWidget()
        self.programs_list.itemClicked.connect(self.on_program_selected)
        self.tabs.addTab(self.programs_list, "Programs")

        # Program view tab
        self.program_view = QTextEdit()
        self.program_view.setReadOnly(True)
        self.tabs.addTab(self.program_view, "Program View")

    def create_control_panel(self) -> QWidget:
        """Create control panel with Start/Stop buttons."""
        panel = QWidget()
        layout = QHBoxLayout(panel)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.on_start)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)

        layout.addStretch()

        return panel

    def setup_timer(self):
        """Set up timer for UI updates."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(1000)  # Update every second

    def on_start(self):
        """Handle start button click."""
        self.engine.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.update_ui()

    def on_stop(self):
        """Handle stop button click."""
        self.engine.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_ui()

    def update_ui(self):
        """Update UI with current status."""
        status = self.engine.get_status()

        # Update status label
        status_text = (
            f"Status: {status['status_message']} | "
            f"Feeds: {status['feeds_count']} | "
            f"New Items: {status['new_items_count']} | "
            f"Queued: {status['queued_items_count']} | "
            f"Programs: {status['programs_count']} | "
            f"Available Anchors: {status['available_anchors']}"
        )
        self.status_label.setText(status_text)

        # Update queue list
        self.update_queue_list()

        # Update programs list
        self.update_programs_list()

    def update_queue_list(self):
        """Update queue list with current items."""
        self.queue_list.clear()

        # Get queued items
        queued_items = self.engine.db.get_items_by_status(ItemStatus.QUEUED, limit=50)
        for item in queued_items:
            self.queue_list.addItem(f"{item.title} (Score: {item.score:.1f})")

        # Also show new items
        new_items = self.engine.db.get_items_by_status(ItemStatus.NEW, limit=20)
        if new_items and queued_items:
            self.queue_list.addItem("--- New Items ---")
        for item in new_items:
            self.queue_list.addItem(f"{item.title} (Score: {item.score:.1f})")

    def update_programs_list(self):
        """Update programs list."""
        self.programs_list.clear()

        programs = self.engine.db.get_all_programs(limit=50)
        for program in programs:
            anchor = self.engine.db.get_anchor(program.anchor_id)
            anchor_name = anchor.name if anchor else "Unknown"
            date_str = program.generated_at.strftime("%Y-%m-%d %H:%M")
            self.programs_list.addItem(f"{program.title} - {anchor_name} - {date_str}")

        # Store programs for later retrieval
        self.programs = programs

    def on_program_selected(self, item):
        """Handle program selection."""
        index = self.programs_list.row(item)
        if index < len(self.programs):
            program = self.programs[index]
            self.display_program(program)
            self.tabs.setCurrentIndex(2)  # Switch to Program View tab

    def display_program(self, program):
        """Display program script in the program view."""
        anchor = self.engine.db.get_anchor(program.anchor_id)
        anchor_name = anchor.name if anchor else "Unknown"

        text = f"Program: {program.title}\n"
        text += f"Anchor: {anchor_name}\n"
        text += f"Generated: {program.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"Items: {len(program.item_ids)}\n"
        text += "\n" + "=" * 80 + "\n\n"
        text += program.script

        self.program_view.setText(text)

    def closeEvent(self, event):
        """Handle window close event."""
        self.engine.close()
        event.accept()
