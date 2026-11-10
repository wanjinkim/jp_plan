#!/usr/bin/env python3
"""Replace two audited mismatches using manually verified, CC-licensed Commons files.

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
 'tokyo-d1-04':{
  'file':'Fall leaves in Tokyo.JPG',
  'aliases':['ueno park','上野公園'],
  'note':'Ueno Park autumn foliage, not cherry blossoms'},
 'nagoya-d2-05':{
  'file':'Urban-quar-Spa-Fujimi-Nagoya.jpg',
  'aliases':['urban-quar','アーバンクア'],
  'note':'Exact Urban Quar SPA & LIVING facility photo'}
}
def clean(s):return normal(s)
def main():
 source=Sources()
 assets=ROOT/'assets'
 manifest={x['key']:x for x in json.loads((assets/'photo_manifest_281.json').read_text(encoding='utf-8'))}
 local_path=assets/'local_schedule_photos.json'
 local=json.loads(local_path.read_text(encoding='utf-8'))
 old=json.loads((assets/'recommended.json').read_text(encoding='utf-8'))
 new=json.loads((assets/'new_routes.json').read_text(encoding='utf-8'))
 gallery=json.loads((assets/'gallery.json').read_text(encoding='utf-8'))
 successes=[]
 errors=[]
 for key,expected in TARGETS.items():
  task=manifest[key]
  results=source.commons_info(expected['file'])
  photo=next((x for x in results if any(clean(alias) in clean(x['title']+' '+x.get('desc','')) for alias in expected['aliases'])),None)
  if not photo:
   errors.append(key+': no verified Commons title, description, and freely licensed photo')
   print(errors[-1],flush=True)
   continue
  path=ROOT/task['local_path']
  try:
   blob=get(photo['url'],accept='image/*',timeout=30,retries=3)
   if not image_bytes_ok(blob,path):raise RuntimeError('Image decoded with invalid dimensions')
   data=path.read_bytes()
   sha=hashlib.sha1(f'blob {len(data)}\0'.encode('utf-8')+data).hexdigest()
  except Exception as exc:
   errors.append(key+': '+str(exc)[:200])
   print(errors[-1],flush=True)
   continue
  target=(new if task['category']=='new' else old)['cities'][task['city']]
  schedule=target['days'][task['day']-1][task['step']-1]
  pool=target['photos'] if task['category']=='new' else gallery[task['city']]
  rec={'file':'LOCAL-'+key+'.jpg','title':task['title'],'place':task['place'],
    'kind':schedule.get('kind','일정'),'local':'./'+task['local_path'],
    'local_verified':True,'source':photo['source'],
    'author':photo.get('author',''),'license':photo['license'],
    'license_url':photo.get('license_url',''),'scope':'해당 장소의 실제 사진 · 일정 관련성 확인'}
  pool[:]=[p for p in pool if p.get('file')!=rec['file']]+[rec]
  schedule['photo_file']=rec['file']
  schedule['photo_match']=rec['scope']
  local[key]={'url':'./'+task['local_path'],'place':task['place'],
   'source':photo['source'],'author':photo.get('author',''),
   'license':photo['license'],'license_url':photo.get('license_url',''),
   'match':'manual_venue_and_season_review',
   'source_verified_by':'commons_file_metadata_and_visual_review',
   'source_proof_blob_sha':sha}
  successes.append({'key':key,'original_filename':expected['file'],
    'source':photo['source'],'license':photo['license'],'author':photo.get('author',''),
    'git_blob_sha':sha,'note':expected['note']})
  print('VERIFIED CURATED IMAGE',key,photo['source'],flush=True)
 # Retain successful outcomes even when a different photo fails.
 for path,obj in [('assets/recommended.json',old),('assets/new_routes.json',new),
    ('assets/gallery.json',gallery),('assets/local_schedule_photos.json',local)]:
  (ROOT/path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (ROOT/'photo_audit/curated_photo_corrections.json').write_text(
  json.dumps({'corrected':len(successes),'photos':successes,'errors':errors},
  ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if len(successes)!=len(TARGETS):
  print('INCOMPLETE CURATED PHOTOS',errors,flush=True)
  return 1
 return 0
if __name__=='__main__':sys.exit(main())
