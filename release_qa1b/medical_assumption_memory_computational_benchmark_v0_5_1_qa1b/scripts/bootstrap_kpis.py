import argparse,json,random,csv
from pathlib import Path
from sklearn.metrics import f1_score
ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--output',required=True);ap.add_argument('--replicates',type=int,default=10000);ap.add_argument('--seed',type=int,default=13082644);a=ap.parse_args();R=Path(__file__).resolve().parents[1]
rows=[json.loads(x) for x in open(Path(a.run)/'scoring_records.jsonl')];ctx={x['context_id']:x for x in csv.DictReader(open(R/'data/current_contexts.csv'))};refs={x['context_id']:x for x in map(json.loads,open(R/'hidden/oracle_references.jsonl'))};rows=[x for x in rows if ctx[x['context_id']]['transform'] in ('BASE','SECONDARY')];eps=sorted({x['episode_id'] for x in rows});rng=random.Random(a.seed)
def f(q,c):
 z=[x for x in q if x['condition']==c];y=[refs[x['context_id']]['oracle_decision']['reaction'] for x in z];p=[x.get('parsed',{}).get('reaction','__INVALID__') for x in z];labs=sorted(set(y));return f1_score(y,p,labels=labs,average='macro',zero_division=0)
vals=[]
for _ in range(a.replicates):
 sample=[rng.choice(eps) for _ in eps];q=[]
 for e in sample:q += [x for x in rows if x['episode_id']==e]
 vals.append({'memory':f(q,'B1_VERIFIED_MEMORY')-f(q,'B0_LLM_ALONE'),'verification':f(q,'B1_VERIFIED_MEMORY')-f(q,'M0_OPEN_LOOP_MEMORY')})
def ci(k):
 v=sorted(x[k] for x in vals);return [v[int(.025*len(v))],v[min(len(v)-1,int(.975*len(v)))]]
out={'replicates':a.replicates,'seed':a.seed,'memory_95ci':ci('memory'),'verification_95ci':ci('verification')};Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
