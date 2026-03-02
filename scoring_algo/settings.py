from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

# Fixed at 3: majority voting logic in iteration.py and early-exit
# optimisation in batching.py both assume exactly 3 iterations.
ITERATIONS: int = 3


class Settings(BaseSettings):
    REPOS_TO_RUN: list[str] = [
        # "cantina_minimal-delegation_2025_04",
        # "cantina_smart-contract-audit-of-tn-contracts_2025_08",
        # "code4rena_bakerfi-invitational_2025_02",
        # "code4rena_fenix-finance-invitational_2024_10",
        # "code4rena_iq-ai_2025_03",
        # "code4rena_kinetiq_2025_07",
        # "code4rena_lambowin_2025_02",
        # "code4rena_liquid-ron_2025_03",
        # "code4rena_loopfi_2025_02",
        "code4rena_secondswap_2025_02",
        # "code4rena_superposition_2025_01",
    ]
    MODEL: str = "o4-mini"
    BATCH_SIZE: int = 10
    SCAN_SOURCE: str = "auditagent"
    DATA_ROOT: str = "../data"
    OUTPUT_ROOT: str = "../benchmarks"
    DEBUG_PROMPT: bool = False
    SUPPORTED_MODELS: dict[str, list[str]] = {
        "openai": [
            "o3-2025-04-16",
            "o4-mini",
            "gpt-4.1-nano-2025-04-14",
            "gpt-5-2025-08-07",
            "gpt-5-nano-2025-08-07",
        ],
    }
    LANGFUSE_HOST: str | None = None
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_USER_ID: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
