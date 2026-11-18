"""Offline batch gallery with pinned real captures, failures and separate rights counts."""
import html
import os
from pathlib import Path
from library import ROOT,read,write,sha,summarize

def esc(x):return html.escape(str(x),quote=True)
def rel(p):return os.path.relpath(p,ROOT).replace('\\','/')
def link(p,label):return '<a href="'+esc(rel(p))+'">'+esc(label)+'</a>'
def main():
    records=read(ROOT/'registry/assets.json')['assets'];status=summarize(records);write(ROOT/'reports/status.json',status)
    parts=['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Blendkit 資產擴充</title><style>body{font:16px system-ui;margin:24px;background:#15202b;color:#edf3f7}a{color:#9bd6ff}img{width:100%}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}article{padding:16px;background:#233344}table{border-collapse:collapse}td,th{border:1px solid #789;padding:8px}p{line-height:1.7}</style><h1>飯店資產擴充：Cumulative batches</h1>']
    parts.append('<p>'+link(ROOT/'comparison.html','V1.0 / V0.2 / 首個真實資產比較')+' · '+link(ROOT/'registry/assets.json','資產登錄')+' · '+link(ROOT/'reports/status.json','完整統計')+'</p>')
    names={'candidates':'候選來源','acquired':'已取得','converted':'已轉換','local_technical_ready':'本機端到端驗收','generation_ready':'GENERATION_READY','public_starter':'公開 Starter','rights_clear_internal_acquired':'本機測試權利已記錄','verified_cc0_acquired':'已取得且來源標示 CC0'}
    parts.append('<table>'+''.join('<tr><th>'+label+'</th><td>'+str(status[key])+'</td></tr>' for key,label in names.items())+'</table>')
    parts.append('<p>目標 10 → 25 → 50 → 75+ → 約 125。本機驗收與可抽取 USD／公開再散布資格分開。所有資產保留 STATIC_ONLY；沒有動態、柔性形變或操作資格。</p>')
    cases=[];receipts=[]
    first=ROOT/'runs/real_backpack_hotel705_stayover_high_706_a002'
    if (first/'case_index.json').exists():cases.append((read(first/'case_index.json'),ROOT/'reports/native_real_backpack_a001',first/'native_render/case-0'))
    for config,room_root,preview_roots in [
        ('batch_001_cases.json','batch001_scene_render_a000',['batch001_native_previews_a000']),
        ('batch001c_cases.json','batch001c_scene_render_a000',['batch001b_native_previews_a000','batch001c_native_previews_a000']),
        ('batch001d_cases.json','batch001d_scene_render_a000',['batch001d_native_previews_a000']),
        ('batch002a_cases.json','batch002a_scene_render_a000',['batch002a_native_previews_a000']),
        ('batch003a_cases.json','batch003a_scene_render_a000',['batch003a_native_previews_a000']),
        ('batch003b_cases.json','batch003b_scene_render_a000',['batch003b_native_previews_a000']),
        ('batch004a_cases.json','batch004a_scene_render_a000',['batch004a_native_previews_a000'])]:
        config_path=ROOT/'config'/config
        if not config_path.exists():continue
        for i,case in enumerate(read(config_path)['cases']):
            preview=next((ROOT/'reports'/p/case['asset_id'] for p in preview_roots if (ROOT/'reports'/p/case['asset_id']/'render.json').exists()),None)
            if preview is not None:cases.append((case,preview,ROOT/'runs'/room_root/('case-'+str(i))))
    cases=list({row[0]['asset_id']:row for row in cases}.values())
    for case,preview,room in cases:
        a=next(x for x in records if x['asset_id']==case['asset_id'])
        parts.append('<h2>'+esc(a['name'])+'</h2><p>'+esc(a['category'])+' / '+esc(a['rights']['license'])+' / '+esc(a['quality_decision'])+' / '+esc(a['robotics_relevance'])+'</p>')
        review=preview/'visual_review.json'
        if not review.exists() and a.get('evidence',{}).get('visual'):review=ROOT/a['evidence']['visual']['path']
        parts.append('<p>'+esc(a['quality_reason'])+'</p><p>'+link(Path(case['scene']),'場景 USD')+' · '+link(Path(case['manifest']),'Manifest')+' · '+(link(review,'實際視覺審查') if review.exists() else '待視覺審查')+'</p><div class="grid">')
        for report_path,prefix in [(preview/'render.json',ROOT),(room/'render.json',None)]:
            if not report_path.exists():continue
            report=read(report_path)
            if prefix is None:assert report['manifest_sha256']==sha(case['manifest']) and report['scene_sha256']==sha(case['scene'])
            for im in report['images']:
                pic=(prefix or report_path.parent)/im['path'];assert sha(pic)==im['sha256']
                parts.append('<article><p>'+esc(im.get('view',pic.stem))+'</p><a href="'+esc(rel(pic))+'"><img src="'+esc(rel(pic))+'" loading="lazy"></a></article>')
                receipts.append(dict(path=rel(pic),sha256=im['sha256']))
        parts.append('</div>')
    parts.append('<h2>淘汰與阻礙</h2><ul>')
    for a in records:
        if a['status']=='REJECTED':parts.append('<li>'+esc(a['name'])+'：'+esc(a.get('rejection_reason'))+'</li>')
    parts.append('</ul><p>拖鞋下載逾時的空目錄不計取得；已保存失敗紀錄，後續批次跳過該候選。原始來源與每次轉換、抽樣失敗紀錄保留。</p></html>')
    (ROOT/'batch_001.html').write_text('\n'.join(parts),encoding='utf-8')
    write(ROOT/'reports/batch001_gallery_receipt.json',dict(outcome='HASH_VERIFIED_REAL_CAPTURES',images=receipts,scope='Capture identity only; acceptance decisions in linked actual reviews'))
    print('BATCH_GALLERY_WRITTEN',len(receipts))

if __name__=='__main__':main()
