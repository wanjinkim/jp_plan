#!/usr/bin/env python3
"""Fill the single missing Osaka Naniwa no Yu photo using an exact facility image.

No invented photo or arbitrary location substitution. Store original source for audit.
"""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from repair_all_schedule_photos import get, image_bytes_ok

BASE=Path(__file__).resolve().parents[1]
KEY='osaka-d1-08'
PHOTO=BASE/'assets/photos/schedules/osaka/d1-08.jpg'
SOURCES=[
 ('https://naniwanoyu.com/onsen/images/sga.jpg','https://naniwanoyu.com/onsen/','공식 나니와노유 건물 사진'),
 ('https://www.yunavi.net/img/sento/naniwanoyu_gaikan2_200228142833_1.jpeg','https://www.yunavi.net/sento/tennenonsen_naniwanoyu/photogallary/','나니와노유 외관 야경'),
 ('https://media.triple.guide/triple-cms/c_limit%2Cf_auto%2Ch_1024%2Cw_1024/4b219083-7bc2-4226-bf7f-3964414aa961.jpeg','https://triple.guide/attractions/1c311b75-2ca3-455d-a86f-97b2db716d40','나니와노유 입구 사진')
]
errors=[]
picked=None
for url,source,label in SOURCES:
 try:
  data=get(url,accept='image/avif,image/webp,image/jpeg,image/png,*/*',timeout=28,retries=3)
  if image_bytes_ok(data,PHOTO):
   picked=(source,label)
   break
  errors.append('invalid image from '+url)
 except Exception as e:errors.append(url+' '+str(e)[:120])
if not picked:
 print('ERROR: No Naniwa no Yu venue photograph could be loaded:',errors,flush=True)
 sys.exit(1)
source,label=picked
manifest=json.loads((BASE/'assets/photo_manifest_281.json').read_text(encoding='utf-8'))
assert any(x['key']==KEY for x in manifest)
npath=BASE/'assets/new_routes.json'
r=json.loads(npath.read_text(encoding='utf-8'))
step=r['cities']['osaka']['days'][0][7]
assert step['place']=='天然温泉 なにわの湯'
file='LOCAL-'+KEY+'.jpg'
item={'file':file,'title':step['title'],'place':step['place'],
      'kind':step['kind'],'local':'./assets/photos/schedules/osaka/d1-08.jpg',
      'local_verified':True,'source':source,'author':'시설 또는 사진 제공처',
      'license':'권리 상태 미확인 · 출처 명시', 'license_url':'',
      'scope':'실제 나니와노유 시설 사진 · 공식/사진 제공처 출처'}
pool=r['cities']['osaka']['photos']
pool[:]=[p for p in pool if p.get('file')!=file]+[item]
step['photo_file']=file
step['photo_match']=item['scope']
npath.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
local=BASE/'assets/local_schedule_photos.json'
index=json.loads(local.read_text(encoding='utf-8'))
b=PHOTO.read_bytes()
sha=hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
index[KEY]={'url':'./assets/photos/schedules/osaka/d1-08.jpg','source':source,'place':step['place'],
 'author':'시설 또는 사진 제공처','license':'권리 상태 미확인 · 출처 명시',
 'license_url':'','match':'exact_venue','source_verified_by':'official_or_venue_catalog_image',
 'source_proof_blob_sha':sha}
local.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'id':KEY,'status':'downloaded','source':source,'name':label,'sha':sha,'errors':errors}
(BASE/'photo_audit/naniwanoyu_rescue.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SAVED VERIFIED NAN IWA ONSEN VENUE PHOTO:',report,flush=True)
