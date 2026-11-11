#!/usr/bin/env python3
"""Generate fully static, crawlable pages from a public GAS JSON snapshot."""
import html,json,os,re,shutil
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone

ROOT=Path(__file__).parent
OUT=ROOT/'dist'
DATA=ROOT/'data'/'public.json'
NAME='中國醫藥大學牙醫系校友會醫療團'
SITE=os.environ.get('SITE_URL','').strip().rstrip('/')
if not SITE or not SITE.startswith('https://'):
    raise SystemExit('Set SITE_URL to your actual https://*.pages.dev URL in Cloudflare Pages environment variables.')
if not DATA.exists(): raise SystemExit('Missing data/public.json. Run the GitHub Actions sync workflow first.')
data=json.loads(DATA.read_text(encoding='utf-8'))
if not isinstance(data.get('events'),list): raise SystemExit('Invalid feed: events must be a list')
events=data['events']; settings=data.get('siteSettings') or {}
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir()

def e(v):return html.escape(str(v if v is not None else ''),quote=True)
def urlpath(id): return '/events/'+quote(str(id),safe='')+'/'
def image(url,alt,cls='',lazy=True):
    if not str(url or '').startswith('https://'):return ''
    return f'<img class="{cls}" src="{e(url)}" alt="{e(alt)}" loading="{"lazy" if lazy else "eager"}">'
def page(title,desc,path,content,ogimg=''):
    canonical=SITE+path
    metaimg=f'<meta property="og:image" content="{e(ogimg)}">' if ogimg else ''
    ld=json.dumps({'@context':'https://schema.org','@type':'Organization','name':NAME,'url':SITE+'/'},ensure_ascii=False).replace('<','\\u003c')
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)}</title><meta name="description" content="{e(desc[:155])}"><meta name="robots" content="index,follow"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="website"><meta property="og:locale" content="zh_TW"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc[:155])}"><meta property="og:url" content="{e(canonical)}">{metaimg}<script type="application/ld+json">{ld}</script><link rel="stylesheet" href="/style.css"></head><body><header><div class="wrap head"><a class="brand" href="/">{image(settings.get('logoUrl'),'醫療團標誌','logo')}<span>{NAME}<small>DENTAL COMMUNITY OUTREACH</small></span></a><nav><a href="/#activities">義診活動</a><a href="/#about">公益理念</a></nav></div></header><main class="wrap">{content}</main><footer><div class="wrap">{NAME} · 記錄每一次付出，分享每一份關懷。</div></footer></body></html>'''

def excerpt(s,n=110):
    s=re.sub(r'\s+',' ',str(s or '')).strip()
    return s[:n]+('…' if len(s)>n else '')

def card(x):
    href=urlpath(x['id']); desc=excerpt(x.get('description') or x.get('treatments'),115)
    return f'<article class="card"><a href="{e(href)}">{image(x.get("coverUrl"),x.get("title"),"cover")}<div class="cardbody"><p class="meta">{e(x.get("date") or x.get("year"))} · {e(x.get("county"))}</p><h3>{e(x.get("title"))}</h3><p>{e(desc)}</p><span class="more">閱讀完整義診紀錄 →</span></div></a></article>'

def detail(x):
    path=urlpath(x['id']); title=str(x.get('title') or '義診活動')
    desc=excerpt(x.get('description') or x.get('treatments') or title,150)
    fields=[('活動日期',x.get('date')),('地點',' '.join(filter(None,[x.get('county'),x.get('location')]))),('服務對象',x.get('audience')),('治療及服務內容',x.get('treatments')),('參與醫師',x.get('doctors')),('主辦／協辦單位',x.get('organizers')),('贊助商／合作單位',x.get('sponsors')),('服務人次',str(x.get('serviceCount') or 0)+' 人')]
    details=''.join(f'<div class="detail"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k,v in fields if v)
    gallery=''.join(image(p.get('url'),'義診活動照片','galleryimg') for p in (x.get('gallery') or []) if isinstance(p,dict))
    text=f'<p class="fulltext">{e(x.get("description") or "尚未提供活動介紹。")}</p>'
    content=f'<div class="back"><a href="/">← 返回義診活動</a></div><p class="eyebrow">義診活動紀錄</p><h1>{e(title)}</h1><p class="muted">{e(x.get("date"))} · {e(x.get("county"))}</p>{image(x.get("coverUrl"),title,"detailcover",False)}<section><h2>活動介紹</h2>{text}</section><section><h2>活動與服務內容</h2><dl class="details">{details}</dl></section>'+ (f'<section><h2>活動照片</h2><div class="gallery">{gallery}</div></section>' if gallery else '')
    dest=OUT/path.lstrip('/');dest.mkdir(parents=True,exist_ok=True)
    (dest/'index.html').write_text(page(title+'｜'+NAME,desc,path,content,x.get('coverUrl') or ''),encoding='utf-8')

ids=set()
for x in events:
    if not isinstance(x,dict) or not x.get('id') or not x.get('title'):raise SystemExit('Invalid event record')
    if x['id'] in ids:raise SystemExit('Duplicate event ID')
    ids.add(x['id'])
    detail(x)

stats=data.get('stats') or {}
hero=image(settings.get('heroUrl'),'醫療團公益義診主視覺','heroimg',False)
about=image(settings.get('aboutUrl'),'公益理念照片','aboutimg')
items=''.join(card(x) for x in events) or '<p class="empty">目前尚未發布義診活動。</p>'
content=f'''<section class="hero"><div><p class="eyebrow">CARE · SHARE · SMILE</p><h1>用專業守護笑容，<br>記錄每一次公益足跡。</h1><p>走進社區、深入偏鄉，分享牙科醫療、口腔衛教及歷年義診服務成果。</p><a class="pill" href="#activities">探索義診紀錄 ↓</a></div>{hero}</section><div class="stats"><div><strong>{len(events)}</strong><span>累積義診場次</span></div><div><strong>{sum(int(x.get('serviceCount') or 0) for x in events):,}</strong><span>累積服務人次</span></div><div><strong>{e(stats.get('partners',0))}</strong><span>公益合作單位</span></div></div><section id="activities"><p class="eyebrow">OUR JOURNEY</p><h2>義診活動紀錄</h2><p class="muted">依年份、地點尋找每一段公益足跡。活動卡片顯示摘要，點擊可閱讀全文。</p><div class="filters"><label>年份 <select id="year" aria-label="篩選年份"><option value="">所有年份</option>{''.join(f'<option value="{e(y)}">{e(y)} 年</option>' for y in sorted({str(x.get('year') or '') for x in events if x.get('year')},reverse=True))}</select></label><label>地點 <select id="county" aria-label="篩選地點"><option value="">所有地點</option>{''.join(f'<option value="{e(c)}">{e(c)}</option>' for c in sorted({str(x.get('county') or '') for x in events if x.get('county')}))}</select></label><label>搜尋 <input id="q" type="search" placeholder="活動、醫師、贊助商、介紹…"></label></div><div class="cards">{items}</div><p id="noResults" class="empty" hidden>沒有符合條件的活動。</p></section><section id="about"><p class="eyebrow">OUR BELIEF</p><h2>讓照護走得更遠</h2><p>記錄醫療團隊的付出，也感謝每一位支持公益的夥伴。</p>{about}</section>'''
(OUT/'index.html').write_text(page(NAME+'｜牙科公益義診與偏鄉口腔醫療紀錄','中國醫藥大學牙醫系校友會醫療團，分享歷年牙科公益義診、偏鄉醫療、口腔衛教、參與醫師及合作單位。','/',content,settings.get('heroUrl') or ''),encoding='utf-8')
(OUT/'style.css').write_text('''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#fbf8f2;color:#403b32;font-family:system-ui,-apple-system,"Noto Sans TC",sans-serif;line-height:1.75}.wrap{max-width:1140px;margin:auto;padding:0 22px}header{background:#fbf8f2;border-bottom:1px solid #e7dfd3}header .head{min-height:80px;display:flex;align-items:center;justify-content:space-between;gap:18px}.brand{display:flex;align-items:center;gap:12px;font-weight:800;font-size:18px;text-decoration:none;color:inherit}.brand small{display:block;font-size:10px;letter-spacing:.18em;color:#81786c}.logo{width:52px;height:52px;object-fit:contain}nav{display:flex;gap:18px}a{color:inherit}nav a{text-decoration:none}.hero{padding:55px 0;display:grid;grid-template-columns:1fr 1fr;align-items:center;gap:35px}.hero h1{font-size:clamp(30px,4vw,49px);line-height:1.3}.heroimg{width:100%;max-height:380px;object-fit:cover;border-radius:20px}.eyebrow{font-size:12px;letter-spacing:.18em;color:#b87955;font-weight:700}.pill{display:inline-block;background:#788775;color:white;text-decoration:none;padding:10px 22px;border-radius:28px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.stats>div{background:#f1e9dc;padding:20px;border-radius:15px}.stats strong{display:block;font-size:28px}.stats span,.muted,.meta{color:#81786c}section{padding:35px 0}.filters{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.filters label{font-size:13px}.filters select,.filters input{display:block;padding:11px;border:1px solid #e7dfd3;border-radius:10px;background:white;min-width:170px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.card{background:white;border:1px solid #e7dfd3;border-radius:16px;overflow:hidden}.card a{text-decoration:none;display:block;height:100%}.cover{width:100%;height:180px;object-fit:cover}.cardbody{padding:18px}.card h3{font-size:19px;margin:5px 0}.card p{margin:6px 0}.card .more{color:#657962;font-weight:700}.back{margin-top:24px}.detailcover{width:100%;max-height:480px;object-fit:cover;border-radius:18px;margin-top:15px}.fulltext{white-space:pre-wrap}.details{display:grid;grid-template-columns:1fr 1fr;gap:14px}.detail{padding:16px;background:white;border:1px solid #e7dfd3;border-radius:12px}.detail dt{font-size:12px;color:#81786c}.detail dd{margin:0;white-space:pre-wrap}.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.galleryimg{width:100%;height:200px;object-fit:cover;border-radius:10px}.aboutimg{max-width:100%;max-height:380px;border-radius:16px}footer{background:#eae2d6;padding:30px 0;color:#6f665a}.empty{padding:20px;color:#81786c}@media(max-width:750px){header .head{align-items:flex-start;flex-direction:column;padding-top:12px;padding-bottom:12px}.hero{grid-template-columns:1fr}.cards{grid-template-columns:repeat(2,1fr)}.details{grid-template-columns:1fr}}@media(max-width:520px){.cards,.stats{grid-template-columns:1fr}.gallery{grid-template-columns:repeat(2,1fr)}.brand{font-size:15px}}''',encoding='utf-8')
# Search filter is progressive enhancement: all activity links remain visible without JS.
js_data=[{'id':str(x['id']),'year':str(x.get('year') or ''),'county':str(x.get('county') or ''),'text':' '.join(str(x.get(k) or '') for k in ('title','description','doctors','sponsors','location','treatments','audience')).lower()} for x in events]
(OUT/'search.js').write_text('const events='+json.dumps(js_data,ensure_ascii=False).replace('<','\\u003c')+';'+'''const cards=[...document.querySelectorAll('.card')];function filter(){const y=document.getElementById('year').value,c=document.getElementById('county').value,q=document.getElementById('q').value.trim().toLowerCase();let count=0;cards.forEach((el,i)=>{const x=events[i];const show=(!y||x.year===y)&&(!c||x.county===c)&&(!q||x.text.includes(q));el.hidden=!show;if(show)count++});document.getElementById('noResults').hidden=count>0;}['year','county','q'].forEach(id=>document.getElementById(id).addEventListener('input',filter));''',encoding='utf-8')
p=OUT/'index.html';p.write_text(p.read_text(encoding='utf-8').replace('</body>','<script defer src="/search.js"></script></body>'),encoding='utf-8')
# Copy optional Google Search Console HTML verification files.
verification=ROOT/'verification'
if verification.exists():
    for f in verification.glob('google*.html'):
        if f.is_file(): shutil.copy2(f,OUT/f.name)
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+SITE+'/sitemap.xml\n',encoding='utf-8')
now=datetime.now(timezone.utc).date().isoformat()
paths=['/']+[urlpath(x['id']) for x in events]
xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{e(SITE+p)}</loc><lastmod>{now}</lastmod></url>\n' for p in paths)+'</urlset>\n'
(OUT/'sitemap.xml').write_text(xml,encoding='utf-8')
print('Generated',len(paths),'pages at',OUT)
