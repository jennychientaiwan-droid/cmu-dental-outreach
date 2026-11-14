#!/usr/bin/env python3
"""Fetch ONLY the public GAS feed; refuse to overwrite last good data on errors."""
import json,os,urllib.request
from pathlib import Path
url=os.environ.get('GAS_FEED_URL','').strip()
if not url.startswith('https://script.google.com/macros/s/') or 'public_feed=1' not in url:
    raise SystemExit('GAS_FEED_URL must be a Google Apps Script /exec?public_feed=1 URL')
request=urllib.request.Request(url,headers={'User-Agent':'OutreachStaticSiteSync/1.0'})
with urllib.request.urlopen(request,timeout=40) as r:
    body=r.read(6_000_001)
if len(body)>6_000_000: raise SystemExit('Feed too large')
data=json.loads(body)
if not isinstance(data,dict) or not isinstance(data.get('events'),list) or not isinstance(data.get('siteSettings'),dict):
    raise SystemExit('Invalid public feed; snapshot unchanged')
for x in data['events']:
    if not isinstance(x,dict) or not x.get('id') or not x.get('title'):raise SystemExit('Invalid event; snapshot unchanged')
p=Path(__file__).parent/'data'/'public.json'
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Validated',len(data['events']),'published events')
