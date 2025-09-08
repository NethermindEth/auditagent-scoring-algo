from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    REPOS_TO_RUN: list[str] = [
        "cantina_minimal-delegation_2025_04",
        # "cantina_smart-contract-audit-of-tn-contracts_2025_08",
        # "code4rena_cabal-liquid-staking-token_2025_05",
        # "code4rena_coded-estate-invitational_2024_12",
        # "code4rena_initia-move_2025_04",
        # "code4rena_iq-ai_2025_03",
        # "code4rena_kinetiq_2025_07",
        # "code4rena_lambowin_2025_02",
        # "code4rena_liquid-ron_2025_03",
        # "code4rena_pump-science_2025_02",
    ]
    MODEL: str = "gpt-5-nano-2025-08-07"
    ITERATIONS: int = 3
    BATCH_SIZE: int = 10
    SCAN_SOURCE: str = "hound"
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
    LANGFUSE_HOST: str | None = Field(default=None, env="LANGFUSE_HOST")
    LANGFUSE_PUBLIC_KEY: str | None = Field(default=None, env="LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY: str | None = Field(default=None, env="LANGFUSE_SECRET_KEY")
    LANGFUSE_USER_ID: str | None = Field(default=None, env="LANGFUSE_USER_ID")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
