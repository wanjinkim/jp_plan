#!/usr/bin/env python3
"""JAPAN ATLAS photo repair, verified bytes and exact-or-contextual image mapping.

Uses Wikimedia Commons and (if necessary) openly licensed Openverse image results.
Searches user-provided schedule place, day, title; broadens to region+activity only
when an exact venue cannot be illustrated. Never equates regional reference with
actual venue. Writes files locally and updates source JSON only after PIL validation.

Use with GitHub Actions or a normal Python environment with internet access.
"""
from __future__ import annotations
import argparse, csv, html, io, json, os, re, shutil, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
from PIL import Image, ImageOps

BASE=Path(__file__).resolve().parents[1]
COM='https://commons.wikimedia.org/w/api.php'
JAW='https://ja.wikipedia.org/w/api.php'
OV='https://api.openverse.org/v1/images/'
UA='JapanAtlasPhotoRepair/3.0 (https://github.com/wanjinkim/jphUQgQXoSnXM6VP5rSECCcbQQ0u8YWhY8LpIsBjpi; publicly auditable travel site) Python/3'
CITIES={
 'hiroshima':('Hiroshima','広島'), 'shizuoka':('Shizuoka','静岡'),
 'sapporo':('Sapporo','札幌'), 'nagoya':('Nagoya','名古屋'),
 'sendai':('Sendai','仙台'), 'okinawa':('Okinawa','沖縄'),
 'fukuoka':('Fukuoka','福岡'), 'osaka':('Osaka','大阪'),
 'tokyo':('Tokyo','東京'), 'matsuyama':('Matsuyama','松山'),
 'takamatsu':('Takamatsu','高松'), 'kumamoto':('Kumamoto','熊本')}
KINDS=[
 ('airport international terminal',r'공항|입국|출국|항공|비행|空港|airport'),
 ('railway station train',r'駅|철도|전철|열차|JR|지하철|역|기차|승차|하차'),
 ('bus transportation',r'버스|버스터미널|리무진|bus'),
 ('onsen hot spring bath',r'온천|입욕|목욕|스파|사우나|温泉|湯'),
 ('Japanese food restaurant',r'식사|점심|저녁|라멘|우동|스시|초밥|간식|먹거리|정식|덮밥|맛집|食|飯'),
 ('park Japanese garden',r'공원|정원|庭園|公園|녹지'),
 ('temple shrine',r'사찰|절|신사|神社|寺|관음'),
 ('shopping street market',r'시장|상점|쇼핑|商店|쇼핑거리'),
 ('sea coastline harbor',r'바다|항구|해안|フェリー|港|海|페리|해변'),
 ('hotel room',r'호텔|숙소|객실|체크인|체크아웃|취침|샤워|숙박|휴식'),
 ('night city lights',r'야경|야식|밤 산책|야간|night'),
 ('nature landscape',r'산책|자연|산|전망|숲|트레킹|경관')]
BANNED=('noncommercial','non-commercial','no derivatives','no-derivatives','all rights reserved','fair use','unknown')
GOOD=('cc by','cc-by','cc0','creative commons zero','public domain','pdm','pd-')
STOP={'japan','japanese','photo','image','place','city','travel','trip','the','and','terminal','of','in','at','station','park','airport', 'restaurant','hotel','scenery'}

class Strip(HTMLParser):
 def __init__(self): super().__init__();self.parts=[]
 def handle_data(self,v):self.parts.append(v)
def clean(s):
 p=Strip()
 try:p.feed(str(s or ''))
 except Exception:return str(s or '')[:250]
 return html.unescape(' '.join(p.parts)).strip()[:500]
def kind(task):
 text=task.get('title','')+' '+task.get('place','')
 for k,regex in KINDS:
  if re.search(regex,text,re.I):return k
 return 'landmark city scenery'
def urlhost(url):
 try:return urllib.parse.urlsplit(url).hostname or ''
 except Exception:return ''
def is_good_license(name,url):
 name=clean(name).lower().replace('–','-');url=str(url or '').lower()
 x=name+' '+url
 return not any(b in x for b in BANNED) and any(g in x for g in GOOD)

def get(url,accept='application/json',timeout=14,retries=2,maxbytes=12_000_000):
 if not url.startswith('https://'):raise ValueError('Only HTTPS downloads')
 # No arbitrary redirect into internal networks: user-supplied URL is never used here.
 last=None
 for attempt in range(retries):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':accept})
   with urllib.request.urlopen(req,timeout=timeout) as r:
    if r.url.startswith('http://'):raise ValueError('Unsafe redirect')
    if int(r.headers.get('Content-Length') or 0)>maxbytes:raise ValueError('File too large')
    data=r.read(maxbytes+1)
    if len(data)>maxbytes:raise ValueError('File too large')
    return data
  except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as ex:
   last=ex
   if isinstance(ex,urllib.error.HTTPError) and ex.code in (400,401,403,404):break
   if attempt < retries-1:time.sleep(0.7+attempt*1.2)
 raise last

class Sources:
 def __init__(self):self.cache={};self.errors=Counter();self.warned=set();self.blocked=set()
 def query(self,url,**kwargs):
  request=url+'?'+urllib.parse.urlencode(kwargs)
  if urlhost(url) in self.blocked:return {}
  if request not in self.cache:
   try:
    self.cache[request]=json.loads(get(request).decode('utf-8'))
   except Exception as ex:
    sig=urlhost(url)+':'+str(getattr(ex,'code',type(ex).__name__))
    self.errors[sig]+=1
    if sum(n for k,n in self.errors.items() if k.startswith(urlhost(url)+':'))>=3:
     print('WARNING source unreachable; skip remaining API calls for',urlhost(url),flush=True)
     self.blocked.add(urlhost(url))
    if sig not in self.warned:
     print('WARNING API',sig, 'e.g.',str(ex)[:120],flush=True);self.warned.add(sig)
    self.cache[request]={}
  return self.cache[request]
 def commons_info(self,fn):
  title=('File:'+fn.removeprefix('File:'))
  res=self.query(COM,action='query',format='json',formatversion='2',redirects='1',titles=title,prop='imageinfo',iiprop='url|mime|extmetadata',iiurlwidth='900')
  return [self.from_commons(p) for p in res.get('query',{}).get('pages',[]) if self.from_commons(p)]
 def from_commons(self,p):
  i=(p.get('imageinfo') or [None])[0]
  if not i or i.get('mime') not in ('image/jpeg','image/png','image/webp'):return None
  ext=i.get('extmetadata') or {}
  lic=clean((ext.get('LicenseShortName') or {}).get('value',''))
  licenseurl=clean((ext.get('LicenseUrl') or {}).get('value',''))
  if not is_good_license(lic,licenseurl):return None
  url=i.get('thumburl') or i.get('url')
  if not url:return None
  file=p.get('title','')
  return dict(url=url,source='https://commons.wikimedia.org/wiki/'+urllib.parse.quote(file.replace(' ','_'),safe=':._-(),'),file=file,
              title=file.removeprefix('File:').replace('_',' '),desc=clean((ext.get('ImageDescription') or {}).get('value','')),
              author=clean((ext.get('Artist') or {}).get('value','')),
              license=lic, license_url=licenseurl,provider='Wikimedia Commons')
 def search_commons(self,q):
  res=self.query(COM,action='query',format='json',formatversion='2',generator='search',gsrsearch=q,gsrnamespace='6',gsrlimit='12',prop='imageinfo',iiprop='url|mime|extmetadata',iiurlwidth='900')
  return [x for p in res.get('query',{}).get('pages',[]) if (x:=self.from_commons(p))]
 def wikipedia_image(self,place):
  res=self.query(JAW,action='query',format='json',formatversion='2',redirects='1',titles=place,prop='pageimages',piprop='name')
  files=[p.get('pageimage') for p in res.get('query',{}).get('pages',[]) if p.get('pageimage')]
  if files:return self.commons_info(files[0])
  return []
 def openverse(self,q):
  res=self.query(OV,q=q,page_size='18',license='by,by-sa,cc0,pdm')
  out=[]
  for r in res.get('results',[]):
   lic=(r.get('license') or '').lower()
   if lic not in ('by','by-sa','cc0','pdm'):continue
   url=r.get('thumbnail') or r.get('url')
   if not url or not url.startswith('https://'):continue
   host=urlhost(url)
   if host in ('localhost','127.0.0.1','0.0.0.0'):continue
   # Prefer Openverse thumbnail proxy; licensed metadata is attached to result.
   source=r.get('foreign_landing_url') or r.get('detail_url') or r.get('url') or ''
   if not source.startswith('https://'):continue
   out.append(dict(url=url,source=source,title=r.get('title',''),desc=' '.join((x.get('name','') for x in r.get('tags',[])[:5] if isinstance(x,dict))),
                   author=r.get('creator') or '',license=lic,license_url=r.get('license_url',''),provider='Openverse',file=''))
  return out

def tokens(s):
 return [x for x in re.findall(r'[a-z]{4,}',s.lower()) if x not in STOP]
def score(info,task,q,grade):
 text=(info['title']+' '+info.get('desc','')).lower()
 place=(task.get('place') or '').lower().replace(' ','')
 qwords=tokens(q)
 count=len({x for x in qwords if x in text})
 if len(place)>2 and place in text.replace(' ',''):count+=5
 # Source full-text search ranking is useful even if filename is Japanese.
 return count+(4 if grade=='exact' else 0)
def image_bytes_ok(buf,out):
 with Image.open(io.BytesIO(buf)) as source:
  src=ImageOps.exif_transpose(source)
  if src.width<250 or src.height<160:return False
  src.thumbnail((960,680),Image.Resampling.LANCZOS)
  if src.mode!='RGB':
   if 'A' in src.getbands():
    canvas=Image.new('RGB',src.size,'white');canvas.paste(src,mask=src.getchannel('A'));src=canvas
   else:src=src.convert('RGB')
  out.parent.mkdir(parents=True,exist_ok=True)
  tmp=out.with_suffix('.tmp')
  src.save(tmp,format='JPEG',quality=80,optimize=True)
  with Image.open(tmp) as verify:verify.verify()
  os.replace(tmp,out)
  return True

def prepare_queries(task,t):
 city_en,city_jp=CITIES[task['city']]
 place=(task.get('place') or '').strip()
 english=(t.get('search_keywords') or '').replace(' 日本','').strip()
 k=kind(task)
 queries=[]
 # grade 'exact' means search is based on explicitly named place, not verified venue photo.
 if english:queries.append((english,'exact'))
 if place:queries.append((place,'exact'))
 if place and len(place)<22:queries.append((place+' '+city_jp,'exact'))
 # Explanatory fallback remains city+type, not unrelated random picture.
 queries.extend([(city_en+' '+k,'reference'),(city_jp+' '+k,'reference')])
 # Return distinct short query list.
 return list(dict.fromkeys((q,g) for q,g in queries if q))[:5]

def fetch_for_task(s,task,t,used_urls,city_fallback,report):
 key=task['key'];place=task.get('place','')
 explicit=[]
 for fn in t.get('commons_candidates',[]):explicit.append(fn)
 if task.get('candidate_file'):explicit.append(task['candidate_file'])
 # Known filenames came from prior image searches; no filename-embedding assumptions.
 candidate=[]
 for fn in dict.fromkeys(explicit):
  for r in s.commons_info(fn):
   # Pre-assigned historical pictures may be just a regional reference, not a venue photo.
   q=(t.get('search_keywords') or place)
   rank=score(r,task,q,'exact')
   grade='exact' if fn in t.get('commons_candidates',[]) and rank>=5 else 'reference'
   candidate.append((r,grade,rank))
 if place:
  for r in s.wikipedia_image(place):candidate.append((r,'exact',10))
 queries=prepare_queries(task,t)
 for q,grade in queries:
  c=s.search_commons(q)
  for r in c:candidate.append((r,grade,score(r,task,q,grade)))
  # Secondary index: search metadata in Openverse if Commons is empty / too weak.
  if (not c or not any(score(r,task,q,grade)>=2 for r in c)) and re.search(r'[a-z]',q):
   for r in s.openverse(q):candidate.append((r,grade,score(r,task,q,grade)))
  # Don't send more requests if strong exact candidate available.
  if grade=='exact' and any(g=='exact' and sc>=5 for _,g,sc in candidate):break
 # Fallback may reuse a real photo of a related scene in same city if search APIs are down;
 # retain a truthful reference label. Avoid blank card while keeping provenance.
 typekey=(task['city'],kind(task))
 if not candidate and city_fallback.get(typekey):
  candidate.extend((dict(x), 'reference',0) for x in city_fallback[typekey])
 candidate.sort(key=lambda x:(x[1]=='exact', x[2],x[0]['url'] not in used_urls),reverse=True)
 seen=set();fail=[]
 for r,grade,sc in candidate[:26]:
  if r['url'] in seen:continue
  seen.add(r['url'])
  try:
   buf=get(r['url'],accept='image/*',timeout=22,retries=2)
   out=BASE/task['local_path']
   if not image_bytes_ok(buf,out):continue
   used_urls.add(r['url'])
   photo={**r, 'grade':grade,'place':place,'key':key,'local':'./'+task['local_path']}
   city_fallback.setdefault(typekey,[]).append(r)
   return photo
  except Exception as ex:
   fail.append(str(ex)[:95]);continue
 report['failures']=fail[:3]
 return None

def valid_jpeg(p):
 try:
  with Image.open(p) as i:i.verify()
  return True
 except Exception:return False

def main(argv=None):
 a=argparse.ArgumentParser()
 a.add_argument('--city',choices=list(CITIES));a.add_argument('--limit',type=int,default=0)
 a.add_argument('--dry-run',action='store_true')
 opts=a.parse_args(argv)
 manifest=json.loads((BASE/'assets/photo_manifest_281.json').read_text('utf-8'))
 tasks={x['id']:x for x in json.loads((BASE/'assets/photo_tasks.json').read_text('utf-8'))}
 manifest=[x for x in manifest if not opts.city or x['city']==opts.city]
 if opts.limit:manifest=manifest[:opts.limit]
 s=Sources();used_urls=set();city_fallback={};results=[]
 # Load current repo JSON, never rebuild or overwrite travel plans or budgets.
 changes={}
 for path in ('assets/recommended.json','assets/new_routes.json','assets/gallery.json'):
  fp=BASE/path
  if not fp.is_file():raise SystemExit(f'MISSING {path}. Upload original website data too.')
  changes[path]=json.loads(fp.read_text('utf-8'))
 for num,task in enumerate(manifest,1):
  key=task['key'];t=tasks.get(key,{})
  out=BASE/task['local_path'];record={'id':key,'place':task.get('place',''),'title':task['title'],'status':'missing','source':'','local':task['local_path'],'failures':[]}
  # Existing downloaded files count ONLY if bytes are actual JPEG verified by Pillow.
  if out.is_file() and valid_jpeg(out):
   rec={'url':'','source':(task.get('source') or ''),'license':'previously supplied, verify original license','license_url':'','author':'',
        'provider':'existing local file','grade':'reference','local':'./'+task['local_path'],'key':key,'place':task.get('place','')}
   record.update(status='existing',source=rec['source'],license=rec['license'],match='previously saved');photo=rec
  elif opts.dry_run:record['status']='planned';photo=None
  else:
   photo=fetch_for_task(s,task,t,used_urls,city_fallback,record)
   if photo:record.update(status='downloaded',source=photo['source'],author=photo.get('author',''),license=photo.get('license',''),license_url=photo.get('license_url',''),match=photo.get('grade','reference'))
  if photo and not opts.dry_run:
   rec={'file':'LOCAL-'+key+'.jpg','title':task['title'],'place':task['place'], 'kind':'명소',
        'local':'./'+task['local_path'],'local_verified':True,'source':photo['source'],
        'author':photo.get('author',''), 'license':photo.get('license',''),'license_url':photo.get('license_url',''),
        'scope':'동일 장소 검색 사진' if photo['grade']=='exact' else '관련 지역 참고사진'}
   if task['category']=='original':
    obj=changes['assets/recommended.json']['cities'][task['city']]
    pool=changes['assets/gallery.json'][task['city']]
   else:
    obj=changes['assets/new_routes.json']['cities'][task['city']]
    pool=obj['photos']
   row=obj['days'][task['day']-1][task['step']-1]
   row['photo_file']=rec['file'];row['photo_match']=rec['scope']
   pool[:]=[p for p in pool if p.get('file')!=rec['file']]+[rec]
  results.append(record)
  print(f'[{num}/{len(manifest)}] {key} {record["status"]}',flush=True)
  if not opts.dry_run and num%15==0:
   write_outputs(changes,results,s,intermediate=True)
 if not opts.dry_run:write_outputs(changes,results,s,intermediate=False)
 ct=Counter(x['status'] for x in results)
 print('RESULT:',dict(ct),'API ERRORS:',dict(s.errors),flush=True)
 # Exit 0 so partial successes are always committed; report still explicitly discloses missing.
 return 0

def write_outputs(changes,results,s,intermediate=False):
 for path,obj in changes.items():
  (BASE/path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 report={'total_attempted':len(results),'counts':dict(Counter(r['status'] for r in results)),
         'api_errors':dict(s.errors),'items':results}
 (BASE/'PHOTO_REPAIR_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# JAPAN ATLAS · 사진 원본 및 라이선스','',
        '실제 원본 사진의 저작자, 라이선스, 링크를 확인하세요. 다운로드한 이미지는 용량에 맞춰 크기를 줄였습니다.','']
 for row in results:
  if row['status'] in ('downloaded','existing'):
   lines.append('- **'+row['id']+'** / '+row.get('place','')+' / '+row.get('match','')+' / '+row.get('author','')+' / '+row.get('license','')+' / '+row.get('license_url','')+' / '+row.get('source',''))
 (BASE/'PHOTO_CREDITS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 with (BASE/'PHOTO_REPAIR_STATUS.csv').open('w',newline='',encoding='utf-8-sig') as f:
  writer=csv.DictWriter(f,fieldnames=['id','place','title','status','source','local'],extrasaction='ignore');writer.writeheader();writer.writerows(results)

if __name__=='__main__':raise SystemExit(main())
