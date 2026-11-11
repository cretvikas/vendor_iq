from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VendorIQ API"
    database_url: str = "sqlite:///./vendor_iq.db"
    upload_dir: str = "./uploads"
    max_upload_mb: int = 10
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    # demo: deterministic mock provider for local evaluation; manual: unresolved until a real provider is integrated
    verification_mode: str = "demo"
    demo_blocked_tax_ids: str = ""  # server-side test fixture simulating an authoritative registry rejection
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Gemini AI ───────────────────────────────────────────────
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"

    # ── AI Risk Score Thresholds ────────────────────────────────
    ai_low_threshold: int = 30    # score <= this → AUTO APPROVED
    ai_high_threshold: int = 70   # score >= this → AUTO REJECTED
                                  # between low+1 and high-1 → PENDING (manual review)

    # ── Email (SMTP) ────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "VendorIQ <noreply@vendoriq.local>"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key != "your_gemini_api_key_here")

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_user and self.smtp_password
                    and self.smtp_user != "your_gmail@gmail.com")


settings = Settings()
