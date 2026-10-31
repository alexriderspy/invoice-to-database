# pipeline/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Ollama speaks the OpenAI API, so a cloud model is just a different URL, key and model name.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")

# Your provider's price in US dollars per million tokens. A local model costs 0.
PRICE_IN_PER_M = float(os.getenv("PRICE_IN_PER_M", "0"))
PRICE_OUT_PER_M = float(os.getenv("PRICE_OUT_PER_M", "0"))

CACHE_PATH = os.getenv("CACHE_PATH", "llm_cache.db")
