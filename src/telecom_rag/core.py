from __future__ import annotations

import hashlib
from datetime import date, datetime
import json
import os
import re
import sqlite3
import threading
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def read_md(path: Path) -> tuple[dict, str]:
    """Read YAML safely, including lists written by Obsidian properties."""
    text = path.read_text(encoding='utf-8-sig')
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        return {}, text
    head, body = text[4:].split('\n---\n', 1)
    import yaml
    try:
        meta = yaml.safe_load(head)
    except yaml.YAMLError as exc:
        raise ValueError(f'{path}: invalid or unsupported YAML frontmatter') from exc
    if not isinstance(meta, dict):
        raise ValueError(f'{path}: frontmatter must be a mapping')
    # Obsidian can rewrite JSON-valued fields as ordinary YAML lists.
    def normalize(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        return value
    return normalize(meta), body.lstrip('\n')


def load_data(repo: Path) -> tuple[dict, dict]:
    topics, parents = {}, {}
    registry = (repo / 'data/SOURCES.md').read_text(encoding='utf-8')
    urls = {}
    for line in registry.splitlines():
        if not line.startswith('|'):
            continue
        local = re.search(r'\]\((chunks/.+?\.md)\)', line)
        remote = re.search(r'\]\((https?://[^)]+)\)', line)
        if local and remote:
            urls['data/' + local[1]] = remote[1]
    for path in sorted((repo / 'data/topics').glob('*.md')):
        meta, body = read_md(path)
        if meta.get('source_type') != 'generated_topic_metadata' or 'item_id' not in meta:
            continue
        item_id = meta['item_id']
        if item_id in topics:
            raise ValueError(f'Duplicate topic {item_id}')
        if not meta.get('index_text') or not meta.get('name'):
            raise ValueError(f'Incomplete topic {item_id}')
        topics[item_id] = {**meta, 'path': path.relative_to(repo).as_posix()}
    for path in sorted((repo / 'data/chunks').glob('*/*.md')):
        meta, body = read_md(path)
        cid = meta['chunk_id']
        if cid in parents:
            raise ValueError(f'Duplicate original chunk {cid}')
        rel = path.relative_to(repo).as_posix()
        source = urls.get(rel)
        if not source or not urlparse(source).hostname.endswith('.kt.com'):
            raise ValueError(f'Missing/non-official URL: {rel}: {source}')
        parents[cid] = {
            'chunk_id': cid, 'document_id': meta['document_id'],
            'title': meta.get('product_name', meta.get('document_title', '')),
            'section_title': meta.get('section', meta.get('title', '')),
            'body': body, 'path': rel, 'source_url': source,
            'version': digest(body)[:16], 'meta': meta,
        }
        if not parents[cid]['title']:
            parents[cid]['title'] = parents[cid]['section_title']
    for t in topics.values():
        for cid in t['related_chunk_ids']:
            if cid not in parents:
                raise ValueError(f'{t["item_id"]}: unknown chunk {cid}')
        if not set(t['primary_chunk_ids']) <= set(t['related_chunk_ids']):
            raise ValueError(f'{t["item_id"]}: representative not linked')
    return topics, parents


def split_offsets(text: str, tokenizer, size: int, overlap: int) -> list[tuple[int, int]]:
    """Use tokenizer character offsets; preserve parent text and every character."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Require size > overlap >= 0')
    encoded = tokenizer.encode(text, add_special_tokens=False)
    spans = [(a, b) for a, b in encoded.offsets if b > a]
    if len(spans) <= size:
        return [(0, len(text))] if text else []
    ranges = []
    start = 0
    while start < len(spans):
        stop = min(start + size, len(spans))
        a = 0 if start == 0 else spans[start][0]
        # Include whitespace between adjacent tokens; overlap may repeat characters.
        b = len(text) if stop == len(spans) else spans[stop][0]
        ranges.append((a, b))
        if stop == len(spans):
            break
        start = stop - overlap
    return ranges


class Embedder:
    signature = 'Xenova/multilingual-e5-small:onnx/model_quantized.onnx:mean:l2:prefix-v1'

    def __init__(self, config: dict, runtime: Path, model_cache: Path):
        os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
        os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
        from fastembed import TextEmbedding
        from fastembed.common.model_description import ModelSource, PoolingType
        from tokenizers import Tokenizer
        if config['embedding_model'] != 'Xenova/multilingual-e5-small':
            raise ValueError('This adapter is validated only for multilingual-e5-small')
        if not any(x['model'] == 'telecom/e5-small-q' for x in TextEmbedding.list_supported_models()):
            TextEmbedding.add_custom_model(
                model='telecom/e5-small-q', pooling=PoolingType.MEAN, normalization=True,
                sources=ModelSource(hf=config['embedding_model']), dim=384,
                model_file=config['embedding_file'], license='mit', size_in_gb=0.12,
            )
        self.model = TextEmbedding('telecom/e5-small-q', cache_dir=str(model_cache),
                                   threads=config['threads'], providers=['CPUExecutionProvider'])
        self.tokenizer = Tokenizer.from_str(self.model.model.tokenizer.to_str())
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        runtime.mkdir(parents=True, exist_ok=True)
        self._cache_lock = threading.RLock()
        self.cache = sqlite3.connect(runtime / 'embeddings.sqlite3', check_same_thread=False)
        self.cache.execute('CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vector TEXT NOT NULL)')
        self.model_hash = hashlib.sha256((self.model.model._model_dir / config['embedding_file']).read_bytes()).hexdigest()
        self.cache.execute('CREATE TABLE IF NOT EXISTS model_identity (signature TEXT PRIMARY KEY, artifact_hash TEXT NOT NULL)')
        identity = self.cache.execute('SELECT artifact_hash FROM model_identity WHERE signature=?', (self.signature,)).fetchone()
        if identity and identity[0] != self.model_hash:
            raise ValueError('Embedding model files changed: use a new runtime directory')
        self.cache.execute('INSERT OR IGNORE INTO model_identity VALUES (?,?)', (self.signature, self.model_hash))
        self.cache.commit()
        self.batch = config['batch_size']
        self.dimension = config['embedding_dimension']
        self.computed = 0
        self.hits = 0

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text).ids)

    def embed(self, texts: list[str], kind: str) -> list[list[float]]:
        with self._cache_lock:
            return self._embed(texts, kind)

    def _embed(self, texts: list[str], kind: str) -> list[list[float]]:
        if kind not in {'query', 'passage'}:
            raise ValueError(kind)
        result = [None] * len(texts)
        pending = defaultdict(list)
        for i, text in enumerate(texts):
            payload = kind + ': ' + text
            if self.count_tokens(payload) > 512:
                raise ValueError('Embedding input exceeds 512 tokens; split or shorten first')
            key = digest(self.signature + '\n' + payload)
            row = self.cache.execute('SELECT vector FROM vectors WHERE key=?', (key,)).fetchone()
            if row:
                result[i] = json.loads(row[0]); self.hits += 1
            else:
                pending[(key, payload)].append(i)
        items = list(pending)
        for start in range(0, len(items), self.batch):
            batch = items[start:start + self.batch]
            vectors = list(self.model.embed([payload for _, payload in batch], batch_size=self.batch))
            for (key, payload), vector in zip(batch, vectors):
                vec = vector.tolist()
                if len(vec) != self.dimension:
                    raise ValueError('Embedding dimension mismatch')
                self.cache.execute('INSERT OR REPLACE INTO vectors VALUES (?,?)', (key, json.dumps(vec)))
                for i in pending[(key, payload)]:
                    result[i] = vec
                self.computed += 1
            self.cache.commit()
        return result


def build_records(topics, parents, config, engine):
    linked = defaultdict(list)
    for item_id, t in topics.items():
        for cid in t['related_chunk_ids']:
            linked[cid].append(item_id)
    tasks, evidence = [], []
    max_tokens = 0
    for item_id, t in topics.items():
        meta = {
            'item_id': item_id, 'name': t['name'], 'category': t['category'],
            'service_types_json': json.dumps(t['service_types'], ensure_ascii=False),
            'review_status': t['review_status'], 'evidence_status': t['evidence_status'],
            'primary_document_id': t['primary_document_id'] or '',
            'source_type': 'generated_topic_metadata', 'is_policy_evidence': False,
            'answer_ready': bool(t['answer_ready']), 'path': t['path'],
        }
        for service in t['service_types']:
            meta['service_' + service] = True
        tasks.append({'id': item_id, 'text': t['index_text'], 'meta': meta})
    for cid, p in parents.items():
        m = p['meta']
        label = p['title'] + ' / ' + p['section_title']
        # Keep title context inside the model budget without changing the original.
        while engine.count_tokens(label) > 72:
            label = label[:max(1, len(label) * 3 // 4)]
        ranges = split_offsets(p['body'], engine.tokenizer,
                               config['chunk_size_tokens'], config['chunk_overlap_tokens'])
        for n, (a, b) in enumerate(ranges):
            text = '문서: ' + label + '\n' + p['body'][a:b]
            tokens = engine.count_tokens('passage: ' + text)
            max_tokens = max(max_tokens, tokens)
            if tokens > 512:
                raise ValueError(f'{cid}: child exceeds embedding limit: {tokens}')
            meta = {
                'parent_chunk_id': cid, 'document_id': p['document_id'],
                'document_version': p['version'], 'title': p['title'],
                'section_title': p['section_title'], 'source_url': p['source_url'],
                'source_type': m.get('source_type', Path(p['path']).parent.name),
                'source_path': p['path'], 'review_status': m.get('review_status', 'draft'),
                'collected_at': m.get('collected_at', ''), 'effective_from': m.get('effective_from') or '',
                'effective_to': m.get('effective_to') or '',
                'source_pages_json': json.dumps(m.get('source_pages', [])),
                'char_start': a, 'char_end': b, 'chunk_index': n, 'chunk_count': len(ranges),
                'token_count': tokens, 'quality_ok': not bool(m.get('extraction_quality_flags')),
                'table_review_required': bool(m.get('table_review_required', False)),
                'related_item_ids_json': json.dumps(linked[cid]),
            }
            for item_id in linked[cid]:
                meta['topic_' + item_id] = True
            evidence.append({'id': f'{cid}:{p["version"]}:{a}-{b}', 'text': text, 'meta': meta})
    return tasks, evidence, max_tokens


class RetrievalStore:
    def __init__(self, repo: Path, runtime: Path, model_cache: Path, config: dict):
        import chromadb
        from chromadb.config import Settings
        self.repo, self.runtime, self.config = repo, runtime, config
        self.topics, self.parents = load_data(repo)
        self.engine = Embedder(config, runtime, model_cache)
        self.client = chromadb.PersistentClient(path=str(runtime / 'chroma'),
                                                settings=Settings(anonymized_telemetry=False))
        self.collections = {}
        for name in [config['topic_collection'], config['evidence_collection']]:
            collection = self.client.get_or_create_collection(
                name=name, embedding_function=None,
                metadata={'owner': 'telecom-guide-rag', 'embedding_signature': self.engine.signature},
                configuration={'hnsw': {'space': 'cosine'}},
            )
            if collection.metadata.get('owner') != 'telecom-guide-rag':
                raise ValueError('Refusing to change a collection owned by another project')
            if collection.metadata.get('embedding_signature') != self.engine.signature:
                raise ValueError('Embedding model mismatch: use a separate runtime directory')
            self.collections[name] = collection

    def fingerprint(self) -> str:
        source_state = {cid: {'version': p['version'], 'url': p['source_url'], 'meta': p['meta']}
                        for cid, p in self.parents.items()}
        return digest(json.dumps({'topics': self.topics, 'sources': source_state,
                                  'config': self.config}, ensure_ascii=False, sort_keys=True))

    def check_index(self):
        path = self.runtime / 'build_manifest.json'
        if not path.exists():
            raise ValueError('No completed index: run index first')
        manifest = json.loads(path.read_text(encoding='utf-8'))
        if manifest.get('data_fingerprint') != self.fingerprint():
            raise ValueError('Topic/source/config changed: rerun index before searching')
        if manifest.get('embedding_artifact_sha256') != self.engine.model_hash:
            raise ValueError('Embedding artifact changed: use a new runtime directory')

    def index(self) -> dict:
        tasks, docs, max_tokens = build_records(self.topics, self.parents, self.config, self.engine)
        stats = {}
        for name, records in [(self.config['topic_collection'], tasks),
                              (self.config['evidence_collection'], docs)]:
            collection = self.collections[name]
            previous = set(collection.get(include=[])['ids'])
            current = {r['id'] for r in records}
            vectors = self.engine.embed([r['text'] for r in records], 'passage')
            for start in range(0, len(records), 128):
                batch = records[start:start+128]
                collection.upsert(ids=[r['id'] for r in batch],
                                  documents=[r['text'] for r in batch],
                                  metadatas=[r['meta'] for r in batch],
                                  embeddings=vectors[start:start+128])
            # Synchronize only this project's known collection, never filesystem paths.
            stale = sorted(previous - current)
            for start in range(0, len(stale), 128):
                collection.delete(ids=stale[start:start+128])
            stats[name] = {'records': collection.count(), 'removed_stale_records': len(stale)}
        stats.update({'original_chunks': len(self.parents), 'max_evidence_input_tokens': max_tokens,
                      'embeddings_computed': self.engine.computed, 'embedding_cache_hits': self.engine.hits,
                      'config': self.config, 'embedding_signature': self.engine.signature,
                      'embedding_artifact_sha256': self.engine.model_hash,
                      'data_fingerprint': self.fingerprint()})
        (self.runtime / 'build_manifest.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
        return stats

    def search_topics(self, question: str, k: int | None = None, strategy: str = 'single') -> list[dict]:
        self.last_semantic_plan = None
        if strategy == 'semantic':
            from .semantic_plan import SemanticPlanner
            self.last_semantic_plan = SemanticPlanner(self.repo, cache_dir=self.runtime/'semantic_plans').plan(question)
            return self.search_topics_by_queries(self.last_semantic_plan['queries'], k)
        if strategy == 'clauses':
            return self.search_topics_by_clauses(question, k)
        if strategy != 'single':
            raise ValueError('Unknown search strategy: ' + strategy)
        self.check_index()
        collection = self.collections[self.config['topic_collection']]
        if not collection.count():
            raise ValueError('Index is empty: run index first')
        vectors = self.engine.embed([question], 'query')
        r = collection.query(query_embeddings=vectors, n_results=min(k or self.config['topic_top_k'], collection.count()),
                             include=['metadatas', 'distances'])
        return [{'item_id': id, 'name': m['name'], 'distance': d,
                 'evidence_status': m['evidence_status']} for id, m, d in
                zip(r['ids'][0], r['metadatas'][0], r['distances'][0])]

    def search_topics_by_clauses(self, question: str, k: int | None = None) -> list[dict]:
        from .query_expansion import query_plan
        return self.search_topics_by_queries(query_plan(question), k)

    def search_topics_by_queries(self, plan: list[dict], k: int | None = None) -> list[dict]:
        from .query_expansion import fuse_candidates
        self.check_index()
        collection = self.collections[self.config['topic_collection']]
        vectors = self.engine.embed([q['text'] for q in plan], 'query')
        count = min(k or self.config['topic_top_k'], collection.count())
        result = collection.query(query_embeddings=vectors, n_results=count,
                                  include=['metadatas', 'distances'])
        groups = []
        for ids, metadata, distances in zip(result['ids'], result['metadatas'], result['distances']):
            groups.append([{'item_id': id, 'name': meta['name'], 'distance': distance,
                            'evidence_status': meta['evidence_status']} for id, meta, distance in
                           zip(ids, metadata, distances)])
        return fuse_candidates(groups, plan, count)

    def retrieve(self, question: str, selected_ids: list[str] | None = None, strategy: str = 'single', evidence_mode: str | None = None) -> dict:
        from .query_expansion import query_plan
        ranked = self.search_topics(question, strategy=strategy)
        automatic = selected_ids is None
        selected_ids = list(dict.fromkeys(selected_ids if selected_ids is not None else
                                         [r['item_id'] for r in ranked[:self.config['selected_topic_count']]]))
        if not selected_ids or any(id not in self.topics for id in selected_ids):
            raise ValueError('Select one or more known topic IDs')
        metadata = [self.topics[id] for id in selected_ids]
        representatives = list(dict.fromkeys(cid for t in metadata for cid in t['primary_chunk_ids']))
        collection = self.collections[self.config['evidence_collection']]
        candidates, warnings = {}, []
        query_vec = self.engine.embed([question], 'query')
        flags = [{'topic_'+id: True} for id in selected_ids]
        where = {'$and': [{'quality_ok': True}, flags[0] if len(flags)==1 else {'$or':flags}]}
        if any(t['related_chunk_ids'] for t in metadata):
            mode = evidence_mode or self.config.get('evidence_search_mode','similarity')
            if mode not in {'similarity','mmr'}:
                raise ValueError('Unknown evidence search mode')
            fetch_k = max(self.config['evidence_top_k'], self.config.get('mmr_fetch_k',24)) if mode=='mmr' else self.config['evidence_top_k']
            result = collection.query(query_embeddings=query_vec, where=where,
                                      n_results=fetch_k, include=['metadatas','distances']+(['embeddings'] if mode=='mmr' else []))
            indices = list(range(len(result['ids'][0])))
            if mode=='mmr':
                from .ranking import mmr_indices
                indices = mmr_indices(query_vec[0],result['embeddings'][0],self.config['evidence_top_k'],self.config.get('mmr_lambda',0.65))
            for index in indices:
                record_id, meta, distance = result['ids'][0][index], result['metadatas'][0][index], result['distances'][0][index]
                cid = meta['parent_chunk_id']
                if cid not in self.parents:  # Live chunks are TTL-filtered separately.
                    continue
                if cid not in candidates:
                    candidates[cid] = {'distance': distance, 'matched_search_record': record_id,
                                       'matched_char_range': [meta['char_start'],meta['char_end']]}
        # Representatives are included independently of ranking and query length.
        ordered = representatives + [cid for cid in candidates if cid not in representatives]
        evidence = []
        for cid in ordered:
            p = self.parents[cid]
            if p['meta'].get('extraction_quality_flags'):
                warnings.append({'kind':'quarantined_source','parent_chunk_id':cid}); continue
            evidence.append({'parent_chunk_id': cid, 'document_id': p['document_id'],
                             'document_version':p['version'], 'title':p['title'],
                             'section_title':p['section_title'], 'source_url':p['source_url'],
                             'source_path':p['path'], 'text':p['body'],
                             'source_pages':p['meta'].get('source_pages',[]),
                             'role':'representative' if cid in representatives else 'retrieved',
                             'related_item_ids':[id for id in selected_ids if cid in self.topics[id]['related_chunk_ids']],
                             **candidates.get(cid,{})})
        for t in metadata:
            if t['evidence_status'] in {'missing','partial'}:
                warnings.append({'kind':'evidence_'+t['evidence_status'],'item_id':t['item_id'],
                                 'notes':t['review_notes'],'external_lookup_topics':t['external_lookup_topics']})
        return {'question':question,'search_strategy':strategy,'evidence_mode':evidence_mode or self.config.get('evidence_search_mode','similarity'),
                'query_plan':(self.last_semantic_plan['queries'] if strategy=='semantic' else query_plan(question) if strategy=='clauses' else [{'text':question,'kind':'whole','start':0,'end':len(question)}]),
                'semantic_plan':self.last_semantic_plan if strategy=='semantic' else None,
                'topic_candidates':ranked,'selected_item_ids':selected_ids,
                'selection_mode':'provisional_top_k' if automatic else 'explicit',
                'selection_is_confirmed':not automatic,
                'topic_metadata':metadata,'evidence':evidence,'warnings':warnings,
                'answer_generated':False,
                'note':'검색 결과입니다. 주제 메타데이터는 탐색 정보이며 공식 정책 근거가 아닙니다.'}
