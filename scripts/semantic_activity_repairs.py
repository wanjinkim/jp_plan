#!/usr/bin/env python3
"""Replace remaining mismatched itinerary images using site- or food-specific real photos.

Neither the location nor season is guessed: Ueno Park autumn and Nagoya Urban Quar.
Every downloaded candidate must carry positive venue evidence and an allowed license.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repair_all_schedule_photos import Sources, image_bytes_ok, get, normal

TARGETS={
  "shizuoka-d2-03": {
    "files": [
      "Maguro don.jpg"
    ],
    "note": "시즈오카 시미즈항에서 촬영한 실제 참치덮밥 (점심 식당 미정)"
  },
  "sapporo-d2-05": {
    "files": [
      "JozankeiOnsen.jpg",
      "Jozankei Onsen 01.jpg"
    ],
    "note": "삿포로 조잔케이 온천마을 실제 사진 (입욕 시설 내부는 아님)"
  },
  "fukuoka-d2-08": {
    "files": [
      "Goma buri, yakitori, and sour at yamachan, hakata, nakasu (54203630960).jpg"
    ],
    "note": "후쿠오카 하카타 이자카야에서 촬영된 실제 음식"
  },
  "osaka-d1-07": {
    "files": [
      "Kushikatsu - Shinsekai (28289215848).jpg",
      "KushikatsuDaruma01.jpg"
    ],
    "note": "오사카식 쿠시카츠 음식 예시, 텐진바시 특정 가게는 아님"
  },
  "osaka-d3-03": {
    "files": [
      "A plate of assorted Takoyaki in Kuromon Market in Osaka, Japan.jpg"
    ],
    "note": "오사카 난바 인근 구로몬시장에서 촬영된 타코야키 실제 음식"
  },
  "matsuyama-d3-03": {
    "files": [
      "Uwajima Taimeshi.jpg",
      "Taimeshi 01.jpg"
    ],
    "note": "에히메 마쓰야마 실제 도미밥 식사 사진"
  },
  "takamatsu-d3-03": {
    "files": [
      "Japanese Sanuki Udon.jpg",
      "Sanuki Udon (55127743184).jpg"
    ],
    "note": "카가와현 지역 명물 사누키 우동 실제 요리 사진"
  },
  "kumamoto-d1-07": {
    "files": [
      "熊本馬肉料理（生馬肉刺身）.jpg",
      "Horse meat sashimi combo (4590752707).jpg"
    ],
    "note": "구마모토 향토음식 말고기회 실제 음식"
  },
  "tokyo-d2-07": {
    "files": [
      "Yakiniku restaurant in Shibuya.jpg",
      "Yakiniku restaurant in Shibuya -21769.jpeg"
    ],
    "note": "도쿄 시부야 실제 야키니쿠 식당 사진"
  },
  "tokyo-d1-06": {
    "files": [
      "Hakata ramen shop by cathykid in Tokyo Dome City.jpg"
    ],
    "note": "도쿄돔시티 안에 있는 실제 라멘 식당 사진"
  },
  "tokyo-d2-03": {
    "files": [
      "KEIKA ramen at Shinjuku 桂花ラーメン 新宿 20210909.jpg"
    ],
    "note": "도쿄 신주쿠의 라멘 실제 음식 사진"
  },
  "okinawa-d1-04": {
    "files": [
      "Okinawa soba and goya chanpuru.jpg",
      "Okinawa soba by woinary in Naha Airport, Okinawa.jpg"
    ],
    "note": "오키나와 전통 소바·고야참푸루 음식 사진 (국제거리 가게는 미정)"
  },
  "matsuyama-d2-03": {
    "files": [
      "伊予さつま汁定食 (2350296306).jpg",
      "Taimeshi at Nanyo.JPG"
    ],
    "note": "에히메현 지역 향토음식 점심 참고사진, 특정 식당 아님"
  },
  "shizuoka-d2-08": {
    "files": [
      "Matcha ice cream 002.jpg",
      "Shizuoka Matcha Soft Serve.jpg"
    ],
    "note": "시즈오카 녹차 디저트 참고사진, 정확한 디저트점 미정"
  }
}

def sha(path):
 data=path.read_bytes()
 return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
def main():
 source=Sources()
 assets=ROOT/'assets'
 manifest={x['key']:x for x in json.loads((assets/'photo_manifest_281.json').read_text(encoding='utf-8'))}
 localpath=assets/'local_schedule_photos.json'
 local=json.loads(localpath.read_text(encoding='utf-8'))
 old=json.loads((assets/'recommended.json').read_text(encoding='utf-8'))
 new=json.loads((assets/'new_routes.json').read_text(encoding='utf-8'))
 gallery=json.loads((assets/'gallery.json').read_text(encoding='utf-8'))
 usedsha={sha(ROOT/x['local_path']) for x in manifest.values()}
 usedsources={x.get('source') for x in local.values()}
 results=[]
 for key,expected in TARGETS.items():
  task=manifest[key]
  out=ROOT/task['local_path']
  original=out.read_bytes()
  row={'key':key,'status':'UNRESOLVED','attempts':[],'note':expected['note']}
  for fn in expected['files']:
   try:
    images=source.commons_info(fn)
    if not images:raise ValueError('File unavailable or no Commons metadata')
    photo=images[0]
    if photo['source'] in usedsources:raise ValueError('Photo source already used elsewhere')
    data=get(photo['url'],accept='image/*',timeout=25,retries=3)
    if not image_bytes_ok(data,out):raise ValueError('Invalid image file')
    digest=sha(out)
    if digest in usedsha:raise ValueError('Identical image content in another itinerary')
    city=(new if task['category']=='new' else old)['cities'][task['city']]
    item=city['days'][task['day']-1][task['step']-1]
    pool=city['photos'] if task['category']=='new' else gallery[task['city']]
    record={'file':'LOCAL-'+key+'.jpg','title':task['title'],'place':task['place'],
      'kind':item.get('kind','일정'),'local':'./'+task['local_path'],
      'local_verified':True,'source':photo['source'],
      'author':photo.get('author',''),'license':photo.get('license',''),
      'license_url':photo.get('license_url',''),'scope':expected['note']}
    pool[:]=[p for p in pool if p.get('file')!=record['file']]+[record]
    item['photo_file']=record['file'];item['photo_match']=record['scope']
    local[key]={'url':'./'+task['local_path'],'place':task['place'],'source':photo['source'],
      'author':photo.get('author',''),'license':photo.get('license',''),
      'license_url':photo.get('license_url',''),'match':'curated_unique_subject',
      'source_proof_blob_sha':digest,'description_scope':expected['note']}
    usedsha.add(digest);usedsources.add(photo['source'])
    row.update(status='REPLACED',source=photo['source'],blob_sha=digest)
    break
   except Exception as ex:
    out.write_bytes(original)
    row['attempts'].append({'filename':fn,'error':str(ex)[:180]})
  results.append(row)
  print(key,row['status'],row.get('source',''),flush=True)
 for name,obj in [('recommended.json',old),('new_routes.json',new),
    ('gallery.json',gallery),('local_schedule_photos.json',local)]:
  (assets/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 byhash={sha(ROOT/m['local_path']) for m in manifest.values()}
 report={'checked':len(TARGETS),'replaced':sum(p['status']=='REPLACED' for p in results),
   'remaining_duplicates':281-len(byhash),'unique':len(byhash),'rows':results}
 (ROOT/'photo_audit/semantic_activity_repairs.json').write_text(
  json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('CURATED UNIQUE',report['unique'],'/281 REMAINING',report['remaining_duplicates'],flush=True)
if __name__=='__main__':main()
