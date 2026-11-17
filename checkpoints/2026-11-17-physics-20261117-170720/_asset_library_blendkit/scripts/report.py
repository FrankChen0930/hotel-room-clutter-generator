"""Generate offline screening and comparison; never presents pending output as a render."""
import html
import os
from pathlib import Path
from library import ROOT, read, write, summarize, sha

def rel(path): return os.path.relpath(path,ROOT).replace('\\','/')
def link(path,label): return '<a href="'+html.escape(rel(path),quote=True)+'">'+html.escape(label)+'</a>'

def main():
    records=read(ROOT/'registry/assets.json')['assets']; status=summarize(records); write(ROOT/'reports/status.json',status)
    screened=[]
    for a in records:
        score=30 if a['category'] in {'bag','clothing','footwear','electronics'} else 20
        if a['source']['plan']=='FREE': score+=20
        if a['rights']['license']=='CC0': score+=40
        if a['status']=='REJECTED': score=-1
        screened.append(dict(asset_id=a['asset_id'],priority=score,status=a['status'],
            category=a['category'],license=a['rights']['license'],source=a['source']['url'],
            next_action='Exclude non-guest display scene' if a['status']=='REJECTED' else
            'Find CC0 alternative or clarify extractable USD rights; use official free UI when available',
            scope='Semantic/rights pre-screen only; no geometric or visual acceptance'))
    write(ROOT/'reports/screening.json',dict(candidates=sorted(screened,key=lambda x:-x['priority'])))
    local_scene=read(ROOT/'registry/latest_local_scene.json') if (ROOT/'registry/latest_local_scene.json').exists() else None
    scene_images={}
    if local_scene:
        scene_run=Path(local_scene['manifest']).parents[2]
        render_path=scene_run/'native_render/case-0/render.json'
        if render_path.is_file():
            rendered=read(render_path)
            if rendered['manifest_sha256']!=sha(local_scene['manifest']):raise ValueError('CANDIDATE_RENDER_MANIFEST_CHANGED')
            for im in rendered['images']:
                pic=render_path.parent/im['path']
                if sha(pic)!=im['sha256']:raise ValueError('CANDIDATE_IMAGE_CHANGED')
                scene_images[im['view']]=dict(path=pic,sha256=im['sha256'],camera=im['camera'])
    write(ROOT/'registry/candidate_catalog_queue.json',dict(schema_version='1.0',status='GENERATOR_RIGHTS_UNCLEARED',entries=[],
        local_scene=local_scene,scope='Generator-ready queue only. Actual controlled-local Common Core candidate is linked separately; no formal/public adoption.'))
    reference=ROOT.parent/'_common_core_runs/quality_experiments/scene_quality_v02_20261114T153126Z'
    index=read(reference/'comparison_index.json'); selected=[c for c in index['cases'] if c['version'] in ('v1_baseline','v4_bed')]
    parts=['''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Blendkit Asset Library — first batch</title><style>
body{font:16px system-ui;margin:24px;background:#101820;color:#e5edf5}a{color:#9cd4ff}p{line-height:1.7}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}article{background:#1e2c3a;padding:16px;border:1px solid #526879;border-radius:8px}img{width:100%}table{border-collapse:collapse;width:100%}td,th{border:1px solid #526879;padding:8px;text-align:left}.pending{color:#ffda94}@media(max-width:850px){.grid{grid-template-columns:1fr}}code{overflow-wrap:anywhere}</style>
<h1>Hotel Room Asset Library · Blendkit</h1><p>Hotel705 / STAYOVER / High / Seed 706。前兩欄引用既有 V0.2 比較中的歷史原生渲染；新候選沿用同一房間來源、光照及相機。本機技術資格與生成／公開授權分開管理。</p>''']
    parts.append('<p>'+link(ROOT/'reports/status.json','即時資格統計')+' · '+link(ROOT/'reports/screening.json','候選篩選')+' · '+link(ROOT/'registry/assets.json','資產登錄')+' · '+link(ROOT/'README.md','執行與限制')+'</p>')
    parts.append('<p>'+link(ROOT/'batch_001.html','Batch 1 expansion: real model previews, room captures, acceptance and rejections')+'</p>')
    receipts=[]
    for view in ('overview','floor_foot','floor_bedside','entry_bench','desk','bed'):
        parts.append('<h2>'+html.escape(view)+'</h2><div class="grid">')
        for c in selected:
            image=next(x for x in c['images'] if x['view']==view); pic=reference/image['uri']
            ok=pic.is_file() and sha(pic)==image['sha256']
            if not ok: raise ValueError('HISTORIC_IMAGE_IDENTITY_MISMATCH')
            parts.append('<article><h3>'+html.escape(c['label'])+'</h3><p>歷史圖片 · SHA 已核對</p><a href="'+html.escape(rel(pic),quote=True)+'"><img alt="'+html.escape(c['version']+' '+view,quote=True)+'" src="'+html.escape(rel(pic),quote=True)+'"></a>')
            parts.append('<p>'+str(c['count'])+' instances / '+str(c['unique_asset_ids'])+' Asset IDs / '+str(c['quality']['unique_appearance_groups'])+' appearance groups</p>')
            parts.append(link(Path(c['scene']),'USD')+' · '+link(Path(c['manifest']),'Manifest')+' · '+link(reference/'comparison_index.json','歷史驗證與使用清單')+'</article>')
            receipts.append(dict(version=c['version'],view=view,path=rel(pic),sha256=image['sha256'],camera=image['camera'],scope='HISTORICAL_REFERENCE'))
        if len(selected)==2:
            ca=[next(x for x in c['images'] if x['view']==view)['camera'] for c in selected]
            if ca[0]!=ca[1]: raise ValueError('HISTORIC_CAMERA_MISMATCH')
        parts.append('<article><h3>新 Asset Library · 本機候選</h3>')
        if local_scene:
            summary_path=Path(local_scene['manifest']).parents[2]/'scene_quality_summary.json'
            metrics=read(summary_path) if summary_path.is_file() else {}
            parts.append("<p>"+str(local_scene["count"])+" instances / "+str(metrics.get("generated_unique_asset_ids","pending"))+" Asset IDs / "+str(metrics.get("generated_appearance_families","pending"))+" appearance families; "+str(metrics.get("new_independent_blendkit_sources_used",1))+" real Blendkit sources; controlled local use</p>")
            if view in scene_images:
                im=scene_images[view];pic=im['path']
                expected=next(x for x in selected[-1]['images'] if x['view']==view)['camera']
                if im['camera']!=expected:raise ValueError('CANDIDATE_CAMERA_MISMATCH')
                parts.append('<a href="'+html.escape(rel(pic),quote=True)+'"><img alt="Real Blendkit local scene '+view+'" src="'+html.escape(rel(pic),quote=True)+'"></a>')
                receipts.append(dict(version='blendkit_local',view=view,path=rel(pic),sha256=im['sha256'],camera=im['camera'],scope='NEW_CONTROLLED_LOCAL_CANDIDATE'))
            else:parts.append('<p class="pending">此視角尚未擷取</p>')
            parts.append(link(Path(local_scene['scene']),'USD')+' · '+link(Path(local_scene['manifest']),'Manifest')+' · '+link(Path(local_scene['manifest']).parents[2]/'local_qualification.json','Static / Integrity / Replay / Native Support'))
        else:parts.append('<p class="pending">尚未生成；工程 Fixture 不作為模型展示。</p>')
        parts.append('</article></div>')
    for a in records:
        if a.get('local_qualification',{}).get('outcome')!='PASS':continue
        render_ref=a['evidence']['native_render'];asset_render=read(ROOT/render_ref['path'])
        parts.append('<h2>真實官方模型 · 本機技術驗收 PASS</h2><p>'+html.escape(a['name'])+' / '+html.escape(a['author'])+' / '+html.escape(a['rights']['license'])+' / STATIC_ONLY</p><div class="grid">')
        for im in asset_render['images']:
            pic=ROOT/im['path']
            if sha(pic)!=im['sha256']:raise ValueError('ASSET_PREVIEW_CHANGED')
            parts.append('<article><p>Isaac 原生資產預覽；與整房比較分開。</p><img alt="Real official asset preview" src="'+html.escape(rel(pic),quote=True)+'"></article>')
        parts.append('</div><p class="pending">生成工具可抽取 USD 與公開再散布權利仍未確認；不計入 GENERATION_READY 或 GitHub Starter。</p>')
    parts.append('<h2>來源初篩</h2><table><tr><th>名稱</th><th>類別</th><th>方案 / 授權</th><th>狀態</th></tr>')
    for a in records:
        parts.append('<tr><td><a href="'+html.escape(a['source']['url'],quote=True)+'">'+html.escape(a['name'])+'</a></td><td>'+a['category']+'</td><td>'+a['source']['plan']+' / '+a['rights']['license']+'</td><td>'+a['status']+'</td></tr>')
    parts.append('</table><p class="pending">'+html.escape(
        f"候選：{status['candidates']}（含淘汰 {status['status_counts'].get('REJECTED',0)}）；取得：{status['acquired']}；USD：{status['converted']}；本機技術驗收：{status['local_technical_ready']}；GENERATION_READY：{status['generation_ready']}；可公開 Starter：{status['public_starter']}。正式資格以各階段證據為準。")+'</p></html>')
    (ROOT/'comparison.html').write_text('\n'.join(parts),encoding='utf-8')
    write(ROOT/'reports/comparison_receipt.json',dict(outcome='VERIFIED_REFERENCE_AND_CONTROLLED_LOCAL_EVIDENCE',images=receipts,candidate_scene=local_scene))
    print('Comparison written:',ROOT/'comparison.html')

if __name__=='__main__':main()
