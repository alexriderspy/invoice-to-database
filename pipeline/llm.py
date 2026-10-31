# pipeline/llm.py
import hashlib, json, sqlite3, time
from openai import OpenAI
from pydantic import BaseModel
from pipeline import config

client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)

def every_key_required(schema: dict) -> dict:
    # Small models skip optional keys. So every key must appear, and a missing value is written as null.
    for part in [schema, *schema.get("$defs", {}).values()]:
        part["required"] = list(part["properties"])
    return schema

def chat_json(messages: list[dict], schema: type[BaseModel]) -> tuple[str, dict]:
    # Same model + same messages = same answer, so we cache it and never wait twice.
    key = hashlib.sha256(json.dumps([config.LLM_MODEL, messages]).encode()).hexdigest()
    with sqlite3.connect(config.CACHE_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
        row = db.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
    if row:
        return json.loads(row[0])["text"], json.loads(row[0])["usage"]
    shape = every_key_required(schema.model_json_schema())
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=config.LLM_MODEL, messages=messages, temperature=0, seed=7,
        response_format={"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": shape}})
    text = response.choices[0].message.content or ""
    usage = {"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens,
             "seconds": round(time.perf_counter() - start, 2)}
    value = json.dumps({"text": text, "usage": usage})
    with sqlite3.connect(config.CACHE_PATH) as db:
        db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (key, value))
    return text, usage
