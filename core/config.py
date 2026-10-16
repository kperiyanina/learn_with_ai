from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", str(PROJECT_DIR / "learnai.db"))
).expanduser()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "15"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))
AI_FALLBACK_ENABLED = os.getenv("AI_FALLBACK_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "да",
}
API_SECRET_KEY = os.getenv(
    "API_SECRET_KEY",
    "development-secret-change-me",
)
