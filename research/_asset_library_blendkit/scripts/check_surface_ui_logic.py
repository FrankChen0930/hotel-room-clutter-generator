"""Execute the actual report JavaScript using VS Code's installed Node runtime."""
import argparse,json,os,subprocess
from html.parser import HTMLParser
from pathlib import Path
from library import ROOT,read,write,sha

class Script(HTMLParser):
    def __init__(self):super().__init__();self.inside=False;self.code=[]
    def handle_starttag(self,tag,attrs):self.inside=tag=='script'
    def handle_endtag(self,tag):
        if tag=='script':self.inside=False
    def handle_data(self,data):
        if self.inside:self.code.append(data)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();run=a.run.resolve()
    prior=run/'comparison_ui_check.json'
    if prior.exists() and read(prior)['outcome']=='FAIL':
        backup=run/'comparison_ui_browser_failure.json'
        if not backup.exists():backup.write_bytes(prior.read_bytes())
    page=ROOT/'comparison.html';parser=Script();parser.feed(page.read_text(encoding='utf-8'));assert len(parser.code)==1
    expected={c['level']+'_'+str(c['seed']):{v:i['path'] for v,i in c['images'].items()} for c in read(run/'comparison_index.json')['cases']}
    data=run/'ui_logic_input.json';write(data,dict(code=parser.code[0],expected=expected))
    test=run/'ui_logic_test.cjs';test.write_text('''const fs=require('fs'),vm=require('vm'),assert=require('assert');
const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const views=Object.keys(Object.values(input.expected)[0]);
const buttons=views.map(v=>({dataset:{view:v},textContent:v,active:false,addEventListener(type,callback){assert.equal(type,'click');this.click=callback;},classList:{toggle(name,state){this.owner.active=state;}}}));
buttons.forEach(b=>b.classList.owner=b);
const anchors=Object.keys(input.expected).map(key=>({dataset:{case:key},href:'',img:{src:'',alt:''},querySelector(tag){assert.equal(tag,'img');return this.img;}}));
const document={querySelectorAll(selector){if(selector==='[data-view]')return buttons;if(selector==='a.capture')return anchors;throw Error('Unexpected DOM selector '+selector);}};
vm.runInNewContext(input.code,{document},{timeout:3000});
let count=0;for(const button of buttons){button.click();assert.equal(buttons.filter(b=>b.active).length,1);assert(button.active);for(const a of anchors){assert.equal(a.href,input.expected[a.dataset.case][button.dataset.view]);assert.equal(a.img.src,a.href);assert(a.img.alt.includes(button.textContent));count++;}}
assert.equal(count,60);console.log(JSON.stringify({outcome:'PASS',checks:count,views:buttons.length,cards:anchors.length,runtime:process.version}));
''',encoding='utf-8')
    env={**os.environ,'ELECTRON_RUN_AS_NODE':'1'}
    result=subprocess.run(['C:/Program Files/Microsoft VS Code/Code.exe',str(test),str(data)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,creationflags=0x08000000)
    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8',errors='replace')[-1500:])
    report=json.loads(result.stdout.decode('utf-8').strip());assert report['outcome']=='PASS'
    report.update(comparison_sha256=sha(page),scope='Actual inline report JS executed with event/DOM fixtures on installed Node, all60 image/link updates and active controls checked; full browser startup blocked by GPU access and retained separately')
    write(prior,report);print('ACTUAL_REPORT_JS_LOGIC',report)

if __name__=='__main__':main()
