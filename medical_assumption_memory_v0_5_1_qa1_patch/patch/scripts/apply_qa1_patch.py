import argparse,json,shutil,re,os
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('target');a=ap.parse_args();target=Path(a.target).resolve();patch=Path(__file__).resolve().parents[1]
if not target.exists():raise SystemExit('Target package does not exist')
# Copy overlay resources.
for rel in ['public/terminology_v0_5_1_qa1.json','config/extraction_policy.json','config/retry_policy.json','config/call_status_taxonomy.json','scripts/qa_core.py','scripts/qa_runner.py']:
    src=patch/rel;dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
# Add canonical labels to public world specification without changing condition IDs.
world=target/'public/world_specification.json'
if world.exists():
    d=json.load(open(world));d['paper_aligned_condition_names']={'B0_LLM_ALONE':'Raw longitudinal evidence','M0_OPEN_LOOP_MEMORY':'Pre-specified consequence mapping','B1_VERIFIED_MEMORY':'Cognitive memory'};json.dump(d,open(world,'w'),indent=2)
# Portable checksum manifest, relative to package root.
manifest=target/'validation/SHA256SUMS.txt';manifest.parent.mkdir(exist_ok=True)
import hashlib
rows=[]
for p in sorted(target.rglob('*')):
    if p.is_file() and p!=manifest:
        rows.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(target).as_posix())
manifest.write_text('\n'.join(rows)+'\n')
print(json.dumps({'status':'PATCHED','target':str(target),'files':len(rows)},indent=2))
