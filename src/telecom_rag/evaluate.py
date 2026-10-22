"""Authored development checks. This is not a held-out user evaluation."""
import json
from pathlib import Path


def evaluate(store, cases_path: Path):
    cases = json.loads(cases_path.read_text(encoding='utf-8-sig'))
    results=[]
    for case in cases:
        ranked=store.search_topics(case['question'])
        ids=[r['item_id'] for r in ranked]
        expected=set(case['expected'])
        def match(n):
            actual=set(ids[:n])
            return bool(expected & actual) if case.get('match')=='any' else expected<=actual
        results.append({**case,'top3_match':match(3),'top5_match':match(5),'ranked':ranked})
    summary={
        'kind':('previously seen public-board regression, not independent accuracy'
                if all(c.get('sample_type')=='previously_seen_board_question_paraphrase' for c in cases)
                else 'authored development smoke checks, not independent accuracy'),
        'cases':len(results),'top3_matches':sum(r['top3_match'] for r in results),
        'top5_matches':sum(r['top5_match'] for r in results),'results':results,
    }
    return summary
