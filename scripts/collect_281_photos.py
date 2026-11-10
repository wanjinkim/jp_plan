#!/usr/bin/env python3
"""JAPAN ATLAS: acquire actual licensed photo bytes for every schedule.

Requires internet access to Wikimedia Commons/ja.wikipedia.org and Pillow.
No invented photos, no scraping of Google thumbnails, no claims about exact venues
without manual review. Emits photo files, licensing metadata and missing audit.
"""
from __future__ import annotations
import argparse, io, json, re, sys, time, html, urllib.parse, urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT=Path(__file__).resolve().parents[1]
COM='https://commons.wikimedia.org/w/api.php'
JAW='https://ja.wikipedia.org/w/api.php'
CONTACT='JAPAN-ATLAS-photo-collector/1.0 (https://github.com/wanjinkim/jphUQgQXoSnXM6VP5rSECCcbQQ0u8YWhY8LpIsBjpi; open travel photo audit)'
BAD=('noncommercial','non-commercial','no derivatives','no-derivatives','fair use','all rights reserved')
GOOD=('cc by','cc-by','cc0','public domain','pd-','pdm','creative commons zero')
FIELDS=('city','day','step','place','title','status','source','local_path')

class ClearText(HTMLParser):
    def __init__(self): super().__init__(); self.t=[]
    def handle_data(self, data):self.t.append(data)

def strip(t):
    p=ClearText()
    try:p.feed(str(t or ''))
    except Exception:return ''
    return html.unescape(' '.join(p.t)).strip()[:250]

def api(base, **opts):
    url=base+'?'+urllib.parse.urlencode({'action':'query','format':'json','formatversion':'2',**opts})
    req=urllib.request.Request(url,headers={'User-Agent':CONTACT,'Accept':'application/json'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=28) as r:return json.load(r)
        except Exception:
            if attempt==3:raise
            time.sleep(2+attempt*3)

def get_image(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname not in ('upload.wikimedia.org','commons.wikimedia.org'):
        raise ValueError('Only Wikimedia HTTPS image URLs are allowed')
    req=urllib.request.Request(url,headers={'User-Agent':CONTACT,'Accept':'image/*'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=35) as res:
                if int(res.headers.get('Content-Length') or 0)>12_000_000:raise ValueError('Image too big')
                data=res.read(12_000_001)
                if len(data)>12_000_000:raise ValueError('Image too big')
                return data
        except Exception:
            if attempt==2:raise
            time.sleep(2+attempt*2)

def license_meta(title):
    if not title:return None
    if not title.startswith('File:'):title='File:'+title
    j=api(COM,prop='imageinfo',titles=title,iiprop='url|mime|extmetadata',iiurlwidth='1024')
    pages=j.get('query',{}).get('pages',[])
    for p in pages:
        inf=(p.get('imageinfo') or [{}])[0]
        ext=inf.get('extmetadata') or {}
        license=strip(ext.get('LicenseShortName',{}).get('value',''))
        license_url=strip(ext.get('LicenseUrl',{}).get('value',''))
        joint=(license+' '+license_url).lower()
        if any(x in joint for x in BAD) or not any(x in joint for x in GOOD):continue
        if inf.get('mime') not in ('image/jpeg','image/png','image/webp'):continue
        if not inf.get('thumburl') and not inf.get('url'):continue
        title=p['title'];source='https://commons.wikimedia.org/wiki/'+urllib.parse.quote(title.replace(' ','_'),safe=':._-()')
        return {'title':title,'url':inf.get('thumburl') or inf['url'],'source':source,'license':license,
                'license_url':license_url,'author':strip(ext.get('Artist',{}).get('value','')),
                'description':strip(ext.get('ImageDescription',{}).get('value',''))}
    return None

def wiki_page_file(place):
    # The name must resolve to a Japanese article before we use the article's main image.
    j=api(JAW,prop='pageimages',titles=place,redirects='1',piprop='name',pithumbsize='1024')
    for p in j.get('query',{}).get('pages',[]):
        if not p.get('missing') and p.get('pageimage'):return p['pageimage']
    return None

def search_commons(query):
    j=api(COM,generator='search',gsrsearch=query,gsrnamespace=6,gsrlimit=15,prop='imageinfo',iiprop='url')
    return [p['title'] for p in j.get('query',{}).get('pages',[]) if p.get('title','').startswith('File:') and re.search(r'\.(jpe?g|png|webp)$',p.get('title',''),re.I)]

def search_quality(filetitle, task, hint):
    name=filetitle.lower().replace('_',' ')
    place=task.get('place','').replace(' ','').lower()
    if len(place)>=3 and place in name.replace(' ',''):return 10
    hint_tokens=[x.lower() for x in re.findall(r'[a-z]{4,}',hint) if x.lower() not in
        {'japan','japanese','photo','picture','travel','city','from','about','fukuoka','osaka','tokyo','takamatsu','kumamoto','matsuyama','station'}]
    matched=len(set(x for x in hint_tokens if x in name))
    return matched

def save_jpeg(meta,path):
    data=get_image(meta['url'])
    with Image.open(io.BytesIO(data)) as im:
        im=ImageOps.exif_transpose(im)
        if im.width<280 or im.height<180:raise ValueError('Too small to be meaningful')
        im.thumbnail((1024,800),Image.Resampling.LANCZOS)
        if im.mode!='RGB':
            if 'A' in im.getbands():
                white=Image.new('RGB',im.size,'white');white.paste(im,mask=im.getchannel('A'));im=white
            else:im=im.convert('RGB')
        path.parent.mkdir(parents=True,exist_ok=True)
        im.save(path,'JPEG',quality=83,optimize=True)
    with Image.open(path) as test:test.verify()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--limit',type=int,default=281,help='For a short test, use 1; default: all 281 schedules')
    p.add_argument('--strict',action='store_true',help='Return failure if not all 281 photos have been saved')
    p.add_argument('--no-search',action='store_true',help='Only curated candidates and exact Wikipedia images')
    p.add_argument('--max-runtime-seconds', type=int, default=2700, help='Stop cleanly before a GitHub Actions job timeout, saving partial results')
    opts=p.parse_args()
    manifest=json.loads((ROOT/'assets/photo_manifest_281.json').read_text('utf-8'))
    tasks={t['id']:t for t in json.loads((ROOT/'assets/photo_tasks.json').read_text('utf-8'))}
    old=json.loads((ROOT/'assets/recommended.json').read_text('utf-8'))
    new=json.loads((ROOT/'assets/new_routes.json').read_text('utf-8'))
    gallery=json.loads((ROOT/'assets/gallery.json').read_text('utf-8'))
    meta_cache={};search_cache={};wiki_cache={};download_cache={}
    audit=[];fail=[];processed=0
    start_time=time.monotonic()
    for task in manifest[:opts.limit]:
        # Continue over several workflow runs without downloading already verified local photos again.
        done_path=ROOT/task['local_path']
        if task.get('status')=='downloaded' and done_path.exists():
            try:
                with Image.open(done_path) as previous: previous.verify()
                continue
            except (OSError,ValueError,UnidentifiedImageError):
                task['status']='missing_or_manual_review'
        if time.monotonic()-start_time>=opts.max_runtime_seconds:
            print('Runtime guard reached; partial photos are saved for commit.',flush=True)
            break
        city=task['city']; key=task['key'];place=task['place']
        schedule=(old['cities'][city] if task['category']=='original' else new['cities'][city])['days'][task['day']-1][task['step']-1]
        city_pool=gallery[city] if task['category']=='original' else new['cities'][city]['photos']
        existing={x.get('file'):x for x in city_pool}
        tt=tasks.get(key,{})
        hint=tt.get('search_keywords','') or f"{place} {task['title']} Japan"
        candidates=[]
        if task['candidate_file']:candidates.append((task['candidate_file'],'사전 지정 참고사진'))
        for c in tt.get('commons_candidates',[]):candidates.append((c,'장소 기반 지정 후보'))
        for pic in city_pool:
            if pic.get('place')==place and pic.get('file'):
                candidates.append((pic['file'],'장소명이 같은 기존 사진 후보'))
        if place:
            try:
                if place not in wiki_cache:wiki_cache[place]=wiki_page_file(place)
                if wiki_cache[place]:candidates.append((wiki_cache[place],'일본어 위키피디아 문서 대표사진'))
            except Exception as ex:fail.append({'key':key,'stage':'ja-wikipedia','error':str(ex)[:120]})
        if not opts.no_search:
            for term in [place, hint, ' '.join(hint.split()[:3])]:
                if not term:continue
                if term not in search_cache:
                    try:search_cache[term]=search_commons(term)
                    except Exception as ex:search_cache[term]=[];fail.append({'key':key,'stage':'commons-search','error':str(ex)[:120]})
                for file in search_cache[term]:
                    # Require match on place or at least one distinctive English keyword.
                    if search_quality(file,task,hint)>=1:candidates.append((file,'검색 후보 · 육안 검토 필요'))
        chosen=None;used=set()
        for fn,match in candidates:
            if fn in used:continue
            used.add(fn)
            if fn not in meta_cache:
                try:meta_cache[fn]=license_meta(fn)
                except Exception as ex:
                    meta_cache[fn]=None;fail.append({'key':key,'stage':'license','file':fn,'error':str(ex)[:120]})
            info=meta_cache[fn]
            if not info:continue
            fpath=ROOT/task['local_path']
            try:
                # Cache photo bytes for repeated schedules, but use per-schedule local file paths.
                if info['url'] in download_cache and download_cache[info['url']].is_file():
                    from shutil import copy2
                    fpath.parent.mkdir(parents=True,exist_ok=True);copy2(download_cache[info['url']],fpath)
                else:
                    save_jpeg(info,fpath);download_cache[info['url']]=fpath
                chosen=(info,match);break
            except (UnidentifiedImageError,Exception) as ex:
                fail.append({'key':key,'stage':'download','file':fn,'error':str(ex)[:120]})
        if chosen:
            info,match=chosen
            photo_id=f"LOCAL-{key}.jpg"
            schedule['photo_file']=photo_id
            schedule['photo_match']='사진 후보 · 원본 위치 확인' if match.startswith('검색') else match
            city_pool.append({'file':photo_id,'local':'./'+task['local_path'],'local_verified':True,
                'title':task['title'],'place':place,'kind':schedule.get('kind','명소'),'source':info['source'],
                'license':info['license'],'license_url':info['license_url'],'author':info['author'],
                'match_type':match,'scope':match})
            task.update({'status':'downloaded','source':info['source'],'license':info['license'],
                'license_url':info['license_url'],'author':info['author'],'match_type':match,'photo_file':photo_id})
            audit.append({'key':key,'path':task['local_path'],'file':info['title'],'source':info['source'],
                'license':info['license'],'author':info['author'],'match_type':match})
            processed+=1
            print(f'[{processed:03d}] {key}: {info["title"]}',flush=True)
        else:
            # Preserve the old entry. Never mark a remote or unverified picture as local.
            task['status']='missing_or_manual_review'
            print(f'[MISSING] {key}: {task["title"]} / {place}',flush=True)
        (ROOT/'assets/photo_manifest_281.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (ROOT/'assets/new_routes.json').write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (ROOT/'assets/recommended.json').write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (ROOT/'assets/gallery.json').write_text(json.dumps(gallery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'total':len(manifest),'downloaded':sum(t['status']=='downloaded' for t in manifest),
        'missing':sum(t['status']!='downloaded' for t in manifest),'entries':audit,'issues':fail}
    (ROOT/'PHOTO_DOWNLOAD_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Report: {report['downloaded']}/{report['total']} actually-downloaded photos. Missing: {report['missing']}")
    return 2 if opts.strict and report['missing'] else 0

if __name__=='__main__':sys.exit(main())
