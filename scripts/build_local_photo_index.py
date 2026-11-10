#!/usr/bin/env python3
"""Rebuild the actual-image index without destroying verified source/author/license metadata.

Keep provenance only when the physical JPEG bytes still match its recorded Git blob SHA.
A new JPEG gets the corresponding catalog's source, never an unrelated manifest link.
"""
from pathlib import Path
import hashlib, json
from PIL import Image

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'assets/photo_manifest_281.json').read_text(encoding='utf-8'))
index_file=root/'assets/local_schedule_photos.json'
old=json.loads(index_file.read_text(encoding='utf-8')) if index_file.is_file() else {}
original=json.loads((root/'assets/recommended.json').read_text(encoding='utf-8'))['cities']
new=json.loads((root/'assets/new_routes.json').read_text(encoding='utf-8'))['cities']
gallery=json.loads((root/'assets/gallery.json').read_text(encoding='utf-8'))
data={}
for row in manifest:
 key=row['key'];p=root/row['local_path']
 if not p.is_file():continue
 try:
  with Image.open(p) as img:
   img.verify()
  with Image.open(p) as img:
   if img.width<100 or img.height<90:continue
 except (OSError,ValueError,SyntaxError):continue
 contents=p.read_bytes()
 blob_sha=hashlib.sha1(f'blob {len(contents)}\\0'.encode()+contents).hexdigest()
 previous=old.get(key,{})
 if previous.get('source_proof_blob_sha')==blob_sha:
  item=previous.copy()
 else:
  city=(new if row['category']=='new' else original)[row['city']]
  schedule=city['days'][row['day']-1][row['step']-1]
  pool=city.get('photos',[]) if row['category']=='new' else gallery.get(row['city'],[])
  current=next((v for v in pool if v.get('file')==schedule.get('photo_file')),None)
  item={'source':(current or {}).get('source',''),
        'author':(current or {}).get('author',''),
        'license':(current or {}).get('license',''),
        'license_url':(current or {}).get('license_url',''),
        'match':schedule.get('photo_match',''),
        'source_verified_by':'current_catalog_for_changed_image'}
  if not item['source']:
   item['source_verified_by']='MISSING_SOURCE'
 item['url']='./'+row['local_path']
 item['place']=row.get('place','')
 item['source_proof_blob_sha']=blob_sha
 data[key]=item
index_file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')
print(f'Index built: {len(data)}/{len(manifest)} verified local files, '
      f'{sum(bool(x.get("source")) for x in data.values())} with source, '
      f'{sum(bool(x.get("license")) for x in data.values())} with recorded license')
