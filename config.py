import os
from pathlib import Path
from dotenv import load_dotenv

# Load file .env nếu có
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")
PREFIX = os.getenv("BOT_PREFIX", "!")

# Owner IDs (chỉ những ID này và Server Owner mới được dùng lệnh backup)
raw_owners = os.getenv("BOT_OWNER_IDS", "")
OWNER_IDS = set()
if raw_owners:
    for oid in raw_owners.split(","):
        oid = oid.strip()
        if oid.isdigit():
            OWNER_IDS.add(int(oid))

# Tự động sao lưu
AUTO_BACKUP_ENABLED = os.getenv("AUTO_BACKUP_ENABLED", "False").lower() in ("true", "1", "yes")
AUTO_BACKUP_INTERVAL_HOURS = int(os.getenv("AUTO_BACKUP_INTERVAL_HOURS", "24"))
MAX_BACKUPS_PER_GUILD = int(os.getenv("MAX_BACKUPS_PER_GUILD", "10"))

# Thư mục lưu backup
BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
