"""Optional thresholded search over the versioned reviewed bilingual library."""
from hashlib import sha256
import json
from math import isfinite, sqrt
import os
import re

from google import genai
from google.genai import types
import psycopg
from backend.db.migrate import connect
from .gemini import http_options, provider_slot


def model_name():
    model = os.getenv("GEMINI_EMBEDDING_MODEL", "")
    return model if re.fullmatch(r"[a-z0-9.-]+", model) else None


def embedding(text, model, kind):
    if not provider_slot():
        raise ValueError("Embedding request budget exhausted")
    with genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                      http_options=http_options()) as client:
        result = client.models.embed_content(model=model, contents=text, config=types.EmbedContentConfig(
            output_dimensionality=768, task_type=kind))
    vector = result.embeddings[0].values
    if len(vector) != 768 or not all(type(x) in (int, float) and isfinite(x) for x in vector) or not any(vector):
        raise ValueError("Invalid embedding")
    # gemini-embedding-001 requires normalization when reducing dimensions.
    norm = sqrt(sum(x * x for x in vector))
    if not isfinite(norm) or norm == 0:
        raise ValueError("Invalid embedding norm")
    return json.dumps([x / norm for x in vector])


def library_version(sources):
    return sha256(json.dumps(sources, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def prepare(sources):
    model = model_name()
    if not model:
        raise ValueError("Set GEMINI_EMBEDDING_MODEL")
    version = library_version(sources)
    # All remote work completes before opening the atomic index transaction.
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
        floor = float(os.getenv("RAG_SIMILARITY_MIN", "0.75"))
        if not isfinite(floor) or not 0 <= floor <= 1:
            return []
        with connect() as db:
            if not db.execute("SELECT to_regclass('saathi_passages')").fetchone()[0]:
                return []
            # Avoid spending query quota until the current source/model index exists.
            if not db.execute("SELECT 1 FROM saathi_passages WHERE model=%s AND version=%s LIMIT 1",
                              (model, version)).fetchone():
                return []
            vector = embedding(question, model, "RETRIEVAL_QUERY")
            rows = db.execute("""SELECT passage, 1 - (embedding <=> %s::vector) AS similarity
                FROM saathi_passages WHERE model=%s AND version=%s
                AND 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector LIMIT 5""",
                (vector, model, version, vector, floor, vector)).fetchall()
            return [key for key, score in rows if key in sources and isfinite(score) and score >= floor]
    except Exception:
        # Missing extension/index, SDK quota and transport errors keep keyword lookup usable.
        return []


if __name__ == "__main__":
    from .saathi import SOURCES
    prepare(SOURCES)
