"""Conservative offline post-acquisition semantics; no acquisition or quality promotion."""
from library import ROOT,read,write
from batch_selection import semantic_rejection
from hotel_metadata import enrich

def main():
    registry=read(ROOT/'registry/assets.json');rejected=[]
    for a in registry['assets']:
        if not a.get('batch_id','').startswith('batch_') or not a['source'].get('version_id') or a['status']=='REJECTED' or a.get('local_qualification',{}).get('outcome')=='PASS':continue
        reason=semantic_rejection(a['name'],a['category'])
        if reason:
            a.update(status='REJECTED',rejection_reason='Post-acquisition hotel semantic review: '+reason+'; '+a['name'],blockers=['HOTEL_SCENARIO_UNSUITABLE_OR_AMBIGUOUS'])
            enrich(a);rejected.append(dict(asset_id=a['asset_id'],name=a['name'],reason=reason))
    write(ROOT/'registry/assets.json',registry)
    write(ROOT/'reports/acquired_semantic_audit_latest.json',dict(new_rejections=rejected,scope='No visual or geometry acceptance inferred for survivors'))
    print('ACQUIRED_SEMANTIC_AUDIT',len(rejected),'new rejects')

if __name__=='__main__':main()
