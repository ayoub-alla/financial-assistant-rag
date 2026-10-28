import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.retrieval import TOP_K, retrieve

load_dotenv()

SYSTEM = """You answer questions about the annual reports of Attijariwafa Bank, Maroc Telecom and Marsa Maroc.

Rules:
1. Use ONLY the numbered context passages provided. Never use outside knowledge.
2. If the passages do not contain the answer, reply exactly: "I don't know based on the available documents." (in French: "Je ne sais pas d'après les documents disponibles.") Do not guess.
3. After each claim, cite the passage number in brackets, like [2]. Only cite passages you actually used.
4. Copy figures exactly as written, with their unit (for example MAD million) and the year or column they belong to. Read table headers carefully: passages may show several years or segments, so pick the right column.
5. Answer in the language of the question (French or English).
6. Give no investment advice, recommendation or forecast. If asked whether to buy or sell, say you cannot give investment advice, and you may state relevant facts from the documents.
7. Some Marsa Maroc statements write numbers with dots as thousands separators and a comma for decimals (19.257.219,87 = 19,257,219.87).
8. Always say which scope each figure refers to (consolidated group, parent company, segment, subsidiary). If the question does not specify a scope, give the consolidated figure first. Never present figures of different scopes as the same metric. If the passages only show a non-consolidated or partial figure, say so.
"""

_client = None
_dead = set()  # models that returned 404 in this process


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _model_chain():
    keys = ("GEMINI_MODEL", "GEMINI_MODEL_BACKUP1", "GEMINI_MODEL_BACKUP2")
    return [n for n in (os.getenv(k, "").strip() for k in keys) if n]


def _generate(prompt):
    chain = _model_chain()
    if not chain:
        raise RuntimeError("No Gemini model set: fill GEMINI_MODEL in .env")
    log = []
    for name in chain:
        if name in _dead:
            continue
        try:
            resp = _get_client().models.generate_content(
                model=name,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0),
            )
            if resp.text:
                return resp.text.strip(), name
            log.append(f"{name}: empty response")
        except Exception as e:
            if getattr(e, "code", None) == 404:
                _dead.add(name)
            log.append(f"{name}: {type(e).__name__}: {str(e)[:150]}")
    raise RuntimeError("All Gemini models failed:\n" + ("\n".join(log) or "all models marked unavailable"))


def build_context(hits):
    return "\n\n".join(
        f"[{i}] {h['company_name']} | {h['year']} annual report | page {h['page']}\n{h['text']}"
        for i, h in enumerate(hits, start=1)
    )


def answer(question, k=TOP_K, **filters):
    hits = retrieve(question, k=k, **filters)
    prompt = f"Context passages:\n\n{build_context(hits)}\n\nQuestion: {question}"
    text, model_used = _generate(prompt)

    # Sources come from chunk metadata, never from text the model wrote
    cited = {int(n) for grp in re.findall(r"\[([\d,\s]+)\]", text) for n in re.findall(r"\d+", grp)}
    sources, seen = [], set()
    for n in sorted(cited):
        if 1 <= n <= len(hits):
            h = hits[n - 1]
            key = (h["source_file"], h["page"])
            if key not in seen:
                seen.add(key)
                sources.append({k_: h[k_] for k_ in ("company_name", "year", "doc_type", "source_file", "page")})
    return {"answer": text, "sources": sources, "hits": hits, "model": model_used}