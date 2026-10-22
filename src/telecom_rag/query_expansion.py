"""Surface clause splitting for retrieval experiments; no policy inference."""
import re
from collections import defaultdict

# General connective endings, not topic IDs or telecom-policy rules.
_BOUNDARY = re.compile(r'(?<!\d)[.!?。;]\s*|\n+|(?:그리고|또한|한편)\s+|(?:하면서|하되|바꾸되|하거나|거나|했는데|인데|하며|하고|바꾸고|넘기고|끝났고|빼고)\s+')


def query_plan(question, max_clauses=4):
    if max_clauses<1:
        raise ValueError('max_clauses must be positive')
    ranges=[];start=0
    for match in _BOUNDARY.finditer(question):
        stop=match.end()
        if question[start:stop].strip():ranges.append((start,stop))
        start=stop
    if question[start:].strip():ranges.append((start,len(question)))
    if len(ranges)>max_clauses:
        ranges=ranges[:max_clauses-1]+[(ranges[max_clauses-1][0],ranges[-1][1])]
    queries=[{'text':question,'start':0,'end':len(question),'kind':'whole'}]
    if len(ranges)<2:return queries
    for a,b in ranges:
        value=question[a:b];left=len(value)-len(value.lstrip());right=len(value.rstrip())
        a+=left;b=a+(right-left)
        fragment=question[a:b]
        if len(re.sub(r'\s','',fragment))<6 or fragment==question:continue
        if fragment not in {q['text'] for q in queries}:
            queries.append({'text':fragment,'start':a,'end':b,'kind':'clause'})
    return queries


def fuse_candidates(groups, queries, k):
    """Keep the whole-query leader, then each clause's leader; fill using RRF."""
    scores=defaultdict(float);records={};leaders=[]
    for group_index,group in enumerate(groups):
        if group:
            leader=group[0]['item_id']
            if leader not in leaders:leaders.append(leader)
        for rank,row in enumerate(group,1):
            id=row['item_id'];scores[id]+=1.0/(60+rank)
            if id not in records:records[id]={**row,'matched_queries':[]}
            records[id]['distance']=min(records[id]['distance'],row['distance'])
            records[id]['matched_queries'].append({'query':queries[group_index]['text'],'rank':rank,'distance':row['distance']})
    rest=sorted(records,key=lambda id:(-scores[id],id))
    order=leaders+[id for id in rest if id not in leaders]
    return [{**records[id],'fusion_score':scores[id]} for id in order[:k]]
