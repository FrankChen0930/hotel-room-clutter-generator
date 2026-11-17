"""Validate local links and execute the exact inline UI script with DOM fixtures."""
import json,os,subprocess,re
from html.parser import HTMLParser
from pathlib import Path
from library import ROOT,read,write,sha

class Page(HTMLParser):
    def __init__(self):super().__init__();self.cards=[];self.links=[];self.views=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='article' and 'data-images' in a:self.cards.append(json.loads(a['data-images']))
        if tag in ['a','img']:self.links.append(a.get('href',a.get('src')))
        if tag=='option':self.views.append(a['value'])

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    page=ROOT/'physics_comparison.html';payload=page.read_text(encoding='utf-8');parser=Page();parser.feed(payload)
    for link in parser.links:
        if link and not link.startswith(('http:','https:','#')):assert (ROOT/link).is_file(),link
    for card in parser.cards:
        for target in card.values():assert (ROOT/target).is_file(),target
    data=dict(cards=parser.cards,views=parser.views,scripts=re.findall(r'<script>(.*?)</script>',payload,re.S))
    write(a.run/'ui_input.json',data)
    script=a.run/'ui_fixture.cjs';script.write_text('''const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));let callback;
const cards=input.cards.map(images=>({dataset:{images:JSON.stringify(images)},img:{},anchor:{},querySelector(selector){return selector==='img'?this.img:this.anchor;}}));
const document={getElementById(){return {addEventListener(event,fn){assert.equal(event,'change');callback=fn;}};},querySelectorAll(){return cards;}};
for(const script of input.scripts)vm.runInNewContext(script,{document});
let checks=0;for(const view of input.views){callback({target:{value:view}});for(let i=0;i<cards.length;i++){assert.equal(cards[i].img.src,input.cards[i][view]);assert.equal(cards[i].anchor.href,input.cards[i][view]);checks++;}}
assert.equal(checks,30);process.stdout.write(JSON.stringify({outcome:'PASS',synchronized_updates:checks}));
''',encoding='utf-8')
    node=Path('C:/Program Files/Microsoft VS Code/Code.exe');process=subprocess.run([str(node),str(script),str(a.run/'ui_input.json')],env={**os.environ,'ELECTRON_RUN_AS_NODE':'1'},capture_output=True,text=True,timeout=30)
    assert process.returncode==0,(process.stdout,process.stderr)
    result=json.loads(process.stdout);write(a.run/'comparison_ui_check.json',dict(**result,local_links=len(parser.links),page_sha256=sha(page),scope='Exact inline JS executed using installed Node runtime with DOM fixtures; offline local links checked, not a full browser layout test'))
    print('PHYSICS_UI_PASS',result)

if __name__=='__main__':main()
