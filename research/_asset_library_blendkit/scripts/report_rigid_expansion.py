"""Evidence-checked local cohort gallery; counts never inferred from download/render totals."""
from collections import Counter
from pathlib import Path
import html
from library import ROOT,read,write,sha,artifact_ok,gate_errors,summarize

def rel(path): return Path(path).resolve().relative_to(ROOT).as_posix()
def esc(value): return html.escape(str(value),quote=True)

def main():
    registry=read(ROOT/'registry/assets.json'); assets=registry['assets']
    status=summarize(assets); assert not status['invalid_ready']
    baseline=set(read(ROOT/'reports/expansion_verification.json')['local_accepted_asset_ids'])
    accepted=[a for a in assets if a.get('local_qualification',{}).get('outcome')=='PASS']
    assert baseline<={a['asset_id'] for a in accepted}
    for a in accepted:
        assert not gate_errors(a,scope='local'),a['asset_id']
        p=ROOT/a['local_qualification']['scene_manifest']['path']
        review=read(p.parents[2]/'scene_visual_review.json')
        assert review['outcome']=='PASS' and review['manifest_sha256']==sha(p)
        assert review['images'] and all(artifact_ok(im) for im in review['images'])
    protected=read(ROOT/'reports/protected_before.json')['files']
    assert all(Path(x['path']).is_file() and sha(x['path'])==x['sha256'] for x in protected)
    groups=[('rigid005006','rigid005006_scene_render_a000',
             ['rigid005_native_previews_a000','rigid006_native_previews_a000'])]
    if (ROOT/'reports/rigid008_local_qualification.json').exists():
        groups.append(('rigid008','rigid008_scene_render_a000',['rigid008_native_previews_a000']))
    for path in sorted((ROOT/'config').glob('rigid[0-9][0-9][0-9]_cases.json')):
        cohort=path.name.removesuffix('_cases.json')
        if cohort in {'rigid005','rigid006','rigid007','rigid008'}:continue
        if (ROOT/'reports'/(cohort+'_local_qualification.json')).exists():
            groups.append((cohort,cohort+'_scene_render_a000',[cohort+'_native_previews_a000']))
    rows=[];image_refs=[]
    for cohort,room,previews in groups:
        assert read(ROOT/'runs'/room/'process.json')['outcome']=='PASS'
        for index,case in enumerate(read(ROOT/'config'/(cohort+'_cases.json'))['cases']):
            a=next(a for a in assets if a['asset_id']==case['asset_id'])
            preview=next(ROOT/'reports'/name/a['asset_id'] for name in previews if (ROOT/'reports'/name/a['asset_id']/'visual_review.json').exists())
            native=read(preview/'render.json');visual=read(preview/'visual_review.json')
            room_report=ROOT/'runs'/room/('case-'+str(index))/'render.json'
            actual=read(room_report)
            assert actual['manifest_sha256']==sha(case['manifest']) and actual['scene_sha256']==sha(case['scene'])
            images=[]
            for record,prefix in [(native,ROOT),(actual,room_report.parent)]:
                for im in record['images']:
                    path=prefix/im['path']; assert sha(path)==im['sha256']
                    ref=dict(path=rel(path),sha256=im['sha256']);images.append(ref);image_refs.append(ref)
            rows.append(dict(asset_id=a['asset_id'],name=a['name'],category=a['category'],
                license=a['rights']['license'],source=a['source']['url'],author=a['author'],
                visual_outcome=visual['outcome'],observations=visual['observations'],
                local_accepted=a.get('local_qualification',{}).get('outcome')=='PASS',
                variant_of=a.get('variant_of'),
                geometry_family=a['geometry_family'],visual_family=a['visual_family'],
                dimensions_m=a['dimensions_m'],manifest=rel(case['manifest']),scene=rel(case['scene']),images=images))
    jobs=[j for path in sorted((ROOT/'config').glob('rigid[0-9][0-9][0-9]_jobs.json')) for j in read(path)['jobs']]
    queued_ids={'bk-'+j['base_id'] for j in jobs}
    attempted_ids={a['asset_id'] for a in assets if a['asset_id'] in queued_ids and (a.get('processing_job') or a.get('processing_failure'))}
    independent=[];seen_geometry=set()
    for a in accepted:
        if a.get('variant_of') or a['geometry_identity'] in seen_geometry:continue
        independent.append(a);seen_geometry.add(a['geometry_identity'])
    assert len(independent)==status['local_technical_ready']
    new=[a for a in independent if a['asset_id'] not in baseline]
    results=[]
    for a in assets:
        if a['asset_id'] not in attempted_ids:continue
        result=dict(asset_id=a['asset_id'],name=a['name'],quality=a['quality_decision'],reason=a['quality_reason'])
        if a.get('processing_failure'):
            result['last_retained_failure']=a['processing_failure']
            result['retained_failure_reason']=read(ROOT/a['processing_failure']['path'])['reason']
        results.append(result)
    report=dict(outcome='PASS_LOCAL_RIGID_EXPANSION_CHECKPOINT',status=status,baseline_local_accepted=len(baseline),
        added_local_accepted=len(new),new_asset_ids=[a['asset_id'] for a in new],attempted_sources=len(attempted_ids),queued_sources=len(queued_ids),
        new_category_distribution=dict(Counter(a['category'] for a in new)),
        new_license_distribution=dict(Counter(a['rights']['license'] for a in new)),
        new_geometry_families=len({a['geometry_family'] for a in new}),
        new_visual_families=len({a['visual_family'] for a in new}),
        new_dynamic_qualified=sum(a['physics']['mode']=='DYNAMIC_QUALIFIED' for a in new),
        new_rights_clear_local=sum(a['rights'].get('internal_use') is True for a in new),
        new_hotel_suitable=sum(a['hotel_suitability']['decision']=='accepted' for a in new),
        protected_files_checked=len(protected),assets=rows,processing_results=results,images=image_refs,
        next_official_query_config='config/batch_005_acquisition.json',
        scope='Controlled local technical pool. New assets are STATIC_ONLY; prior room dynamics do not qualify these new assets. Soft-object physics deferred. No publication or generator-rights inference.')
    write(ROOT/'reports/rigid_expansion_verification.json',report);write(ROOT/'reports/status.json',status)
    parts=['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>剛性物件資產擴充</title>',
      '<style>body{font:16px system-ui;margin:32px;background:#f3f7fc;color:#17304f}a{color:#1759a0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}img{width:100%;background:#ddd}article,section{background:white;padding:18px;margin:16px 0;border-radius:8px}td,th{padding:9px;border:1px solid #bbc9db}table{border-collapse:collapse}p{line-height:1.6}.blocked{color:#8b4600}</style>',
      '<h1>Hotel Room：剛性用品擴充</h1>',
      '<p>本機驗收 '+str(len(baseline))+' → <b>'+str(status['local_technical_ready'])+'</b>；本輪新增 '+str(len(new))+' 個。目標約 150 個不同模型。</p>',
      '<p>通過項目：真實來源、USD／材質依賴、Isaac 正反面與房間畫面、Static、Integrity、Native Support、Replay、候選 Catalog。新資產仍為 STATIC_ONLY，尚未取得新增物件的動態資格；軟體物件物理暫緩。授權另行管理，未公開第三方資產。</p>',
      '<p><a href="reports/rigid_expansion_verification.json">完整驗收與統計</a> · <a href="comparison.html">既有場景比較</a> · <a href="physics_comparison.html">既有全房間物理展示</a></p>',
      '<p>統計時間 UTC：'+esc(status['updated_utc'])+'。下載數與轉換數不代表驗收通過數。</p>',
      '<table>'+''.join('<tr><th>'+esc(k)+'</th><td>'+str(status[k])+'</td></tr>' for k in ('candidates','acquired','converted','local_technical_ready','local_qualified_variants','generation_ready','public_starter'))+'</table>']
    for a in rows:
        label=('本機驗收通過（外觀變體，不計入獨立數）' if a.get('variant_of') else '本機驗收通過') if a['local_accepted'] else esc(a['visual_outcome'])
        parts.append('<section><h2>'+esc(a['name'])+' — '+label+'</h2><p>'+esc(a['category'])+' / '+esc(a['license'])+' / '+esc(a['author'])+' · <a href="'+esc(a['source'])+'">官方原始來源</a></p>')
        parts.append('<p>'+esc('; '.join(a['observations']))+'</p><p><a href="'+esc(a['scene'])+'">場景 USD</a> · <a href="'+esc(a['manifest'])+'">Manifest</a></p><div class="grid">')
        for im in a['images']:parts.append('<a href="'+esc(im['path'])+'"><img loading="lazy" src="'+esc(im['path'])+'"></a>')
        parts.append('</div></section>')
    parts.append('<h2>未通過／待處理</h2>')
    for a in results:
        if a['quality']!='accepted':parts.append('<p class="blocked">'+esc(a['name'])+'：'+esc(a['reason'])+' '+esc(a.get('retained_failure_reason',''))+'</p>')
    (ROOT/'rigid_expansion.html').write_text('\n'.join(parts)+'</html>',encoding='utf-8')
    print('RIGID_EXPANSION_VERIFIED',dict(added=len(new),local_total=status['local_technical_ready'],images=len(image_refs),protected=len(protected)))

if __name__=='__main__': main()
