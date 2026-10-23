import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    api_key: str
    user_id: str
    base_url: str | None


def load_settings() -> Settings:
    # The SDK does not read .env itself, so we load it here.
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("COMINTY_API_KEY", "").strip()
    user_id = os.getenv("COMINTY_USER_ID", "").strip()
    if not api_key or not user_id:
        raise RuntimeError(
            "COMINTY_API_KEY and COMINTY_USER_ID must be set in .env "
            "(see .env.example)."
        )
    return Settings(
        api_key=api_key,
        user_id=user_id,
        base_url=os.getenv("COMINTY_BASE_URL") or None,
    )
