"""
Configuration settings for HealthPay Reconciliation Agent.
Uses environment variables with sensible defaults.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="HEALTHPAY_")

    # FHIR Server configuration
    fhir_server_url: str = "http://localhost:19911/fhir"
    fhir_access_token: Optional[str] = None

    # Server metadata
    server_name: str = "healthpay-reconciliation-agent"
    server_version: str = "0.1.0"

    # Reconciliation settings
    default_date_range_days: int = 90
    match_tolerance_amount: float = 0.01  # USD tolerance for amount matching
    match_tolerance_days: int = 3  # Days tolerance for date matching

    # 0G Storage configuration
    zg_private_key: Optional[str] = None
    zg_evm_rpc: str = "https://evmrpc-testnet.0g.ai"
    zg_indexer_rpc: str = "https://indexer-storage-testnet-turbo.0g.ai"

    # 0G Compute configuration
    zg_compute_private_key: Optional[str] = None
    zg_compute_rpc: Optional[str] = None
    zg_compute_model: str = "Qwen/Qwen2.5-7B-Instruct"

    # Gemma 4 configuration (Google AI Studio)
    gemma4_api_key: Optional[str] = None  # GEMINI_API_KEY
    gemma4_model: str = "gemma-4-27b-it"  # Default: 27B instruction-tuned
    gemma4_temperature: float = 0.3  # Low temperature for medical accuracy
    gemma4_max_tokens: int = 4096  # Maximum output tokens

    # LLM provider priority (gemma4 | 0g | openai)
    llm_provider: str = "gemma4"  # Default to Gemma 4 for Kaggle compliance

    # OpenAI fallback (when Gemma 4 and 0G unavailable)
    openai_api_key: Optional[str] = None


settings = Settings()
