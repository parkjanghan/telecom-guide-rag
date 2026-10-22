from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import RetrievalStore, load_data


def main():
    parser = argparse.ArgumentParser(description='KT topic/evidence retrieval prototype (no answer generation)')
    repo_default = Path(__file__).resolve().parents[2]
    parser.add_argument('--repo', type=Path, default=repo_default)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--models', type=Path)
    parser.add_argument('--config', type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('audit')
    commands.add_parser('index')
    evaluation = commands.add_parser('evaluate')
    evaluation.add_argument('--cases', type=Path)
    evaluation.add_argument('--output', type=Path)
    search = commands.add_parser('search')
    search.add_argument('question')
    search.add_argument('--topic', action='append', dest='topics')
    search.add_argument('--output', type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.command == 'audit':
        topics, parents = load_data(repo)
        print(json.dumps({'topics':len(topics),'original_chunks':len(parents),
                          'topic_links':sum(len(t['related_chunk_ids']) for t in topics.values()),
                          'missing':[t['item_id'] for t in topics.values() if t['evidence_status']=='missing']}, ensure_ascii=False, indent=2))
        return
    config = json.loads((args.config or repo/'config/retrieval.json').read_text(encoding='utf-8-sig'))
    runtime = (args.runtime or repo/'.runtime').resolve()
    models = (args.models or runtime/'models').resolve()
    store = RetrievalStore(repo, runtime, models, config)
    if args.command == 'index':
        print(json.dumps(store.index(), ensure_ascii=False, indent=2))
        return
    if args.command == 'evaluate':
        from .evaluate import evaluate
        result = evaluate(store, args.cases or repo/'tests/search_cases.json')
        output = args.output or runtime/'evaluation.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k!='results'}, ensure_ascii=False, indent=2))
        print(str(output))
        return
    result = store.retrieve(args.question, args.topics)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    brief = {'question':result['question'],'topic_candidates':result['topic_candidates'],
             'selected_item_ids':result['selected_item_ids'], 'selection_mode':result['selection_mode'],
             'selection_is_confirmed':result['selection_is_confirmed'],
             'evidence':[{'title':e['title'],'section':e['section_title'],'source_url':e['source_url'],
                          'parent_chunk_id':e['parent_chunk_id'],'role':e['role']} for e in result['evidence']],
             'warnings':result['warnings'],'answer_generated':False}
    print(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
