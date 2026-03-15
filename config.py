from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    model_name: str = "gpt-4o"
    max_search_results: int = 5
    max_search_content_length: int = 8000
    max_url_content_length: int = 5000
    output_dir: str = "example_output"
    log_level: str = "INFO"


settings = Settings()
