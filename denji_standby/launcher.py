"""Console entry point for Denji StandBy."""

from pathlib import Path
import sys

try:
	from main import run_denji
except ModuleNotFoundError:
	sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
	from main import run_denji
