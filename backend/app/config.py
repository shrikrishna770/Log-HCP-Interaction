import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./crm.db")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    class Config:
        env_file = ".env"

settings = Settings()
