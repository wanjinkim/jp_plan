#!/usr/bin/env python3
"""Repair manually checked itinerary/photo contradictions with named Commons files.

Only photographs explicitly selected for an itinerary subject are imported.
No random nearest-match APIs, no existing-image re-use, SHA-unique JPEGs,
original source/author/license recorded with each replacement.
"""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from repair_all_schedule_photos import Sources, get, image_bytes_ok

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
AUDIT=ROOT/'photo_audit'
# Each line was reviewed against the actual 2026-11-11 itinerary and source-page subject.
# Context examples are explicitly distinguished from an exact booked venue.
TARGETS={
 'hiroshima-d2-10':('2013-09-01 a hotel room in Hiroshima 02.jpg','숙소 객실 참고사진 · 실제 예약 호텔 미정'),
 'hiroshima-d3-03':('Nishikidō.jpg','히로시마역 니시키도 모미지만주 매장 · 기념품 쇼핑'),
 'sapporo-d1-08':('Hotel Route Inn Sapporo-Ekimae-Kitaguchi.JPG','삿포로역 인근 호텔 외관 참고 · 실제 예약 호텔 미정'),
 'sapporo-d2-09':('JR-EAST.HOTEL-METS-Sapporo.JPG','삿포로역 인근 호텔 외관 참고 · 실제 예약 호텔 미정'),
 'nagoya-d2-08':('Meitetsu Inn Nagoyaeki Shinkansenguchi.jpg','나고야역 인근 메이테츠인 실제 건물 · 실제 예약 호텔 미정'),
 'sendai-d3-03':('Zunda-mochi.jpg','센다이 대표 기념 간식 즈다모치 실제 음식사진'),
 'sendai-d3-04':('Sedaigyutantei200607.jpg','센다이 규탄 정식 실제 음식사진'),
 'fukuoka-d3-03':('Ramen shin shin.jpg','후쿠오카 라멘 신신 실제 하카타 라멘 · 식당 방문 확정 아님'),
 'osaka-d1-06':('CAFE Lab. in Knowledge Capital, Grand Front Osaka 20130928.jpg','우메다 그랑프론트 오사카의 실제 카페'),
 'osaka-d2-09':('Hokkyoku no ice candy.jpg','오사카 난바 호쿠교쿠 아이스캔디 · 간식 참고'),
 'osaka-d3-01':('Hotel KEIHAN Namba Grande.jpg','난바 지역 호텔 실제 외관 · 실제 예약 호텔 미정'),
 'tokyo-d3-04':('Tempura restaurant by clanchou in Asakusa, Tokyo.jpg','도쿄 아사쿠사의 실제 텐푸라 음식점 외관 · 방문 식당 미정'),
 'matsuyama-d1-08':('Jako-ten and Dogo beer by Hyougushi in Dogo Onsen, Ehime.jpg','도고온천 지역 자코텐과 지역 맥주 실제 음식사진'),
 'matsuyama-d2-07':('Jako-ten udon by woinary in Matsuyama, Ehime.jpg','마쓰야마 지역 자코텐 우동 실제 음식사진'),
 'takamatsu-d2-07':('Fish sashimi.jpg','해산물 저녁 메뉴 중 사시미 참고사진 · 고정 식당 미정'),
 'kumamoto-d1-09':('KKR Hotel Kumamoto 20230227.jpg','구마모토 시내 호텔 실제 건물 · 실제 예약 호텔 미정'),
 'kumamoto-d2-10':('MIELPARQUE Kumamoto 202512.jpg','구마모토 시내 숙박시설 실제 외관 · 실제 예약 호텔 미정'),
 'kumamoto-d3-01':('Richmond Hotels single bedroom 20110806-001.jpg','구마모토현 숙박시설 객실 참고사진 · 실제 예약 호텔 미정'),
}
def git_blob_sha(path):
 body=path.read_bytes()
 return hashlib.sha1(f'blob {len(body)}\0'.encode()+body).hexdigest()

def main():
 source=Sources()
 manifests=json.loads((ASSETS/'photo_manifest_281.json').read_text(encoding='utf-8'))
 lookup={x['key']:x for x in manifests}
 idxp=ASSETS/'local_schedule_photos.json'
 idx=json.loads(idxp.read_text(encoding='utf-8'))
 originals=json.loads((ASSETS/'recommended.json').read_text(encoding='utf-8'))
 new=json.loads((ASSETS/'new_routes.json').read_text(encoding='utf-8'))
 gallery=json.loads((ASSETS/'gallery.json').read_text(encoding='utf-8'))
 hashes={git_blob_sha(ROOT/x['local_path']) for x in manifests if (ROOT/x['local_path']).is_file()}
 results=[]
 for n,(key,(filename,note)) in enumerate(TARGETS.items(),1):
  row=lookup[key];p=ROOT/row['local_path']
  outcome={'id':key,'requested_file':filename,'status':'UNRESOLVED','previous_source':idx.get(key,{}).get('source',''),'scope':note}
  records=source.commons_info(filename)
  for sourcephoto in records[:3]:
   tmp=p.with_name(p.stem+'-semantic-candidate.jpg')
   try:
    data=get(sourcephoto['url'],accept='image/*',timeout=26,retries=3)
    if not image_bytes_ok(data,tmp):
     outcome['reason']='Image did not decode as valid photograph'
     continue
    sha=git_blob_sha(tmp)
    if sha in hashes:
     outcome['reason']='Duplicate photograph hash already present in other itinerary'
     tmp.unlink(missing_ok=True)
     continue
    tmp.replace(p);hashes.add(sha)
    category=new if row['category']=='new' else originals
    city=category['cities'][row['city']]
    step=city['days'][row['day']-1][row['step']-1]
    pool=city['photos'] if row['category']=='new' else gallery[row['city']]
    file_id='LOCAL-'+key+'.jpg'
    record={'file':file_id,'title':row['title'],'place':row['place'],'kind':step.get('kind','일정'),
     'local':'./'+row['local_path'],'local_verified':True,
     'source':sourcephoto['source'],'author':sourcephoto.get('author',''),'license':sourcephoto.get('license',''),
     'license_url':sourcephoto.get('license_url',''),'scope':note}
    pool[:]=[entry for entry in pool if entry.get('file')!=file_id]+[record]
    step['photo_file']=file_id
    step['photo_match']=note
    idx[key]={'url':'./'+row['local_path'],'source':sourcephoto['source'],
      'place':row['place'],'author':sourcephoto.get('author',''),
      'license':sourcephoto.get('license',''),'license_url':sourcephoto.get('license_url',''),
      'match':'curated_schedule_activity','description_scope':note,
      'source_verified_by':'curated_specific_file_subject','source_proof_blob_sha':sha}
    outcome.update(status='REPLACED',source=sourcephoto['source'],license=sourcephoto.get('license',''),
      author=sourcephoto.get('author',''),sha=sha)
    break
   except Exception as exc:
    outcome['reason']=str(exc)[:200]
   finally:tmp.unlink(missing_ok=True)
  if not records:
   outcome['reason']='No permitted Commons image found for exact requested filename'
  results.append(outcome)
  print(f'[{n}/{len(TARGETS)}] {key}: {outcome["status"]} {outcome.get("reason","")}',flush=True)
 # Write only source mappings for actually downloaded replacements.
 for filename,obj in [('assets/recommended.json',originals),('assets/new_routes.json',new),
       ('assets/gallery.json',gallery),('assets/local_schedule_photos.json',idx)]:
  (ROOT/filename).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 summary={'total':len(TARGETS),'replaced':sum(x['status']=='REPLACED' for x in results),
          'unresolved':sum(x['status']!='REPLACED' for x in results),
          'items':results,'api_errors':dict(source.errors)}
 (AUDIT/'final_semantic_replacements.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('FINAL SEMANTIC REPLACEMENTS',summary['replaced'],'/',summary['total'],'errors:',dict(source.errors),flush=True)
 return 0
if __name__=='__main__':sys.exit(main())
