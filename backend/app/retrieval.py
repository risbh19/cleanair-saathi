"""Optional semantic search over the reviewed bilingual reference library."""
from hashlib import sha256
import json
from math import isfinite
import os
import re
from urllib.request import Request, urlopen

import psycopg
from backend.db.migrate import connect


def model_name():
    model = os.getenv("GEMINI_EMBEDDING_MODEL", "")
    return model if re.fullmatch(r"[a-z0-9.-]+", model) else None


def embedding(text, model, kind):
    key = os.environ["GEMINI_API_KEY"]
    body = {"model": "models/" + model, "content": {"parts": [{"text": text}]},
            "outputDimensionality": 768, "taskType": kind}
    req = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
                  data=json.dumps(body).encode(), headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    with urlopen(req, timeout=4) as response:
        vector = json.load(response)["embedding"]["values"]
    if len(vector) != 768 or not all(isinstance(x, (int, float)) and isfinite(x) for x in vector) or not any(vector):
        raise ValueError("Invalid embedding")
    return json.dumps(vector)


def library_version(sources):
    return sha256(json.dumps(sources, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def prepare(sources):
    model = model_name()
    if not model:
        raise ValueError("Set GEMINI_EMBEDDING_MODEL")
    version = library_version(sources)
    rows = [(model, version, key, embedding(" ".join((entry[0], entry[3], entry[4])), model, "RETRIEVAL_DOCUMENT"))
            for key, entry in sources.items()]
    with connect() as db:
        db.execute("CREATE EXTENSION IF NOT EXISTS vector")
        db.execute("""CREATE TABLE IF NOT EXISTS saathi_passages (
            model text, version text, passage text, embedding vector(768) NOT NULL,
            PRIMARY KEY (model, version, passage))""")
        with db.cursor() as cursor:
            cursor.executemany("""INSERT INTO saathi_passages VALUES (%s,%s,%s,%s::vector)
                ON CONFLICT (model,version,passage) DO UPDATE SET embedding=EXCLUDED.embedding""", rows)


def retrieve(question, sources):
    model = model_name()
    if not model or not os.getenv("GEMINI_API_KEY"):
        return []
    version = library_version(sources)
    try:
        with connect() as db:
            if not db.execute("SELECT to_regclass('saathi_passages')").fetchone()[0]:
                return []
            vector = embedding(question, model, "RETRIEVAL_QUERY")
            rows = db.execute("""SELECT passage FROM saathi_passages WHERE model=%s AND version=%s
                ORDER BY embedding <=> %s::vector LIMIT 3""", (model, version, vector)).fetchall()
            return [row[0] for row in rows if row[0] in sources]
    except (psycopg.Error, OSError, ValueError, KeyError, TypeError):
        return []


if __name__ == "__main__":
    from .saathi import SOURCES
    prepare(SOURCES)
