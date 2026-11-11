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
 'shizuoka-d1-03':('マグロの漬け丼---2024-07-05.jpg','시즈오카 참치덮밥 점심의 음식 참고사진 · 실제 가게 미정'),
 'shizuoka-d2-08':('Hachi-no-ji（Japanese sweets in Shizuoka）.jpg','시즈오카 지역 실제 과자·디저트 참고사진 · 특정 카페 미정'),
 'sendai-d2-04':('AKIU Village agrie.JPG','센다이 아키우 온천 지역 실제 식품판매·휴식 시설 · 식당 확정 아님'),
 'kumamoto-d2-04':('Kumamoto ramen by woinary in Kumamoto.jpg','구마모토 시내에서 촬영된 라멘 점심 참고 · 에즈호 인근 식당 확정 아님'),
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
 (AUDIT/'final_semantic_replacements_round3.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('FINAL SEMANTIC REPLACEMENTS',summary['replaced'],'/',summary['total'],'errors:',dict(source.errors),flush=True)
 return 0
if __name__=='__main__':sys.exit(main())
