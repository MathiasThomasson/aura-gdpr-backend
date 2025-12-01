from dotenv import load_dotenv

# Load .env before importing settings or app
load_dotenv()

from app.main import app  # noqa: E402,F401
