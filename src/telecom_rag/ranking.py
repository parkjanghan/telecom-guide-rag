"""Configurable diversity reranking; mandatory representative documents are handled separately."""
import numpy as np

def mmr_indices(query,vectors,k,weight=0.65):
    if not 0<=weight<=1:raise ValueError('mmr_weight_invalid')
    if k<=0 or not len(vectors):return []
    values=np.asarray(vectors,dtype=float);q=np.asarray(query,dtype=float)
    values=values/np.maximum(np.linalg.norm(values,axis=1,keepdims=True),1e-12)
    q=q/max(float(np.linalg.norm(q)),1e-12)
    relevance=values@q;chosen=[];remaining=set(range(len(values)))
    for _ in range(min(k,len(values))):
        def score(i):
            diversity=max(float(values[i]@values[j]) for j in chosen) if chosen else 0.
            return weight*float(relevance[i])-(1-weight)*diversity
        best=max(sorted(remaining),key=score);chosen.append(best);remaining.remove(best)
    return chosen
