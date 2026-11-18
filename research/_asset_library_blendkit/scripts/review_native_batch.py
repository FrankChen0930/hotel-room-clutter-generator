"""Persist explicit manual native image decisions and source-family judgments."""
import argparse
from library import ROOT,read,write,sha,artifact_ok
from hotel_metadata import enrich

def main():
    p=argparse.ArgumentParser();p.add_argument('--previews',required=True);p.add_argument('--decisions',required=True);args=p.parse_args()
    registry=read(ROOT/'registry/assets.json')
    for decision in read(args.decisions)['decisions']:
        aid=decision['asset_id'];folder=ROOT/args.previews/aid;native=read(folder/'render.json')
        assert native['outcome']=='PASS' and len(native['images'])==2 and all(artifact_ok(x) for x in native['images'])
        report=dict(outcome=decision['outcome'],usd_sha256=native['usd_sha256'],reviewer='Codex inspection of actual native front and back PNGs',
            images=native['images'],observations=decision['observations'],scope='Room-scale appearance only; no dynamics/deformation or manipulation qualification')
        path=folder/'visual_review.json'
        if path.exists():assert read(path)==report
        else:write(path,report)
        a=next(x for x in registry['assets'] if x['asset_id']==aid)
        a['visual_review']=dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
        if decision['outcome']=='PASS':
            a['appearance_family']=decision['appearance_family'];a['geometry_family']=decision['geometry_family']
            a['discovery_quality']['visual_acceptance']='ACCEPTED_LOCAL_PREVIEW'
        elif decision['outcome']=='BLOCKED':a.update(status='BLOCKED',blockers=['ACTUAL_NATIVE_REVIEW_REQUIRES_CORRECTION'])
        elif decision['outcome']=='REJECTED':a.update(status='REJECTED',rejection_reason='; '.join(decision['observations']))
        else:raise ValueError('EXPLICIT_VISUAL_DECISION_REQUIRED')
        enrich(a)
        if decision['outcome']=='BLOCKED':a['quality_reason']='; '.join(decision['observations'])
    write(ROOT/'registry/assets.json',registry);print('EXPLICIT_NATIVE_REVIEWS_RECORDED')

if __name__=='__main__':main()
