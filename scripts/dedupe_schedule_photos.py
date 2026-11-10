#!/usr/bin/env python3
"""Find distinct real photos for each duplicate Japan Atlas itinerary image.

Does not simulate uniqueness by re-encoding/cropping. Venue/article keywords
are required and every replacement is a distinct photo source and Git blob.
"""
from __future__ import annotations
import hashlib, json, re, sys, time
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repair_all_schedule_photos import Sources, get, image_bytes_ok, CITIES
from PIL import Image

ASSETS=ROOT/'assets'
MANIFEST=json.loads((ASSETS/'photo_manifest_281.json').read_text(encoding='utf-8'))
TASKS={v['id']:v for v in json.loads((ASSETS/'photo_tasks.json').read_text(encoding='utf-8'))}
INDEX=json.loads((ASSETS/'local_schedule_photos.json').read_text(encoding='utf-8'))
OLD=json.loads((ASSETS/'recommended.json').read_text(encoding='utf-8'))
NEW=json.loads((ASSETS/'new_routes.json').read_text(encoding='utf-8'))
GALLERY=json.loads((ASSETS/'gallery.json').read_text(encoding='utf-8'))
REPORT=ROOT/'photo_audit/deduplication_report.json'
STOP={'japan','japanese','photo','image','from','with','view','city','the','and','for','near','station',
      'airport','hotel','hotspring','onsen','building','inside','entrance','terminal','area','park'}
SEMANTIC={
 'airport':re.compile(r'airport|空港|aeroport|departure|arrival',re.I),
 'station':re.compile(r'station|駅|rail|train|tram|subway|metro|bus|monorail|ferry|terminal',re.I),
 'food':re.compile(r'ramen|ラーメン|udon|うどん|sushi|寿司|katsu|gyutan|beef|meat|okonomiyaki|お好み焼き|noodle|teishoku|鯛めし|rice|curry|dessert|ice cream|restaurant',re.I),
 'onsen':re.compile(r'onsen|温泉|湯|bath|spa',re.I)
}
def digest(path):
 data=path.read_bytes()
 return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
def tokens(s):
 return [x.lower() for x in re.findall(r'[a-zA-Z]{4,}',s or '') if x.lower() not in STOP]
def category(m):
 t=m['title']+' '+m['place']
 if re.search(r'온천|입욕|노천탕|湯|温泉',t):return 'onsen'
 if re.search(r'식사|점심|저녁|라멘|우동|도미밥|양고기|해산물|카레',t):return 'food'
 if re.search(r'공항|空港',t):return 'airport'
 if re.search(r'역|駅|버스|철도|전철|페리|리무진|공항행',t):return 'station'
 return 'other'
def keywords(m):
 names=[m.get('candidate_file','').rsplit('.',1)[0].replace('_',' ')]
 names += [m['place']]
 if m.get('category')=='new':
  names += [TASKS.get(m['key'],{}).get('search_keywords','')]
 if m.get('category')=='original':
  names += [m.get('photo_file','').rsplit('.',1)[0].replace('_',' ')]
 # Numeric/file noise in old data is not an accurate venue
 return list(dict.fromkeys(v.strip() for v in names if v and len(v.strip())>3))
def relevant(photo,m,query):
 desc=(photo.get('title','')+' '+photo.get('desc','')).lower()
 if not desc:return False
 name_tokens=tokens(query)
 city_alias=CITIES.get(m['city'],(m['city'],''))[0].lower()
 specific=[v for v in name_tokens if v not in [city_alias, 'fukuoka','hiroshima','tokyo',
  'osaka','sapporo','nagoya','shizuoka','sendai','matsuyama','takamatsu','kumamoto','okinawa']]
 term_hit=any(v in desc for v in specific) if specific else False
 japanese=m['place']
 jp_hit=len(japanese)>=3 and japanese in (photo.get('title','')+' '+photo.get('desc',''))
 city_hit=city_alias in desc
 # Named locations: reject candidate if neither original subject nor the exact place matches.
 if not (term_hit or jp_hit or (city_hit and not specific)):return False
 kind=category(m)
 if kind in SEMANTIC and not SEMANTIC[kind].search(desc):
  # For location synonyms a venue name without explicit category can still be correct
  if not jp_hit:return False
 if kind=='onsen' and any(x in desc for x in ['government office','city hall','prefectural office']):
  return False
 return True
def candidates(api,m):
 unique=set()
 first=m.get('candidate_file','')
 if first:
  unique.add(first)
  for x in api.commons_info(first):yield x,first
 for cand in TASKS.get(m['key'],{}).get('commons_candidates',[])[:5]:
  if cand not in unique:
   unique.add(cand)
   for x in api.commons_info(cand):yield x,cand
 qs=keywords(m)
 for query in qs[:4]:
  # Wikipedia lead photo is a different directory from Commons MediaSearch.
  for x in api.wikipedia_image(query):
   yield x,query
  for x in api.search_commons(query)[:20]:
   yield x,query
def save(photos,rows):
 for name,obj in [('local_schedule_photos.json',INDEX),('recommended.json',OLD),
                 ('new_routes.json',NEW),('gallery.json',GALLERY)]:
  (ASSETS/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 current=duplicates()
 payload={'total':len(MANIFEST),'unique_images':len({digest(ROOT/x['local_path']) for x in MANIFEST if (ROOT/x['local_path']).is_file()}),
          'duplicate_excess':sum(len(xs)-1 for xs in current.values() if len(xs)>1),
          'duplicate_groups':[v for v in current.values() if len(v)>1],
          'attempted':len(rows),'replaced':sum(r['status']=='REPLACED' for r in rows),
          'items':rows}
 REPORT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('REPAIRS',payload['replaced'],'/',len(rows),'DUPLICATES LEFT',payload['duplicate_excess'],flush=True)
def duplicates():
 by_sha=defaultdict(list)
 for m in MANIFEST:
  path=ROOT/m['local_path']
  if path.is_file():by_sha[digest(path)].append(m['key'])
 return by_sha
def main():
 api=Sources()
 groups=duplicates()
 order=[]
 for group in groups.values():
  # Keep first source on the original visit; others must have different photo content
  order.extend(group[1:] if len(group)>1 else [])
 used_sha=set(groups)
 used_sources={x.get('source') for x in INDEX.values() if x.get('source')}
 manifest={m['key']:m for m in MANIFEST}
 records=[]
 for step,key in enumerate(order,1):
  m=manifest[key]
  record={'key':key,'status':'UNRESOLVED','old_source':INDEX.get(key,{}).get('source',''),'new_source':'','queries':keywords(m)}
  path=ROOT/m['local_path']
  original=path.read_bytes()
  attempted=set()
  matches=[]
  try:
   for photo,q in candidates(api,m):
    url=photo.get('url');src=photo.get('source')
    if not url or not src or src in used_sources or url in attempted:continue
    attempted.add(url)
    if relevant(photo,m,q):matches.append((photo,q))
    if len(matches)>=22:break
  except Exception as exc:record['search_error']=str(exc)[:180]
  for photo,q in matches:
   try:
    data=get(photo['url'],accept='image/*',timeout=17,retries=2)
    if not image_bytes_ok(data,path):path.write_bytes(original);continue
    sha=digest(path)
    if sha in used_sha:
     path.write_bytes(original);continue
    row=(NEW if m['category']=='new' else OLD)['cities'][m['city']]
    slot=row['days'][m['day']-1][m['step']-1]
    pool=row['photos'] if m['category']=='new' else GALLERY[m['city']]
    photo_item={'file':'LOCAL-'+key+'.jpg','title':m['title'],'place':m['place'],
      'kind':slot.get('kind','일정'),'local':'./'+m['local_path'],
      'local_verified':True,'source':photo['source'],'author':photo.get('author',''),
      'license':photo.get('license',''),'license_url':photo.get('license_url',''),
      'scope':'장소·활동 관련 사진 (중복 방지 검색·원본 구별 확인)'}
    pool[:]=[p for p in pool if p.get('file')!=photo_item['file']]+[photo_item]
    slot['photo_file']=photo_item['file']
    slot['photo_match']=photo_item['scope']
    INDEX[key]={'url':'./'+m['local_path'],'source':photo['source'],'place':m['place'],
      'author':photo.get('author',''),'license':photo.get('license',''),
      'license_url':photo.get('license_url',''),'match':'place_or_activity_match',
      'source_proof_blob_sha':sha,'source_verified_by':'download_verified_content'}
    used_sha.add(sha);used_sources.add(photo['source'])
    record.update(status='REPLACED',new_source=photo['source'],matched_query=q,sha=sha)
    break
   except Exception as exc:
    record['download_error']=str(exc)[:120]
    path.write_bytes(original)
  if record['status']!='REPLACED':path.write_bytes(original)
  records.append(record)
  print(f'[{step}/{len(order)}] {key}: {record["status"]}',flush=True)
  if step%8==0:save(INDEX,records)
 save(INDEX,records)
if __name__=='__main__':main()
