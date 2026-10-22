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
    commands.add_parser('config-check')
    smoke = commands.add_parser('gms-smoke')
    smoke.add_argument('--output', type=Path)
    commands.add_parser('index')
    plan = commands.add_parser('plan-question')
    plan.add_argument('question')
    plan.add_argument('--output', type=Path)
    evaluation = commands.add_parser('evaluate')
    evaluation.add_argument('--cases', type=Path)
    evaluation.add_argument('--output', type=Path)
    evaluation.add_argument('--strategy', choices=['single','clauses'], default='single')
    search = commands.add_parser('search')
    search.add_argument('question')
    search.add_argument('--evidence-mode',choices=['similarity','mmr'])
    search.add_argument('--topic', action='append', dest='topics')
    search.add_argument('--output', type=Path)
    search.add_argument('--strategy', choices=['single','clauses','semantic'], default='single')
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.command == 'config-check':
        from .settings import GMSSettings
        print(json.dumps(GMSSettings.load(repo).status(),ensure_ascii=False,indent=2))
        return
    if args.command == 'gms-smoke':
        from .settings import GMSSettings
        from .gms import GMSClient, GMSClientError
        import time
        started = time.monotonic()
        try:
            response = GMSClient(GMSSettings.load(repo)).respond(
                'Reply with exactly GMS_CONNECTION_OK and nothing else.', max_output_tokens=512)
            result = {'ok': response.text == 'GMS_CONNECTION_OK', 'model': response.model,
                      'status': response.status, 'usage': response.usage,
                      'expected_marker_received': response.text == 'GMS_CONNECTION_OK',
                      'network_request_sent': True}
        except GMSClientError as exc:
            result = {'ok':False, 'error_code':exc.code, 'http_status':exc.status_code,
                      'network_request_sent':exc.code!='settings_not_ready'}
        result['elapsed_seconds'] = round(time.monotonic()-started, 2)
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if not result['ok']:
            raise SystemExit(1)
        return
    if args.command == 'plan-question':
        from .semantic_plan import SemanticPlanner, SemanticPlanError
        from .gms import GMSClientError
        try:
            result = SemanticPlanner(repo, cache_dir=(args.runtime or repo/'.runtime')/'semantic_plans').plan(args.question)
        except (GMSClientError, SemanticPlanError) as exc:
            print(json.dumps({'ok':False,'error_code':getattr(exc,'code',str(exc))},ensure_ascii=False))
            raise SystemExit(1)
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
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
        result = evaluate(store, args.cases or repo/'tests/search_cases.json', strategy=args.strategy)
        output = args.output or runtime/'evaluation.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k!='results'}, ensure_ascii=False, indent=2))
        print(str(output))
        return
    result = store.retrieve(args.question, args.topics, strategy=args.strategy,evidence_mode=args.evidence_mode)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    brief = {'question':result['question'], 'search_strategy':result['search_strategy'], 'query_plan':result['query_plan'],'topic_candidates':result['topic_candidates'],
             'semantic_plan':result.get('semantic_plan'),
             'selected_item_ids':result['selected_item_ids'], 'selection_mode':result['selection_mode'],
             'selection_is_confirmed':result['selection_is_confirmed'],
             'evidence':[{'title':e['title'],'section':e['section_title'],'source_url':e['source_url'],
                          'parent_chunk_id':e['parent_chunk_id'],'role':e['role']} for e in result['evidence']],
             'warnings':result['warnings'],'answer_generated':False}
    print(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
