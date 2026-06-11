from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("ARHA_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.getenv("ARHA_DB_PATH", DATA_DIR / "arha.sqlite3"))
UPLOAD_DIR = Path(os.getenv("ARHA_UPLOAD_DIR", DATA_DIR / "uploads"))
SALT_PATH = Path(os.getenv("ARHA_SALT_PATH", DATA_DIR / "arha.salt"))
PASSPHRASE = os.getenv("ARHA_PASSPHRASE", "arha-local-development-passphrase")

INSUFFICIENT_INFO = "I do not currently have sufficient verified information to complete this request."
SCORING_FORMULA_VERSION = "arha-v1-deterministic-2026-06-11"


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
