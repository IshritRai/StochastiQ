"""Environment-based configuration.

Every value here is overridable via environment variable so the same code
runs against SQLite locally and Postgres in Docker/cloud: Python only, no
microservices, and cloud-ready is satisfied by environment-based config.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./stochastiq.db"

    # LLM: Gemini API, called from the backend only. Key comes from the
    # environment; never hard-code it or log it.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # Simulation defaults (10k-50k iterations, fixed seed).
    default_seed: int = 42
    default_n_iter: int = 20_000

    # USD -> INR conversion. Single configurable rate, labeled illustrative
    # everywhere it is used.
    usd_to_inr_rate: float = 83.0
    usd_to_inr_rate_asof: str = "2026-09-24"  # source date for the rate above

    # ExposureMult bounds (is_assumption=true).
    exposure_mult_lo: float = 0.5
    exposure_mult_hi: float = 3.0

    # Floor on combined resistive-control reduction: controls may never
    # jointly claim more than (1 - combined_control_reduction_floor) of
    # Vuln reduction.
    combined_control_reduction_floor: float = 0.15

    # Tornado/sensitivity perturbation size (+/- this fraction of each
    # factor), and the thresholds for the Fragile/Unstable flags
    # (is_assumption=true, revisit with real telemetry history).
    tornado_perturbation_pct: float = 0.20
    fragile_swing_threshold: float = 0.50  # a single factor's +/-20% swing moves EAL by >50%
    unstable_stderr_threshold: float = 0.05  # MC std_err is >5% of EAL: needs more iterations


settings = Settings()
