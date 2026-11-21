"""AutoMind AI — moteur de recherche automobile conversationnel (analyse par règles, hors ligne)."""

from pathlib import Path

__version__ = "1.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CARS_PATH = DATA_DIR / "cars.json"
FIXTURES_PATH = DATA_DIR / "test_fixtures.json"
SUMMARY_PATH = PROJECT_ROOT / "docs" / "data_summary.md"
