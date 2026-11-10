#!/usr/bin/env python3
"""Validate that all 281 itinerary photos were physically downloaded before calling output a final build."""
import json, sys, zipfile, argparse
from pathlib import Path
from PIL import Image, UnidentifiedImageError
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--package',action='store_true');a=p.parse_args()
 tasks=json.loads((ROOT/'assets/photo_manifest_281.json').read_text('utf-8'))
 if len(tasks)!=281:raise SystemExit(f'Unexpected schedule count {len(tasks)} (expected 281)')
 missing=[];invalid=[]
 for x in tasks:
  pic=ROOT/x['local_path']
  if x['status']!='downloaded' or not pic.exists():missing.append(x)
  else:
   try:
    with Image.open(pic) as im:im.verify()
   except (UnidentifiedImageError,OSError,ValueError):invalid.append(x)
 out=ROOT/'PHOTO_VERIFICATION_REPORT.md'
 lines=['# JAPAN ATLAS 281개 일정의 실사진 검증 결과','',f'- 일정: 281개',f'- 파일 확인: {281-len(missing)-len(invalid)}개',f'- 누락: {len(missing)}개',f'- 이미지 손상: {len(invalid)}개','',
        '## 아직 미완료된 항목','', '| 도시 | 일차 | 번호 | 일정 | 위치 | 상태 |','|---|---:|---:|---|---|---|']
 for x in missing+invalid:
  lines.append(f"| {x['city']} | {x['day']} | {x['step']} | {x['title'].replace('|','/')} | {x['place'].replace('|','/')} | {'손상' if x in invalid else '미확보'} |")
 out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(f'Physical images: {281-len(missing)-len(invalid)}/281; missing: {len(missing)}, invalid: {len(invalid)}')
 if a.package:
  if missing or invalid:
   print('NOT creating a final ZIP; all 281 real image files are required.',file=sys.stderr);return 2
  result=ROOT/'JAPAN_ATLAS_281_REAL_PHOTOS_FINAL.zip'
  with zipfile.ZipFile(result,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for f in ROOT.rglob('*'):
    if f.is_file() and f!=result and '.git' not in f.parts and f.suffix!='pyc' and '__pycache__' not in f.parts:
     z.write(f,f.relative_to(ROOT))
  print('FINAL FILE',result)
 return 1 if missing or invalid else 0

if __name__=='__main__':sys.exit(main())
