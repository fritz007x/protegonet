import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_id: str = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")
    gemini_embedding_model_id: str = os.getenv(
        "GEMINI_EMBEDDING_MODEL_ID", "models/text-embedding-004"
    )

    safe_browsing_key: str = os.getenv("SAFE_BROWSING_KEY", "")
    urlscan_key: str = os.getenv("URLSCAN_KEY", "")

    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587") or "587")
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    hitl_approver_email: str = os.getenv("HITL_APPROVER_EMAIL", "")
    hitl_signing_key: str = os.getenv("HITL_SIGNING_KEY", "change-me")
    hitl_link_ttl_minutes: int = int(os.getenv("HITL_LINK_TTL_MINUTES", "60") or "60")
    hitl_public_base_url: str = os.getenv("HITL_PUBLIC_BASE_URL", "http://localhost:8000")

    sqlite_checkpoint_path: str = os.getenv("SQLITE_CHECKPOINT_PATH", "./data/checkpoints.sqlite")
    audit_db_path: str = os.getenv("AUDIT_DB_PATH", "./data/audit.sqlite")

    vendor_api_key: str = os.getenv("VENDOR_API_KEY", "")


settings = Settings()


def gemini_credentials_present() -> bool:
    return bool(settings.gemini_api_key)
