import logging
from pathlib import Path


LOG_PATH = Path("app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH, encoding="utf-8")],
)

logger = logging.getLogger("ai_fellowship_week2")