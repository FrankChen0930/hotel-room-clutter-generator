"""Record the actual two-view native visual inspection; no automatic image acceptance."""
from library import ROOT,read,write,sha

reviews={
'6d5257a4-4fdf-421d-92b9-e77f941f5187':('PASS','Corduroy backpack with plausible straps, seams and scan texture on both sides; source tint PBR approximation looks natural at room scale. Fixed form only.'),
'ffeb2aae-6c5a-423e-aba4-deda36270a9c':('PASS','Recognizable closed suitcase; worn leather, handle, clasps and seams resolve naturally in both native views. One of the two original variants only.'),
'2186f9d2-1f2c-4fae-b1b6-1faa23408adc':('REJECTED','Material exports correctly, but inflated worn-torso form is unsuitable as an unsupported floor/bedside garment. Requires a separately validated resting S0 form; no such form claimed.'),
'333ad1d5-11a6-4314-96be-7540cf9af35d':('PASS','Recognizable folded stack of trousers; photographic cloth detail and folds visible on both sides. One inseparable scan counts as one asset, not multiple trousers. Fixed form only.'),
'5d9b4bb2-bae5-4502-82d9-3095407b3e9a':('PASS','Recognizable single canvas shoe; sole, laces and stitched panels visible with complete textures. Some scan softness; suitable for room-scale clutter, not close-up manipulation geometry.')}

families={
'6d5257a4-4fdf-421d-92b9-e77f941f5187':('brown_corduroy_navy_pocket_backpack','upright_travel_backpack_scan'),
'ffeb2aae-6c5a-423e-aba4-deda36270a9c':('worn_olive_leather_suitcase','closed_hard_suitcase'),
'333ad1d5-11a6-4314-96be-7540cf9af35d':('mixed_denim_brown_folded_trousers_stack','folded_trousers_stack_fixed_scan'),
'5d9b4bb2-bae5-4502-82d9-3095407b3e9a':('navy_white_high_top_canvas_shoe','single_high_top_shoe_scan')}

if __name__=='__main__':
    registry=read(ROOT/'registry/assets.json')
    from hotel_metadata import enrich
    for base,(outcome,observation) in reviews.items():
        folder=ROOT/'reports/batch001_native_previews_a000'/('bk-'+base);native=read(folder/'render.json')
        assert native['outcome']=='PASS' and len(native['images'])==2
        for im in native['images']:assert sha(ROOT/im['path'])==im['sha256']
        path=folder/'visual_review.json'
        report=dict(outcome=outcome,usd_sha256=native['usd_sha256'],reviewer='Codex inspection of actual Isaac front.png and back.png',
            images=native['images'],observations=[observation],scope='Room-scale hotel clutter appearance; no dynamics/deformation/manipulation qualification')
        if path.exists():assert read(path)==report
        else:write(path,report)
        a=next(x for x in registry['assets'] if x['asset_id']=='bk-'+base)
        if base in families:
            a['appearance_family'],a['geometry_family']=families[base]
            a['visual_review']=dict(path=str(path.relative_to(ROOT)),sha256=sha(path));enrich(a)
        if outcome=='REJECTED':
            a=next(x for x in registry['assets'] if x['asset_id']=='bk-'+base)
            a.update(status='REJECTED',rejection_reason=observation,blockers=['UNSUITABLE_RESTING_FORM'])
            a['visual_review']=dict(path=str(path.relative_to(ROOT)),sha256=sha(path));enrich(a)
    write(ROOT/'registry/assets.json',registry)
    print('Actual native image reviews saved:',len(reviews),'accepted previews:',sum(x[0]=='PASS' for x in reviews.values()))
