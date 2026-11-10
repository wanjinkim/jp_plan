#!/usr/bin/env python3
"""Replace four audited mismatches using manually verified, CC-licensed Commons files.

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
  "hiroshima-d3-01": {
    "files": [
      "View of north entrance of Hiroshima Station.jpg"
    ],
    "note": "히로시마역 북쪽 출입구 실제 사진"
  },
  "kumamoto-d2-08": {
    "files": [
      "馬刺し（居酒屋とりかわ竹乃屋サクラマチ熊本店）20210924-P1240605.jpg",
      "熊本馬肉料理（生馬肉刺身）.jpg",
      "Basashi001.jpg"
    ],
    "note": "구마모토 향토음식 말고기회 예시"
  },
  "okinawa-d3-03": {
    "files": [
      "Okinawan cuisine set.jpg",
      "Okinawa soba and goya chanpuru.jpg"
    ],
    "note": "오키나와 점심·현지음식 예시, 특정 가게 사진은 아님"
  },
  "osaka-d2-07": {
    "files": [
      "MATSUBA Shrimp KUSHI KATSU 120yen (3064112314).jpg",
      "Kushikatsu - Shinsekai (28289215848).jpg"
    ],
    "note": "오사카 이자카야 저녁 메뉴 쿠시카츠 예시"
  },
  "osaka-d2-03": {
    "files": [
      "Kitsune udon at Tennōji.jpg",
      "Bowl of Kitsune Udon.jpg"
    ],
    "note": "오사카 우동 점심 메뉴 참고사진, 미노오 식당 현장 사진은 아님"
  },
  "sapporo-d3-01": {
    "files": [
      "Inside the Sapporo Station 2026-02-12.jpg",
      "Sapporo Station in November 2025.jpg"
    ],
    "note": "삿포로역 실내 실제 사진"
  },
  "sapporo-d3-03": {
    "files": [
      "Shiroi Koibito (1).jpg",
      "Shiroi koibito.jpg"
    ],
    "note": "홋카이도 실제 기념품 시로이코이비토"
  },
  "sendai-d3-01": {
    "files": [
      "JRE-Sendai-STA West.jpg",
      "仙台駅の外観.jpg"
    ],
    "note": "센다이역 실제 외관"
  },
  "sendai-d2-08": {
    "files": [
      "牛タン定食（牛タン焼専門店司西口名掛丁店・仙台）20220312-P1330639.jpg",
      "Gyutan teishoku.JPG"
    ],
    "note": "센다이 규탄 정식 실제 음식사진"
  },
  "shizuoka-d3-01": {
    "files": [
      "Shizuoka Station Shinkansen Ticket Gate.jpg",
      "Shizuoka station Shinkansen wicket & ASTY-east gate.jpg"
    ],
    "note": "시즈오카역 신칸센 개찰구 실제 사진"
  },
  "shizuoka-d2-09": {
    "files": [
      "Hotel Associa Shizuoka.JPG",
      "Hotel Century Shizuoka.JPG"
    ],
    "note": "시즈오카역 근처 호텔 예시, 실제 선택 호텔은 미정"
  },
  "shizuoka-d3-03": {
    "files": [
      "Shizoka oden 2 20151022.jpg",
      "Shizoka oden 10 20151022.jpg"
    ],
    "note": "시즈오카 오뎅 실제 음식사진"
  },
  "takamatsu-d2-03": {
    "files": [
      "Kamatama-Udon of Gaina-seimenjo Mar 2026.jpg",
      "Japanese Sanuki Udon.jpg"
    ],
    "note": "카가와현 사누키 우동 참고사진, 고토히라 식당은 미정"
  },
  "tokyo-d1-07": {
    "files": [
      "LaQua at night 20141213, 002.jpg",
      "LaQua @ Tokyo Dome City (9332288017).jpg",
      "Laqua 2.jpg"
    ],
    "note": "스파 라쿠아 실제 시설 외관, 욕탕 실내 사진은 아님"
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
 (ROOT/'photo_audit/curated_last14.json').write_text(
  json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('CURATED UNIQUE',report['unique'],'/281 REMAINING',report['remaining_duplicates'],flush=True)
if __name__=='__main__':main()
