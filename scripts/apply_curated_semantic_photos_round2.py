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
 'hiroshima-d3-05':('644-3957 Chugoku U-MS826P Limousine.jpg','히로시마역 출발 공항 리무진 버스 실제 차량 사진'),
 'sendai-d2-01':('Sendaicitybus-5736.jpg','센다이역 서쪽 버스 승강장 차량 참고 · 아키우행 확정 차량은 아님'),
 'osaka-d3-04':('Nankai50000Series Rapit01s4s2880.jpg','간사이공항역의 난카이 공항열차 실제 모습'),
 'tokyo-d2-09':('Hotel Sunroute Stella Ueno.JPG','우에노역 인근 호텔 실제 외관 · 예약 호텔 미정'),
 'takamatsu-d1-08':('JR-Hotel Clement-Takamatsu.jpg','다카마쓰역 인근 숙박시설 실제 외관 · 예약 호텔 미정'),
 'takamatsu-d2-09':('ANA Hotel Clement Takamatsu01s3872.jpg','다카마쓰역 인근 숙박시설 실제 외관 · 예약 호텔 미정'),
 'takamatsu-d3-01':('ANA Hotel Clement Takamatsu02s3872.jpg','다카마쓰역 인근 숙박시설 실제 외관 · 예약 호텔 미정'),
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
