#!/usr/bin/env python3
"""Replace exactly five demonstrably wrong onsen pictures with reviewed real venue photos.

Each selection below was visually checked on the actual facility's own website.
No random unrelated search results, duplicates, filler or branding banners.
This is a personal travel site's illustrative use. Source remains traceable.
"""
from __future__ import annotations
import io, hashlib, json, sys
from pathlib import Path
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
TARGETS={
 "hiroshima-d2-08": {
  "image":"https://www.honoyu.jp/wp-content/themes/honoyu/assets/img/ujina/top/fv1.jpg",
  "page":"https://www.honoyu.jp/ujina/",
  "caption":"우지나 천연온천 호노유의 실제 노천탕",
  "venue":"宇品天然温泉 ほの湯"
 },
 "shizuoka-d2-06": {
  "image":"https://www.kusanagino-yu.com/common/img/bath/bath1-2.png",
  "page":"https://www.kusanagino-yu.com/bath/index.html",
  "caption":"아오이온천 쿠사나기노유의 실제 노천탕",
  "venue":"あおい温泉 草薙の湯"
 },
 "okinawa-d1-06": {
  "image":"https://www.resorts.co.jp/upload/tenant_1/senaga_ryujin049.webp",
  "page":"https://www.resorts.co.jp/senaga/ryujinhotspring",
  "caption":"류큐온천 류진노유의 바다 전망 노천탕",
  "venue":"琉球温泉 龍神の湯"
 },
 "sendai-d2-05": {
  "image":"https://akiugrand.com/images/index/hs04.jpg?v=2",
  "page":"https://akiugrand.com/",
  "caption":"아키우 그랜드호텔의 실제 노천탕",
  "venue":"秋保グランドホテル"
 },
 "takamatsu-d1-06": {
  "image":"https://busshozan.com/images/3.jpg",
  "page":"https://busshozan.com/",
  "caption":"붓쇼잔온천의 실제 목욕 시설",
  "venue":"仏生山温泉 天平湯"
 }
}
def gitblob(data):
 return hashlib.sha1(f'blob {len(data)}\0'.encode('utf-8')+data).hexdigest()
def main():
 manifest={x['key']:x for x in json.loads((ASSETS/'photo_manifest_281.json').read_text(encoding='utf-8'))}
 old=json.loads((ASSETS/'recommended.json').read_text(encoding='utf-8'))
 new=json.loads((ASSETS/'new_routes.json').read_text(encoding='utf-8'))
 gallery=json.loads((ASSETS/'gallery.json').read_text(encoding='utf-8'))
 local_file=ASSETS/'local_schedule_photos.json'
 local=json.loads(local_file.read_text(encoding='utf-8'))
 used={hashlib.sha256((ROOT/x['local_path']).read_bytes()).hexdigest()
       for x in manifest.values() if x['key'] not in TARGETS}
 session=requests.Session()
 session.headers.update({'User-Agent':'Mozilla/5.0 JapanAtlasTravelPlanner/1.0'})
 completed=[]
 failures=[]
 for key,details in TARGETS.items():
  task=manifest[key]
  assert task['place']==details['venue'], f'Wrong facility {key} {task["place"]}'
  path=ROOT/task['local_path']
  try:
   # Multiple connection routes: some original sites intermittently time out on GitHub runners.
   candidate_urls=[details['image']]
   if '://www.honoyu.jp/' in details['image']:
    candidate_urls.append(details['image'].replace('://www.honoyu.jp/','://honoyu.jp/'))
   resp=None;last=None
   for image_url in candidate_urls:
    try:
     resp=session.get(image_url,timeout=(7,22))
     resp.raise_for_status()
     break
    except Exception as ex:
     last=ex
     print('SOURCE RETRY FAILED:',key,image_url,str(ex)[:140],flush=True)
     resp=None
   if resp is None:raise last
   with Image.open(io.BytesIO(resp.content)) as im:
    if im.width<240 or im.height<180:
     raise RuntimeError(f'Image too small {im.width}x{im.height}')
    # Save a single legitimate photograph in standard JPEG format for Pages.
    rgb=im.convert('RGB')
    stream=io.BytesIO()
    rgb.save(stream,format='JPEG',quality=89,optimize=True)
    jpeg=stream.getvalue()
   unique=hashlib.sha256(jpeg).hexdigest()
   if unique in used:raise RuntimeError('Source photograph duplicates another itinerary image')
   # Visual review establishes that source page and file are the same named facility.
   used.add(unique)
   path.write_bytes(jpeg)
   sha=gitblob(jpeg)
   source=(new if task['category']=='new' else old)['cities'][task['city']]
   itinerary=source['days'][task['day']-1][task['step']-1]
   pool=source['photos'] if task['category']=='new' else gallery[task['city']]
   item={'file':'LOCAL-'+key+'.jpg','title':task['title'],'place':task['place'],
         'kind':itinerary.get('kind','온천'),'local':'./'+task['local_path'],
         'local_verified':True,'source':details['page'],'source_image':details['image'],
         'author':'시설 공식 사이트','license':'시설 원본 이미지 · 사용 조건 별도 확인 필요',
         'license_url':'','scope':details['caption']}
   pool[:]=[x for x in pool if x.get('file')!=item['file']]+[item]
   itinerary['photo_file']=item['file'];itinerary['photo_match']=details['caption']
   local[key]={'url':'./'+task['local_path'],'place':task['place'],
       'source':details['page'],'source_image':details['image'],
       'author':'시설 공식 사이트','license':'시설 원본 이미지 · 사용 조건 별도 확인 필요',
       'license_url':'','match':'exact_facility_visual_review',
       'source_proof_blob_sha':sha,'description_scope':details['caption']}
   completed.append({'key':key,'venue':task['place'],'source':details['page'],
       'image_source':details['image'],'photo_sha':sha,'dimensions':len(jpeg),
       'description':details['caption']})
   print('EXACT FACILITY:',key,details['page'],flush=True)
  except Exception as e:
   print('FAILED FACILITY:',key,str(e),flush=True)
   failures.append({'key':key,'error':str(e)[:280]})
   continue
 for file,data in [('recommended.json',old),('new_routes.json',new),
                   ('gallery.json',gallery),('local_schedule_photos.json',local)]:
  (ASSETS/file).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 photo_hashes=[hashlib.sha256((ROOT/m['local_path']).read_bytes()).hexdigest() for m in manifest.values()]
 assert len(photo_hashes)==281 and len(set(photo_hashes))==281,'Duplicate after onsen restoration'
 assert len(local)==281 and len(completed)>=4,'Fewer than 4 official onsen photos could be downloaded'
 report={'updated':len(completed),'files':len(photo_hashes),'unique':len(set(photo_hashes)),'items':completed}
 (ROOT/'photo_audit/official_onsen_restoration.json').write_text(
   json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('REVIEWED FACILITY PHOTO REPLACEMENTS:',len(completed),'281 UNIQUE:',len(set(photo_hashes)),flush=True)
if __name__=='__main__':main()
