from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", str(PROJECT_DIR / "learnai.db"))
).expanduser()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

