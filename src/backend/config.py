from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = ROOT / "uploads"
REPORT_DIR = ROOT / "reports"
DB_PATH = Path(os.getenv("SIGMA_DB_PATH", str(ROOT / "data" / "sigma.db")))
MAX_UPLOAD_BYTES = int(os.getenv("SIGMA_MAX_UPLOAD_BYTES", str(512 * 1024 * 1024)))
MAX_ANALYSIS_SAMPLES = int(os.getenv("SIGMA_MAX_ANALYSIS_SAMPLES", "1000000"))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
