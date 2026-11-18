"""Evidence-linked local degree comparison. Captures never imply visual approval."""
import argparse,html,os,json
from pathlib import Path
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--capture-dir',type=Path);p.add_argument('--html-output',type=Path,default=ROOT/'physics_comparison.html');a=p.parse_args();run=a.run.resolve();captures=a.capture_dir or run/'native_render';cases=read(run/'cases.json')['cases'];cards=[];summary=[]
    records={r['asset_id']:r for r in read(ROOT/'registry/assets.json')['assets']}
    permission=ROOT/'reports/hotel705_redistribution_permission_20261118.json'
    native_permitted={r['asset_id'] for r in read(ROOT/'artifacts/legacy_density_pool_a001/index.json') if r['source_kind']=='EXISTING_ROOM_NOT_NEW_BLENDKIT'} if permission.exists() and read(permission)['outcome']=='USER_CONFIRMED_PERMISSION' else set()
    views=['overview','floor_foot','bed_surface','pillow_left_detail','chair_seat'];labels=['全房間','地面與床尾','床面','枕頭','椅面']
    rel=lambda p:os.path.relpath(p,ROOT).replace('\\','/')
    for index,case in enumerate(cases):
        folder=Path(case['manifest']).parent;m=read(case['manifest']);r=read(folder/'physics_evidence.json');assert r['outcome']=='PASS'
        usage=[]
        categories={request['request_id']:request['category'] for request in m['requests']}
        for obj in m['objects']:
            asset=records.get(obj['asset_id'],{})
            usage.append(dict(instance_id=obj['instance_id'],asset_id=obj['asset_id'],name=asset.get('name',obj['asset_id']),category=categories[obj['request_id']],support_id=obj['effective']['support_id'],source_url=asset.get('source',{}).get('url'),author=asset.get('author'),version_id=asset.get('source',{}).get('version_id'),origin='BLENDKIT' if obj['asset_id'] in records else 'EXISTING_INTERNAL_PROP_NOT_NEW_BLENDKIT',license=asset.get('rights',{}).get('license','EXISTING_INTERNAL_ONLY'),rights=asset.get('rights',{}),physics_scope='EXPERIMENTAL_RIGID_SURROGATE_ONLY'))
            if obj['asset_id'] in native_permitted:
                usage[-1].update(origin='HOTEL705_ORIGINAL_ROOM_PROP_NOT_NEW_BLENDKIT',license='USER_CONFIRMED_AUTHOR_LAB_ROOM_PERMISSION',
                    source_url='https://github.com/yfan62858/hotel705-random-clutter/releases/tag/v1.0.0',
                    rights=dict(redistribution=True,decision='USER_CONFIRMED_ORIGINAL_ROOM_SCOPE_ONLY',permission_sha256=sha(permission),blanket_open_license=False))
        write(folder/'asset_usage.json',dict(instances=usage,unique_asset_ids=len({x['asset_id'] for x in usage}),unique_blendkit_ids=len({x['asset_id'] for x in usage if x['origin']=='BLENDKIT'}),category_counts=m['achieved']['category_counts'],surface_counts=case['surface_counts']))
        capture=captures/('case-'+str(index));record=read(capture/'render.json');images={}
        for im in record['images']:
            path=capture/im['path'];assert sha(path)==im['sha256'];images[im['view']]=rel(path)
        assert set(images)==set(views)
        row=dict(level=case['level'],seed=case['seed'],count=len(m['objects']),unique_asset_ids=case['unique_assets'],category_counts=m['achieved']['category_counts'],surface_counts=case['surface_counts'],physics=r['outcome'],registered_bodies=r['registered_dynamic_bodies'],native_steps=r['native_steps'],images=images,visual_review='CAPTURED_PENDING_REVIEW')
        review=folder/'visual_review.json'
        if review.exists():row['visual_review']=read(review)['outcome']
        summary.append(row)
        links=' | '.join('<a href="'+html.escape(rel(folder/name))+'">'+label+'</a>' for name,label in [('scene.usda','Preview USD'),('scene_dynamic.usda','Dynamic USD'),('manifest.json','Manifest'),('physics_evidence.json','Physics'),('native_support.json','Native Support'),('initial_static.json','Initial Static'),('integrity.json','Integrity'),('replay.json','Replay'),('asset_usage.json','Asset usage')])
        cards.append('<article data-images="'+html.escape(json.dumps(images),quote=True)+'"><h2>'+case['level'].title()+' · Seed '+str(case['seed'])+'</h2><p>'+str(len(m['objects']))+' 件／'+str(case['unique_assets'])+' 種來源；'+str(r['registered_dynamic_bodies'])+' 個動態剛體</p><a class="full" href="'+images['overview']+'"><img src="'+images['overview']+'"></a><p>30 秒／3,600 步：PASS；最後 2 秒穩定檢查：PASS</p><p>'+links+'</p><p>影像審查：'+row['visual_review']+'</p></article>')
    document='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Hotel705 · Physics guided density</title><style>body{background:#111827;color:#edf2f7;font:16px system-ui;margin:24px}a{color:#93c5fd}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px}article{background:#1f2937;padding:16px;border-radius:10px}img{width:100%}select{font:inherit;padding:8px}p{line-height:1.6}h2{font-size:20px}</style><h1>Hotel705 · 物理回饋生成比較</h1><p>Low 10–20；Medium 30–50；High 70–80。數量是實例，重複模型不算新資產。固定相機與原始光照；畫面位置來自實際模擬結果。</p><p>測試範圍：CPU PhysX、重力、全房間 49 個原始剛體與 31 個關節、所有生成物件。質量與剛性碰撞代理仍為研究估計，未認定已解決柔性變形或機器人操作。</p><p><a href="surface_comparison.html">先前靜態多表面比較</a> · <a href="comparison_before_measured_surfaces_a002.html">V1.0／V0.2 歷史比較</a> · <a href="https://physcensis.github.io/">PhyScensis 參考方法</a></p><label>同步視角：<select id="view">'''+''.join('<option value="'+v+'">'+l+'</option>' for v,l in zip(views,labels))+'''</select></label><main>'''+''.join(cards)+'''</main><script>document.getElementById('view').addEventListener('change',e=>{document.querySelectorAll('article[data-images]').forEach(card=>{const path=JSON.parse(card.dataset.images)[e.target.value];card.querySelector('img').src=path;card.querySelector('a.full').href=path;});});</script></html>'''
    assert a.html_output.resolve().parent==ROOT
    a.html_output.write_text(document,encoding='utf-8')
    write(run/'scene_quality_summary.json',dict(cases=summary,scope='Experimental local rigid surrogate validation, not flexible or manipulation qualification'))
    print('PHYSICS_COMPARISON',len(cases),sum(len(c['images']) for c in summary))

if __name__=='__main__':main()
