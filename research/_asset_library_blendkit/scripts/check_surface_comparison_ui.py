"""Exercise all synchronized view buttons in an isolated offline headless browser."""
import argparse,json,subprocess
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote
from library import ROOT,read,write,sha

class Links(HTMLParser):
    def __init__(self):super().__init__();self.targets=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag in {'a','img'}:self.targets.append(values.get('href') if tag=='a' else values.get('src'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();run=a.run.resolve()
    page=ROOT/'comparison.html';before=sha(page);payload=page.read_text(encoding='utf-8');links=Links();links.feed(payload)
    for target in links.targets:
        if target and not target.startswith(('https:','http:','#')):assert (ROOT/unquote(target)).is_file(),target
    expected={c['level']+'_'+str(c['seed']):{v:i['path'] for v,i in c['images'].items()} for c in read(run/'comparison_index.json')['cases']}
    check='''<script>try{const expected=EXPECTED;let count=0;for(const button of document.querySelectorAll('[data-view]')){button.click();if(document.querySelectorAll('button.active').length!==1)throw Error('active state');for(const anchor of document.querySelectorAll('a.capture')){const target=expected[anchor.dataset.case][button.dataset.view];if(anchor.getAttribute('href')!==target||anchor.querySelector('img').getAttribute('src')!==target)throw Error('synchronized image mismatch');count++;}}if(count!==60)throw Error('interaction count '+count);document.documentElement.setAttribute('data-ui-check','PASS');document.documentElement.setAttribute('data-ui-interactions',String(count));}catch(e){document.documentElement.setAttribute('data-ui-check','FAIL '+e.message);}</script>'''.replace('EXPECTED',json.dumps(expected))
    ordinal=0
    while (ROOT/('_surface_ui_a'+str(ordinal).zfill(3)+'.html')).exists():ordinal+=1
    tag='surface_ui_a'+str(ordinal).zfill(3);test=ROOT/('_'+tag+'.html');test.write_text(payload.replace('</main>',check+'</main>'),encoding='utf-8')
    profile=ROOT/'reports'/(tag+'_profile');browser=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    command=[str(browser),'--headless','--disable-gpu','--disable-background-networking','--disable-extensions','--no-first-run','--no-default-browser-check',
        '--host-resolver-rules=MAP * ~NOTFOUND','--user-data-dir='+str(profile),'--virtual-time-budget=3000','--dump-dom',test.as_uri()]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60,creationflags=0x08000000)
    (ROOT/'reports'/(tag+'.dom.html')).write_bytes(result.stdout);(ROOT/'reports'/(tag+'.log')).write_bytes(result.stderr)
    passed=result.returncode==0 and b'data-ui-check="PASS"' in result.stdout and b'data-ui-interactions="60"' in result.stdout
    assert sha(page)==before
    report=dict(outcome='PASS' if passed else 'FAIL',browser_exit_code=result.returncode,synchronized_image_checks=60 if passed else 0,
        local_links_checked=len(links.targets),comparison_sha256=before,browser_profile=str(profile.relative_to(ROOT)),
        scope='Offline fresh profile; all10 view buttons clicked and all6 card links/images checked; actual comparison file unchanged')
    write(run/'comparison_ui_check.json',report);print('COMPARISON_BROWSER_CHECK',report);raise SystemExit(not passed)

if __name__=='__main__':main()
