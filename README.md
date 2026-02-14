# Castor

Castor is an RSS-based content aggregation and script generation system. It automatically fetches content from RSS feeds, scores and deduplicates items, schedules content with anchor rotation, and generates program scripts ready for presentation.

## Features

- **RSS Feed Ingestion**: Automatically fetch and parse RSS feeds
- **Content Scoring**: Intelligent scoring based on recency, quality, and relevance
- **Deduplication**: Avoid duplicate content with similarity detection
- **Anchor Scheduling**: Rotate anchors/presenters with configurable cooldown periods
- **Script Generation**: Generate presentation-ready scripts from selected content
- **PySide6 UI**: Clean, intuitive interface with real-time status updates
- **SQLite Persistence**: Reliable local database storage
- **Automated Workflow**: Continuous operation with configurable intervals

## Requirements

- Python 3.11 or higher
- PySide6 for UI
- feedparser for RSS parsing
- requests for HTTP operations
- SQLite (included with Python)

## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/keepitcheesy/castor.git
cd castor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. For development, install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

### Using pip

```bash
pip install .
```

## Quick Start

1. **Initialize the database with sample data**:
```bash
python -m castor.init_db
```

This creates a `castor.db` file and populates it with:
- Sample RSS feeds (Hacker News, Reddit Technology)
- Three sample anchors (Alice, Bob, Charlie)
- A default script template

2. **Run the application**:
```bash
python -m castor.main
```

Or if installed:
```bash
castor
```

3. **Using the UI**:
   - Click **Start** to begin the automated workflow
   - Monitor status in the status bar
   - View **Queue** tab to see pending items
   - View **Programs** tab to see generated programs
   - Click a program to view its full script in **Program View**
   - Click **Stop** to pause operations

## Configuration

### Feed Management

Add RSS feeds to the database by modifying `castor/init_db.py` or using the database directly:

```python
from castor.persistence import Database
from castor.models import Feed

db = Database()
feed = Feed(url="https://example.com/rss", name="My Feed", active=True)
db.add_feed(feed)
db.close()
```

Example feeds are provided in `examples/feeds.txt`.

### Anchor Management

Add anchors (presenters) with custom cooldown periods:

```python
from castor.persistence import Database
from castor.models import Anchor

db = Database()
anchor = Anchor(name="Your Name", cooldown_minutes=90)
db.add_anchor(anchor)
db.close()
```

### Timing Configuration

Edit intervals in `castor/engine.py`:

```python
self.fetch_interval_seconds = 300  # Feed update interval (5 minutes)
self.program_interval_seconds = 600  # Program generation interval (10 minutes)
self.items_per_program = 5  # Items per program
```

See `examples/config.ini` for additional configuration options (future versions will support loading from this file).

## Architecture

### Components

- **Models** (`castor/models/`): Data structures (Feed, Item, Anchor, Program, Script)
- **Persistence** (`castor/persistence/`): SQLite database layer with CRUD operations
- **Ingestion** (`castor/ingestion/`): RSS feed fetching and parsing
- **Scoring** (`castor/scoring/`): Item scoring, deduplication, and scheduling
- **Scripting** (`castor/scripting/`): Program script generation from templates
- **Engine** (`castor/engine.py`): Core orchestration and workflow management
- **UI** (`castor/ui/`): PySide6 graphical interface

### Workflow

1. **Feed Ingestion**: Periodically fetch RSS feeds (respecting ETag/Last-Modified)
2. **Scoring**: Assign scores to new items based on recency, title, and content quality
3. **Scheduling**: Select top-scored items and deduplicate
4. **Anchor Selection**: Choose an available anchor (respecting cooldown)
5. **Script Generation**: Create program script using template and selected items
6. **Program Storage**: Save program to database for viewing

## Development

### Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=castor --cov-report=html
```

### Code Quality

Format code with black:
```bash
black castor tests
```

Lint with ruff:
```bash
ruff check castor tests
```

Auto-fix linting issues:
```bash
ruff check --fix castor tests
```

### Project Structure

```
castor/
├── castor/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── engine.py            # Core engine
│   ├── init_db.py           # Database initialization
│   ├── models/              # Data models
│   ├── persistence/         # Database layer
│   ├── ingestion/           # RSS ingestion
│   ├── scoring/             # Scoring and scheduling
│   ├── scripting/           # Script generation
│   └── ui/                  # PySide6 UI
├── tests/                   # Test suite
├── examples/                # Example configurations
├── pyproject.toml           # Project configuration
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## Building Executable

Build a standalone executable with PyInstaller:

```bash
pyinstaller --name castor \
    --onefile \
    --windowed \
    --add-data "castor:castor" \
    castor/main.py
```

The executable will be created in the `dist/` directory.

For platform-specific builds, see PyInstaller documentation.

## Testing

The test suite covers:

- **Models**: Data structure validation
- **Persistence**: Database operations, CRUD, constraints
- **Scoring**: Item scoring algorithms, deduplication
- **Scheduling**: Anchor selection, cooldown management
- **Scripting**: Template processing, script generation

Run specific test files:
```bash
pytest tests/test_models.py
pytest tests/test_persistence.py
pytest tests/test_scoring.py
pytest tests/test_scripting.py
```

## Troubleshooting

### Database Issues

If you encounter database errors, remove `castor.db` and reinitialize:
```bash
rm castor.db
python -m castor.init_db
```

### Feed Fetch Errors

- Verify RSS feed URLs are accessible
- Check network connectivity
- Some feeds may require specific User-Agent headers

### UI Not Starting

Ensure PySide6 is properly installed:
```bash
pip install --upgrade PySide6
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code is formatted
6. Submit a pull request

## License

[Add your license here]

## Future Enhancements

- Configuration file loading
- Web-based admin interface
- Export programs in multiple formats (PDF, audio, etc.)
- Advanced NLP-based content analysis
- Multi-language support
- Cloud sync and backup
- Plugin system for custom scorers and templates

## Contact

[Add contact information]
