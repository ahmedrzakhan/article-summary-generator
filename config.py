import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

# SOLUTION: Manually load .env file
from dotenv import load_dotenv

# Force load the .env file before creating Settings
load_dotenv()

# Add these debug prints
print(f"🔍 Current working directory: {os.getcwd()}")
print(f"🔍 .env file exists: {os.path.exists('.env')}")
print(f"🔍 .env file path: {os.path.abspath('.env')}")
# Add this in your __init__ method
print(f"🔍 GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
print(f"🔍 GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")

class Settings(BaseSettings):
    google_cloud_project: Optional[str] = Field(default=None, env="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[str] = Field(
        default=None, env="GOOGLE_APPLICATION_CREDENTIALS"
    )
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")

    langchain_tracing_v2: bool = Field(default=False, env="LANGCHAIN_TRACING_V2")
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT"
    )
    langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(
        default="article-summary-generator", env="LANGCHAIN_PROJECT"
    )

    api_host: str = Field(default="localhost", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=True, env="DEBUG")

    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")

    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()