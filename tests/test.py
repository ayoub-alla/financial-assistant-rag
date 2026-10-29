import csv
import json
import re
import time
from pathlib import Path
import os

from src.retrieval import  retrieve

from src.generate import _generate, build_context

TEST_FILE = Path('tests/test_set.json')
OUTPUT = Path('results/10Q_test_result.csv')
TOP_K = int(os.getenv("TOP_K", 8))

def normalize(s):
    # Accept comma/space thousands separators and decimal comma.
    return re.sub(r'(?<=\d)[,\s](?=\d{3}(?:\D|$))', '', s).lower()


def has_token(answer, token):
    a, t = normalize(answer), normalize(token)
    return t in a or token.lower() in answer.lower()


def answer_is_idk(answer):
    a = answer.lower()
    return any(s in a for s in ["i don't know", 'i do not know', 'je ne sais pas'])


def main():
    tests = json.loads(TEST_FILE.read_text(encoding='utf-8'))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ['id', 'type', 'question', 'expected', 'answer', 'model',
              'required_terms_ok', 'source_hit', 'answer_source_cited',
              'retrieval_ms', 'generation_ms', 'total_ms', 'retrieved_sources',
              'error', 'manual_correct', 'failure_type', 'notes']
    with OUTPUT.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for test in tests:
            row = {field: '' for field in fields}
            row.update({k: test.get(k, '') for k in ('id', 'type', 'question', 'expected')})
            try:
                start = time.perf_counter()
                hits = retrieve(test['question'], k=TOP_K)
                retrieved = time.perf_counter()
                prompt = f"Context passages:\n\n{build_context(hits)}\n\nQuestion: {test['question']}"
                answer, model = _generate(prompt)
                finished = time.perf_counter()
                sources = {(h.get('source_file'), h.get('page')) for h in hits}
                expected_sources = {tuple(src) for src in test.get('source', [])}
                citations = {int(n) for group in re.findall(r'\[([\d,\s]+)\]', answer)
                             for n in re.findall(r'\d+', group)}
                cited_sources = {(hits[n - 1].get('source_file'), hits[n - 1].get('page'))
                                 for n in citations if 1 <= n <= len(hits)}
                terms = test.get('must_contain', [])
                # A mechanical check, NOT a semantic accuracy judgment.
                term_ok = answer_is_idk(answer) if test.get('expect_idk') else (
                    all(has_token(answer, token) for token in terms) if terms else None)
                row.update(answer=answer, model=model, required_terms_ok=term_ok,
                           source_hit=bool(sources & expected_sources) if expected_sources else '',
                           answer_source_cited=bool(cited_sources & expected_sources) if expected_sources else '',
                           retrieval_ms=round((retrieved-start)*1000, 1),
                           generation_ms=round((finished-retrieved)*1000, 1),
                           total_ms=round((finished-start)*1000, 1),
                           retrieved_sources='; '.join(f'{h.get("source_file")} p.{h.get("page")}' for h in hits),
                           notes='Manual review required; empty term list is not automatic success.')
            except Exception as exc:
                row['error'] = f'{type(exc).__name__}: {exc}'
            writer.writerow(row)
            f.flush()
            print(f"Q{test['id']}: {row['total_ms'] or 'ERROR'} ms | terms={row['required_terms_ok']}")
    print(f'Created: {OUTPUT} (fill manual_correct, failure_type, notes after reviewing answers)')


if __name__ == '__main__':
    main()
