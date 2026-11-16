"""GymBro computer-vision service."""
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".runtime-cache") / "matplotlib"))
