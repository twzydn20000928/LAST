"""Post-hoc alignment diagnostics; true maps never enter blind selection here."""
import argparse,json
from pathlib import Path
from .feature_cache import load,sha


def evaluate(nodes,mapping,selected):
    if any(type(i) is not int or not -1<=i<=64 for i in mapping):raise ValueError('Invalid source-frame map')
    truth=[]
    for node in nodes:
        indices=node['indices']
        if len(indices)!=4 or any(type(i) is not int or not 0<=i<len(mapping) for i in indices):
            raise ValueError('Expected four valid received-frame indices')
        ids=[mapping[i] for i in indices];group=None
        if ids[0]>=1 and (ids[0]-1)%4==0:
            g=(ids[0]-1)//4
            if ids==list(range(1+4*g,5+4*g)):group=g
        truth.append(group)
    seen=set();groups=set();rows=[]
    for item in selected:
        i=item['candidate'];g=item['group']
        if type(i) is not int or not 0<=i<len(nodes) or type(g) is not int or not 0<=g<16:
            raise ValueError('Invalid selected candidate/group')
        if i in seen or g in groups:raise ValueError('Duplicate selected candidate or group')
        seen.add(i);groups.add(g)
        rows.append(dict(candidate=i,predicted_group=g,true_group=truth[i],
                         intact=truth[i] is not None,correct=truth[i]==g))
    intact=sum(r['intact'] for r in rows);correct=sum(r['correct'] for r in rows)
    available={g for g in truth if g is not None}
    recovered={r['true_group'] for r in rows if r['correct']}
    return dict(selected=len(rows),correct=correct,intact_selected=intact,false_window_selected=len(rows)-intact,
                wrong_group_on_intact=intact-correct,
                selected_alignment_accuracy=correct/len(rows) if rows else None,
                intact_only_group_accuracy=correct/intact if intact else None,
                available_intact_groups=len(available),correctly_recovered_groups=len(recovered),
                intact_group_coverage=len(recovered)/len(available) if available else None,
                rows=rows,definition='Selected accuracy includes non-intact windows as errors; intact-only accuracy and group coverage reported separately',
                scope='Post-hoc alignment diagnostic, not message recovery or authentication')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('video','cache','extraction','attack-receipt','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();_,nodes,features=load(a.cache,a.video)
    receipt=json.loads((a.extraction/'receipt.json').read_text())
    if receipt.get('status')!='completed' or receipt.get('blind') is not True:raise ValueError('Require completed blind controlled extraction')
    for path in (a.video,a.cache/'receipt.json',a.cache/'nodes.json',a.cache/'features.npy'):
        if receipt['input_sha256'].get(str(path.resolve()))!=sha(path):raise ValueError('Extraction uses another video or cache')
    attack=json.loads(a.attack_receipt.read_text())
    if attack.get('status')!='completed' or attack.get('received_sha256')!=sha(a.video):raise ValueError('Attack map is not bound to received video')
    mapping=attack['attack_map']
    if mapping is None:
        if features['frames']!=65:raise ValueError('Missing map for changed-length input')
        mapping=list(range(65))
    if len(mapping)!=features['frames']:raise ValueError('Map length differs from cached video')
    inputs={str(path.resolve()):sha(path) for path in (a.video,a.cache/'receipt.json',a.cache/'nodes.json',a.cache/'features.npy',a.extraction/'receipt.json',a.attack_receipt)}
    result=evaluate(nodes,mapping,receipt['selection']['selected'])
    if any(sha(Path(path))!=h for path,h in inputs.items()):raise ValueError('Inputs changed during evaluation')
    result.update(input_sha256=inputs,reader=receipt['reader'],source_sha256=sha(Path(__file__)))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
