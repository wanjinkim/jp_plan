#!/usr/bin/env python3
from pathlib import Path
import json
from PIL import Image
root=Path(__file__).resolve().parents[1]
rows=json.loads((root/'assets/photo_manifest_281.json').read_text())
data={}
for r in rows:
 p=root/r['local_path']
 if not p.is_file():continue
 try:
  with Image.open(p) as img:img.verify()
 except Exception:continue
 data[r['key']]={'url':'./'+r['local_path'],'source':r.get('source',''),'place':r.get('place',''),'match':r.get('match_type','unverified')}
(root/'assets/local_schedule_photos.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(f'Index built: {len(data)}/{len(rows)} verified local files')
