from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://rag:rag@localhost:5432/rag"

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = (
        "qwen3-4b-instruct-8k"  # qwen3:4b-instruct-2507 with an 8K context, from ollama/Modelfile
    )
    # Sent as reasoning_effort; "none" turns thinking off on Ollama. Empty omits the parameter.
    llm_reasoning_effort: str = ""
    # A different model family from llm_model, to limit self-preference bias.
    judge_base_url: str = "https://ollama.com/v1"
    judge_api_key: str = ""
    judge_model: str = "gpt-oss:120b"
    judge_rpm: float = 20  # pacing for hosted free tiers

    embed_base_url: str = "http://localhost:11434/v1"
    embed_api_key: str = ""
    embed_model: str = "bge-m3"

    price_in_per_mtok: float = 0.0
    price_out_per_mtok: float = 0.0

    top_k: int = 5
    max_tool_rounds: int = 3
    # Classifier scores above this drop a chunk or refuse a question. Chosen on the dev split.
    injection_threshold: float = 0.5
    # Planted in the system prompt; seeing it in an answer means the prompt leaked.
    canary: str = "CANARY-7f3a91c2"


settings = Settings()
