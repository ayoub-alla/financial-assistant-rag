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
7. Some Marsa Maroc statements write numbers with dots as thousands separators and a comma for decimals (19.257.219,87 = 19,257,219.87)."""

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def build_context(hits):
    return "\n\n".join(
        f"[{i}] {h['company_name']} | {h['year']} annual report | page {h['page']}\n{h['text']}"
        for i, h in enumerate(hits, start=1)
    )


def answer(question, k=TOP_K, **filters):
    hits = retrieve(question, k=k, **filters)
    prompt = f"Context passages:\n\n{build_context(hits)}\n\nQuestion: {question}"
    resp = _get_client().models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0),
    )
    text = (resp.text or "").strip()

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
    return {"answer": text, "sources": sources, "hits": hits}