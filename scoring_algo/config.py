import os


REPOS_TO_RUN = [
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

# Default parameters used by the CLI when not overridden by flags
# You can keep using command-line options to override these at runtime.

# Model selection (auto-detected provider)
MODEL = "gpt-5-nano-2025-08-07"

# Number of LLM calls per prompt and batch size for junior findings
ITERATIONS = 3
BATCH_SIZE = 10

# Which scanner results to compare against truth: "auditagent" or "hound"
SCAN_SOURCE = "hound"

# Paths are resolved relative to `scoring_algo/` when not absolute
DATA_ROOT = "../data"
OUTPUT_ROOT = "../benchmarks"

# Whether to write the rendered prompt beside results
DEBUG_PROMPT = False


SUPPORTED_MODELS = {
    "openai": [
        "o3-2025-04-16",
        "o4-mini",
        "gpt-4.1-nano-2025-04-14",
        "gpt-5-2025-08-07",
        "gpt-5-nano-2025-08-07",
    ],
}

##################################################
#                  LANGFUSE
##################################################

LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_USER_ID = os.getenv("LANGFUSE_USER_ID")
