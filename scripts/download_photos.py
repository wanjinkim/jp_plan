#!/usr/bin/env python3
"""Acquire Commons-licensed location photos for 141 JAPAN ATLAS activities.

Only actual photo bytes from Wikimedia Commons are stored. Exact venue candidates
are preferred, and search-only results are explicitly labeled as references.
This program requires public network access; it is run manually or via GitHub
Actions. It cannot guarantee all 141 events have a suitably licensed image.
"""
import argparse
import html
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError as e:
    raise SystemExit('Pillow required: pip install Pillow') from e

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'assets/photo_tasks.json'
ROUTES = ROOT / 'assets/new_routes.json'
PHOTO_DIR = ROOT / 'assets/photos'
API = 'https://commons.wikimedia.org/w/api.php'
USER_AGENT = 'JAPAN-ATLAS-travel-photo-collection/1.0 (public educational travel planner; Wikimedia Commons author credited)'
CACHE = {}
LOOKUP_CACHE = {}
BAD_LICENSE = ('noncommercial', 'no derivatives', 'fair use', 'all rights reserved')
ALLOWED_PARTS = ('cc by', 'cc-by', 'cc0', 'creative commons zero', 'public domain', 'pd-', 'pdm')

class Strip(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data): self.parts.append(data)

def plain(value):
    p = Strip(); p.feed(str(value or ''))
    return html.unescape(' '.join(p.parts)).strip()[:300]

def get(url, retries=3):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'commons.wikimedia.org','upload.wikimedia.org'}:
        raise ValueError('Only HTTPS Wikimedia URLs may be downloaded')
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json,image/*'})
            with urllib.request.urlopen(req, timeout=25) as response:
                chunk = response.read(10_000_000) # 10MB hard cap per requested thumbnail
                if len(chunk) >= 10_000_000: raise ValueError('Image thumbnail exceeds 10 MB')
                return chunk
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc; time.sleep(1.0 + 2.0 * attempt)
    raise last

def query_api(**params):
    args = {'action':'query','format':'json','formatversion':2,'redirects':1,**params}
    return json.loads(get(API + '?' + urllib.parse.urlencode(args, doseq=True)).decode('utf-8'))

def license_ok(ext):
    name = plain(ext.get('LicenseShortName',{}).get('value','')).lower()
    name = name.replace('–','-').replace('—','-')
    url = (ext.get('LicenseUrl',{}).get('value','') or '').lower()
    joined = name+' '+url
    if any(x in joined for x in BAD_LICENSE): return False
    return any(x in joined for x in ALLOWED_PARTS)

def image_meta(file_title):
    if file_title in CACHE: return CACHE[file_title]
    # Accept exact titles only for the curated first phase
    title = 'File:' + file_title.removeprefix('File:')
    data = query_api(prop='imageinfo',titles=title,iiprop='url|mime|extmetadata',iiurlwidth=1024)
    records = data.get('query',{}).get('pages',[])
    result = None
    for p in records:
        if p.get('missing') or not p.get('imageinfo'): continue
        info = p['imageinfo'][0]
        mime = info.get('mime','')
        if mime not in ('image/jpeg','image/png','image/webp'): continue
        ext = info.get('extmetadata') or {}
        if not license_ok(ext): continue
        url = info.get('thumburl') or info.get('url')
        if not url:continue
        result = {'file':p['title'].removeprefix('File:'),'url':url,
          'source':'https://commons.wikimedia.org/wiki/'+urllib.parse.quote(p['title'].replace(' ','_'),safe='():,._-'),
          'author':plain(ext.get('Artist',{}).get('value')) or '원본 Commons 기록 참고',
          'license':plain(ext.get('LicenseShortName',{}).get('value')),
          'license_url':plain(ext.get('LicenseUrl',{}).get('value')),
          'description':plain(ext.get('ImageDescription',{}).get('value'))}
        break
    CACHE[file_title] = result
    return result

def text_score(candidate, search_hint):
    # Strict English token overlap; generic 'japan', 'city', etc don't count.
    stop={'japan','japanese','station','the','in','of','at','a','and','city','tokyo','osaka','fukuoka','takamatsu','matsuyama','kumamoto','ehime','kagawa','kyushu','park'}
    tokens=[x for x in re.findall(r'[a-z]{3,}',search_hint.lower()) if x not in stop]
    name=candidate.lower()
    matches=[x for x in tokens if x in name]
    return len(set(matches))

def search_candidates(hint):
    if hint in LOOKUP_CACHE: return LOOKUP_CACHE[hint]
    items=[]
    data=query_api(generator='search',gsrsearch=hint,gsrnamespace=6,gsrlimit=20, prop='imageinfo',iiprop='url')
    for p in data.get('query',{}).get('pages',[]):
        title=p.get('title','')
        if not title.startswith('File:') or not re.search(r'\.(jpg|jpeg|png|webp)$',title,re.I):continue
        score=text_score(title,hint)
        if score<1: continue
        items.append((score,title.removeprefix('File:')))
    items.sort(key=lambda x:-x[0]); LOOKUP_CACHE[hint]=[name for score,name in items]
    return LOOKUP_CACHE[hint]

def save_image(info,path):
    buf=get(info['url'])
    try:
        with Image.open(io.BytesIO(buf)) as im:
            im=ImageOps.exif_transpose(im)
            if im.width < 300 or im.height < 200: return False
            im.thumbnail((1024,768),Image.Resampling.LANCZOS)
            if im.mode!='RGB':
                if 'A' in im.mode:
                    background=Image.new('RGB', im.size,'white');background.paste(im,mask=im.getchannel('A'));im=background
                else: im=im.convert('RGB')
            path.parent.mkdir(parents=True,exist_ok=True)
            im.save(path,'JPEG',quality=82,optimize=True)
            return True
    except (UnidentifiedImageError, OSError, ValueError): return False

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=141)
    parser.add_argument('--no-search',action='store_true',help='Only explicit Commons candidate titles')
    args=parser.parse_args()
    tasks=json.loads(TASKS.read_text('utf-8'))
    routes=json.loads(ROUTES.read_text('utf-8'))
    existing_pool={c: list(routes['cities'][c].get('photos',[])) for c in routes['cities']}
    used=defaultdict(set); seen_files={c:{p.get('file') for p in pool} for c,pool in existing_pool.items()}
    licenses=[]; errors=[]; fetched=0; failures=0
    for task in tasks[:args.limit]:
        city,day,step=task['city'],task['day'],task['step']
        entry=routes['cities'][city]['days'][day-1][step-1]
        hint=task['search_keywords']
        priority=[(name,'직접 지정한 장소 후보') for name in task['commons_candidates']]
        if not args.no_search:
            try:
                priority += [(name,'검색결과: 장소명 추가 확인 필요') for name in search_candidates(hint)]
            except Exception as e:
                errors.append({'id':task['id'],'stage':'search','error':str(e)})
        names=set(); opts=[]
        for name,grade in priority:
            if name in names:continue
            names.add(name)
            try: info=image_meta(name)
            except Exception as e:
                errors.append({'id':task['id'],'stage':'metadata','candidate':name,'error':str(e)});continue
            if info: opts.append((info,grade))
        # Avoid duplication inside one city when possible (without stealing another venue's photo)
        opts.sort(key=lambda t: (t[0]['file'] in used[city],t[1]!='직접 지정한 장소 후보'))
        assigned=False
        for info,grade in opts:
            local=PHOTO_DIR / city / f'd{day}-{step:02d}.jpg'
            try:
                if not save_image(info,local):continue
            except Exception as e:
                errors.append({'id':task['id'],'stage':'download','candidate':info['file'],'error':str(e)});continue
            used[city].add(info['file'])
            file_id=f'LOCAL-{city}-d{day}-{step:02d}.jpg'
            match='장소일치' if grade=='직접 지정한 장소 후보' else '지역참고'
            entry['photo_file']=file_id
            entry['photo_match']=match
            entry.pop('photo_query',None)
            if file_id not in seen_files[city]:
                existing_pool[city].append({'file':file_id,'title':f"{task['title']} · 사진",'kind':'일정',
                    'place':task['place'],'subtitle':task['title'], 'scope':('실제 장소 사진 후보' if match=='장소일치' else '참고사진 · 장소 일치 미확인'),
                    'match_type':('지역참고' if match!='장소일치' else '장소일치'),
                    'local':'./assets/photos/'+city+f'/d{day}-{step:02d}.jpg',
                    'source':info['source'],'author':info['author'],'license':info['license'],'license_url':info['license_url']})
                seen_files[city].add(file_id)
            licenses.append({'id':task['id'],'city':city,'place':task['place'],'file':info['file'],
                'image_path':str(local.relative_to(ROOT)),'source':info['source'], 'author':info['author'],
                'license':info['license'],'license_url':info['license_url'],'match_type':match})
            task['status']='downloaded' if match=='장소일치' else 'reference_downloaded'
            fetched+=1; assigned=True
            print(f"[{fetched:03}] {task['id']}: {info['file']} ({match})",flush=True)
            break
        if not assigned:
            failures+=1
            task['status']='missing_or_review_required'
            print(f"[!] {task['id']} NO suitably licensed and matching Commons photo",flush=True)
    for c,pool in existing_pool.items():routes['cities'][c]['photos']=pool
    TASKS.write_text(json.dumps(tasks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    ROUTES.write_text(json.dumps(routes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'PHOTO_LICENSES.json').write_text(json.dumps(licenses,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'PHOTO_DOWNLOAD_ERRORS.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'PHOTO_DOWNLOAD_REPORT.md').open('w',encoding='utf-8') as out:
        out.write('# 실사진 로컬 다운로드 결과\n\n')
        out.write(f'- 처리 일정: {min(args.limit,len(tasks))}개\n- 실제 다운로드: {fetched}개\n- 실패·검토 필요: {failures}개\n\n')
        out.write('구글 이미지 검색 캡처물은 포함하지 않았습니다. 로컬 사진은 Wikimedia Commons에서 저작권 메타데이터를 확인해 다운로드했습니다.\n\n')
        out.write('| 일정 | 저장경로 | 실제 장소 판정 | 라이선스 | 출처 |\n|---|---|---|---|---|\n')
        for x in licenses:out.write(f"| {x['id']} | `{x['image_path']}` | {x['match_type']} | {x['license']} | {x['source']} |\n")
    print(f'Finished: {fetched} downloaded, {failures} missing, {len(errors)} metadata/network errors.')
    if fetched==0:return 2
    return 0

if __name__=='__main__': sys.exit(main())
