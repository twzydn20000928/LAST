"""Prepare official quality questions against the complete frozen video manifest."""
import argparse,copy,hashlib,json
from collections import defaultdict
from pathlib import Path
from .data import validate
from .upstream import verify

def verified_video(folder,record,reference=False):
    """Anchor quality inputs to existing generation or paired-fidelity evidence."""
    folder=Path(folder);label='reference' if reference else 'marked'
    video=folder/(label+'.mp4');actual=hashlib.sha256(video.read_bytes()).hexdigest()
    anchor=folder/'receipt.json'
    expected=record.get('reference_sha256') if reference else record.get('marked_sha256',record.get('video_sha256'))
    if reference and not expected:
        anchor=folder/'quality.json'
        if not anchor.is_file():raise ValueError('Reference lacks recorded provenance; audit before quality scoring')
        paired=json.loads(anchor.read_text())
        marked=hashlib.sha256((folder/'marked.mp4').read_bytes()).hexdigest()
        if paired.get('marked_sha256')!=marked or record.get('marked_sha256')!=marked:
            raise ValueError('Paired reference belongs to a different marked video')
        expected=paired.get('reference_sha256')
    if not expected or actual!=expected:raise ValueError('Quality video changed or lacks recorded provenance')
    return actual,dict(kind='paired_fidelity' if anchor.name=='quality.json' else 'generation',
                       receipt_sha256=hashlib.sha256(anchor.read_bytes()).hexdigest())


def build(manifest,metadata_root,run_root,family,mode,method):
    validate(manifest);groups=defaultdict(list)
    for row in manifest['samples']:groups[(row['dimension'],row['prompt'])].append(row)
    output=defaultdict(list);coverage=defaultdict(lambda:dict(expected=0,available=0,missing=[]));sources={};videos=[]
    for (dimension,prompt),rows in groups.items():
        text=Path(metadata_root)/'prompt_set/VBench2_aug_prompt'/f'{dimension}.txt'
        meta=Path(metadata_root)/'prompt_set/meta_info'/f'{dimension}.json'
        prompts=text.read_text().splitlines();matches=[i for i,s in enumerate(prompts) if s.strip()==prompt.strip()]
        if len(matches)!=1:raise ValueError('Official prompt must match exactly one auxiliary metadata row')
        questions=json.loads(meta.read_text());item=copy.deepcopy(questions[matches[0]])
        item.update(prompt_en=prompt,dimension=[dimension],video_list=[])
        for path in (text,meta):sources[str(path.relative_to(metadata_root))]=hashlib.sha256(path.read_bytes()).hexdigest()
        for row in sorted(rows,key=lambda r:r['replicate']):
            coverage[dimension]['expected']+=1
            source_method='last' if method=='reference' else method
            folder=Path(run_root)/family/mode/source_method/row['id']
            video=folder/('reference.mp4' if method=='reference' else 'marked.mp4');receipt=folder/'receipt.json'
            record=json.loads(receipt.read_text()) if receipt.exists() else {}
            valid=record.get('status') in ('completed','completed_generation_only') and record.get('family')==family and record.get('mode')==mode and record.get('method')==source_method
            if not video.is_file() or not valid:
                coverage[dimension]['missing'].append(row['id']);continue
            video_sha,anchor=verified_video(folder,record,method=='reference')
            item['video_list'].append(str(video.resolve()));coverage[dimension]['available']+=1
            videos.append(dict(video_id=row['id'],path=str(video.resolve()),sha256=video_sha,provenance=anchor))
        if item['video_list']:output[dimension].append(item)
    complete=all(v['expected']==v['available'] for v in coverage.values())
    return dict(output),dict(complete=complete,coverage=dict(coverage),metadata_sha256=sources,videos=videos,family=family,mode=mode,method=method)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','metadata-root','run-root','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--metadata-manifest',type=Path,default=Path('configs/quality_metadata_manifest.json'))
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True);p.add_argument('--mode',choices=['i2v','t2v'],required=True)
    p.add_argument('--method',choices=['reference','last','lfg','sigmark','videoshield','videomark'],required=True)
    p.add_argument('--allow-partial-diagnostic',action='store_true');a=p.parse_args()
    verify(a.metadata_root,json.loads(a.metadata_manifest.read_text()))
    files,report=build(json.loads(a.manifest.read_text()),a.metadata_root,a.run_root,a.family,a.mode,a.method)
    report['manifest_sha256']=hashlib.sha256(a.manifest.read_bytes()).hexdigest()
    report['scope']='Complete primary quality inputs' if report['complete'] else 'Incomplete inputs; no complete V-score claim'
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'coverage.json').write_text(json.dumps(report,indent=2))
    if not report['complete'] and not a.allow_partial_diagnostic:raise SystemExit('Incomplete quality inputs; coverage saved, scorer files withheld')
    for dimension,rows in files.items():(a.output/f'{dimension}.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(dict(complete=report['complete'],videos=len(report['videos']),dimension_files=len(files))))

if __name__=='__main__':main()
