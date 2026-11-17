"""Offline synchronized degree/seed comparison from unmodified actual native PNGs."""
import argparse,html,json,os,shutil
from pathlib import Path
from collections import Counter
from library import ROOT,read,write,sha

LABELS={'overview':'整房總覽','bed_surface':'主床表面','pillow_left_detail':'左枕頭','pillow_right_detail':'右枕頭','chair_seat':'椅面',
    'floor_foot':'床腳地面','floor_window':'窗邊地面','single_bed_clear':'單人床／坐臥墊','between_beds':'床間地面','entry_bench':'入口檯面'}
def rel(p):return os.path.relpath(p,ROOT).replace('\\','/')
def esc(s):return html.escape(str(s),quote=True)
def link(p,label):return '<a href="'+esc(rel(p))+'">'+esc(label)+'</a>'

def collect(run,index):
    images={}
    for folder,allowed in [('native_render',set(LABELS)),
        ('native_pillow_details',{'pillow_left_detail','pillow_right_detail'}),('native_local_clear',{'single_bed_clear','between_beds','floor_window'})]:
        if not (run/folder).exists() and folder!='native_render':continue
        assert read(run/folder/'process.json')['outcome']=='PASS'
        base=run/folder/('case-'+str(index));record=read(base/'render.json')
        for im in record['images']:
            if im['view'] not in allowed:continue
            p=base/im['path'];assert sha(p)==im['sha256']
            images[im['view']]=dict(path=rel(p),sha256=im['sha256'],camera=im['camera'])
    assert set(images)==set(LABELS)
    return images

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);args=p.parse_args();run=args.run.resolve()
    cases=read(run/'cases.json')['cases'];assets={a['asset_id']:a for a in read(ROOT/'registry/assets.json')['assets']};cards=[];receipts=[]
    for i,case in enumerate(cases):
        manifest=read(case['manifest']);images=collect(run,i);support=read(run/'native_support'/('case-'+str(i)+'.json'))
        assert support['outcome']=='PASS'
        for folder in ['native_render','native_pillow_details','native_local_clear']:
            if not (run/folder).exists():continue
            native=read(run/folder/('case-'+str(i))/'render.json')
            assert native['manifest_sha256']==sha(case['manifest']) and native['scene_sha256']==sha(case['scene'])
        objects=manifest['objects'];usage=[]
        for obj in objects:
            a=assets[obj['asset_id']];usage.append(dict(asset_id=a['asset_id'],name=a['name'],license=a['rights']['license'],source_url=a['source']['url'],
                geometry_family=a['geometry_family'],appearance_family=a['appearance_family'],support_id=obj['effective']['support_id'],state_id=obj['effective']['state_id']))
        summary=dict(level=case['level'],seed=case['seed'],added_objects=len(objects),unique_asset_ids=len({o['asset_id'] for o in objects}),
            appearance_families=len({a['appearance_family'] for a in usage}),support_distribution=dict(Counter(a['support_id'] for a in usage)),
            occupied_regions=len({a['support_id'] for a in usage}),native_queries=len(support['checks']),images=images,manifest=rel(case['manifest']),scene=rel(case['scene']))
        cards.append(summary);write(Path(case['manifest']).parent/'asset_usage.json',dict(assets=usage,**{k:v for k,v in summary.items() if k!='images'}))
        for view,im in images.items():receipts.append(dict(level=case['level'],seed=case['seed'],view=view,**im))
    for view in LABELS:assert len({json.dumps(c['images'][view]['camera'],sort_keys=True) for c in cards})==1,'CAMERA_CHANGED_BETWEEN_LEVELS'
    backup=ROOT/('comparison_before_'+run.name+'.html')
    if not backup.exists():shutil.copy2(ROOT/'comparison.html',backup)
    verification=run/'verification.json';status='已完成檢查' if verification.exists() and read(verification)['outcome']=='PASS' else '驗收證據整理中'
    parts=['''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Hotel 705｜多區域混亂程度比較</title>
<style>body{font:16px system-ui;margin:0;background:#101923;color:#eef3f8}main{max-width:1600px;margin:auto;padding:26px}a{color:#9cdaff}h1{font-size:30px}p{line-height:1.7}.tools{position:sticky;top:0;z-index:2;background:#101923ed;padding:16px 0;display:flex;flex-wrap:wrap;gap:8px}button{font:inherit;color:#eef3f8;background:#24374a;border:1px solid #55758e;border-radius:6px;padding:9px 13px;cursor:pointer}button.active{background:#186887}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}article{background:#1e2d3b;border:1px solid #3e566d;border-radius:10px;padding:16px;min-width:0}img{width:100%;display:block;border-radius:6px}.meta{font-size:14px;color:#bdd0df}.badge{color:#93e3bb}table{border-collapse:collapse;width:100%;margin:14px 0}th,td{border:1px solid #3e566d;padding:9px;text-align:left}code{overflow-wrap:anywhere}summary{cursor:pointer;padding:12px 0}@media(max-width:850px){.grid{grid-template-columns:1fr}}</style><main>
<h1>Hotel 705：更多放置區域 × 不同混亂程度</h1>
<p>STAYOVER · Seed 706／707 · Low／Medium／High。數量指額外生成的獨立資產；原場景內建備品與家具保留。主總覽相機、來源與光照一致，局部相機在全部程度與 Seed 間固定。</p>
<p>地面、主床、單人床、左右枕頭、椅面、桌面及檯面已納入候選放置。物件按語意、大小與量測曲面篩選，再依 Seed 取樣位置。</p>''']
    parts.append('<p class="badge">'+esc(status)+' · STATIC_ONLY · Static / Integrity / Replay / Native Triangle Support</p>')
    parts.append('<p>'+link(backup,'先前 V1.0／V0.2／資產庫整房對照')+' · '+link(ROOT/'batch_001.html','42 個已驗收資產')+' · '+link(run/'cases.json','全部場景 USD／Manifest 路徑')+' · '+link(verification,'完整驗證結果')+'</p>')
    parts.append('<div class="tools">'+''.join('<button data-view="'+v+'"'+(' class="active"' if v=='overview' else '')+'>'+label+'</button>' for v,label in LABELS.items())+'</div>')
    for seed in sorted({c['seed'] for c in cards}):
        parts.append('<h2>Seed '+str(seed)+'</h2><div class="grid">')
        for c in [c for c in cards if c['seed']==seed]:
            key=c['level']+'_'+str(seed);parts.append('<article><h3>'+esc(c['level'].capitalize())+' · '+str(c['added_objects'])+' 件</h3><p class="meta">'+str(c['unique_asset_ids'])+' 個獨立資產 · '+str(c['appearance_families'])+' 個外觀家族 · '+str(c['occupied_regions'])+' 處區域</p>')
            im=c['images']['overview']['path'];parts.append('<a class="capture" data-case="'+key+'" href="'+esc(im)+'"><img src="'+esc(im)+'" alt="'+esc(key)+' 整房總覽"></a>')
            parts.append('<p>'+link(ROOT/c['scene'],'場景 USD')+' · '+link(ROOT/c['manifest'],'Manifest')+' · '+link((ROOT/c['manifest']).parent/'asset_usage.json','使用清單')+'</p><details><summary>放置分布與檢查</summary><p>Native：'+str(c['native_queries'])+' 個支撐查詢</p><table>'+''.join('<tr><td>'+esc(k)+'</td><td>'+str(v)+'</td></tr>' for k,v in c['support_distribution'].items())+'</table></details></article>')
        parts.append('</div>')
    parts.append('<details><summary>品質、範圍與保留問題</summary><p>原始床品與枕頭的三角形表面提供實際支撐高度。曲面檢查採精確三角形最高點與密集高度取樣；Native 在未儲存的 session 中以原始三角網格驗證。這是靜態場景資格，柔性形變、動態穩定及機器人操作資格仍未解決。可抽取 USD 與公開再散布權利維持獨立限制。</p><p>圖片為 Isaac 實際渲染，保留原圖；單件與整體配置皆由產生器取樣。</p></details>')
    data={c['level']+'_'+str(c['seed']):c['images'] for c in cards}
    parts.append('<script>const captures='+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+''';document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('a.capture').forEach(a=>{const im=captures[a.dataset.case][b.dataset.view];a.href=im.path;a.querySelector('img').src=im.path;a.querySelector('img').alt=a.dataset.case+' '+b.textContent;});}));</script></main></html>''')
    payload='\n'.join(parts)
    for name in ['surface_comparison.html','comparison.html']:(ROOT/name).write_text(payload,encoding='utf-8')
    write(run/'comparison_index.json',dict(outcome='HASH_VERIFIED_ACTUAL_CAPTURES',cases=cards,images=receipts,previous_comparison=rel(backup),scope='Capture/paths only; actual visual decisions and final qualification recorded separately'))
    print('SURFACE_COMPARISON_WRITTEN',len(cards),len(receipts),'ACTUAL_IMAGES')

if __name__=='__main__':main()
