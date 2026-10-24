import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

raw_admin_ids = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS: list[int] = []
if raw_admin_ids:
    for aid in raw_admin_ids.split(","):
        cleaned = aid.strip()
        if cleaned.isdigit():
            ADMIN_IDS.append(int(cleaned))

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "minxo_tv.db")).strip()

try:
    PORT = int(os.getenv("PORT", "8080").strip())
except ValueError:
    PORT = 8080


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("MINXO_TV")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger