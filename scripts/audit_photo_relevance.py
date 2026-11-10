#!/usr/bin/env python3
"""JAPAN ATLAS: independently auditable image-to-itinerary inspection.
Does not mistake a decodable image or a generic reference for a verified venue.
Creates one row per itinerary and human-review contact sheets for every city.
"""
from __future__ import annotations
import csv, json, re, urllib.parse
from collections import Counter
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'photo_audit'
OUT.mkdir(exist_ok=True)
ROWS=json.loads((ROOT/'assets/photo_manifest_281.json').read_text(encoding='utf-8'))
OLD=json.loads((ROOT/'assets/recommended.json').read_text(encoding='utf-8'))['cities']
NEW=json.loads((ROOT/'assets/new_routes.json').read_text(encoding='utf-8'))['cities']
GALLERY=json.loads((ROOT/'assets/gallery.json').read_text(encoding='utf-8'))
INDEX=json.loads((ROOT/'assets/local_schedule_photos.json').read_text(encoding='utf-8'))
TASKS={x['id']:x for x in json.loads((ROOT/'assets/photo_tasks.json').read_text(encoding='utf-8'))}
CITIES=['hiroshima','shizuoka','sapporo','nagoya','okinawa','sendai',
        'fukuoka','osaka','tokyo','matsuyama','takamatsu','kumamoto']
# Strong contradictions, NOT general labels that could plausibly accompany the activity.
PHOTO_CATEGORY={
 'airport':r'airport|terminal|空港|aeropuerto|flug|runway',
 'station':r'station|駅|rail|train|電車|subway|metro|trams',
 'onsen':r'onsen|温泉|湯|hot.spring|spa|bath',
 'park':r'park|garden|公園|庭園|lake|forest',
 'meal':r'ramen|ラーメン|udon|うどん|soba|そば|sushi|寿司|curry|カレー|okonomiyaki|お好み焼き|food|dish|meat|steak|牛タン|牡蠣|taco|noodle|hotel.*restaurant',
 'hotel':r'hotel|inn|ryokan|ホテル|旅館|room|guesthouse',
 'shrine':r'shrine|神社|寺|temple|castle|城',
 'market':r'market|street|shopping|mall|商店|商店街'
}
OTHER_LOCATIONS=r'office|市役所|支所|city.office|government|prefectur|博物館|museum|school|university|教会|church'
def normalize(s):
 return re.sub(r'[^\\w\\u3040-\\u9fff]+','',str(s or '').casefold(),flags=re.UNICODE)
def filename(src):
 try:return urllib.parse.unquote((src.split('/File:')[-1] if '/File:' in src else '').split('?')[0]).replace('_',' ')
 except Exception:return ''
def activity_category(title,place,kind):
 s=' '.join((title,place,kind)).lower()
 if re.search(r'온천|입욕|노천탕|おんせん|温泉|spa|hot.spring',s):return 'onsen'
 if re.search(r'라멘|우동|스시|초밥|점심|저녁|먹거리|맛집|식사|향토|타코|간식|디저트',s):return 'meal'
 if re.search(r'공항|空港|출국|입국|flight',s):return 'airport'
 if re.search(r'호텔|숙소|객실|휴식|체크아웃|짐 보관|수하물|ホテル',s):return 'hotel'
 if re.search(r'전철|열차|역|駅|JR|지하철|버스|페리|노면전차',s):return 'station'
 if re.search(r'공원|정원|公園|庭園|숲길|폭포|호수|연못',s):return 'park'
 if re.search(r'신사|사찰|성|절|神社|寺|城',s):return 'shrine'
 if re.search(r'시장|상점|쇼핑|商店',s):return 'market'
 return 'other'
def row_info(task):
 key=task['key'];city=task['city'];raw=(NEW if task['category']=='new' else OLD)[city]
 entry=raw['days'][task['day']-1][task['step']-1]
 pool=raw.get('photos',[]) if task['category']=='new' else GALLERY.get(city,[])
 item=next((p for p in pool if p.get('file') and p.get('file')==entry.get('photo_file')),None)
 loc=INDEX.get(key,{})
 source=(item or {}).get('source') or loc.get('source') or task.get('source') or ''
 file=filename(source)
 desc=entry.get('photo_scope') or entry.get('photo_match') or (item or {}).get('scope') or ''
 picture=ROOT/task['local_path']
 ok=False;dimensions=''
 if picture.is_file():
  try:
   with Image.open(picture) as im:
    im.verify()
   with Image.open(picture) as im:
    ok=(im.width>=100 and im.height>=90)
    dimensions=f'{im.width}x{im.height}'
  except Exception:pass
 category=activity_category(task.get('title',''),task.get('place',''),entry.get('kind',''))
 # Category contradiction rules are conservative: a hotel is not the onsen, and
 # a government office is not the named hot spring.
 contradiction=[]
 if category=='onsen' and file and not re.search(PHOTO_CATEGORY['onsen'],file,re.I):
  contradiction.append('온천 일정인데 사진 파일명에 온천/탕/스파의 근거가 없음')
 if category=='meal' and file and not re.search(PHOTO_CATEGORY['meal'],file,re.I):
  contradiction.append('음식 일정인데 사진 파일명에 음식의 근거가 없음')
 if category=='airport' and file and re.search(OTHER_LOCATIONS,file,re.I):
  contradiction.append('공항 일정에 무관한 시설/건물이 연결됨')
 if category=='park' and file and re.search(r'hotel|airport|food|restaurant|office|station|港',file,re.I):
  contradiction.append('공원·자연 일정에 다른 시설 사진이 연결됨')
 if category=='onsen' and file and re.search(OTHER_LOCATIONS,file,re.I):
  contradiction.append('온천과 관계없는 관공서 또는 기관 건물')
 if re.search('실제 시설.*다를 수 있음',desc) and category in ('onsen','park','airport','shrine'):
  contradiction.append('기존 데이터가 관련 지역 참고사진임을 인정함')
 # Only positive metadata-based evidence, NOT a claim of photo visual verification.
 place=normalize(task.get('place',''))
 doc=normalize(file+' '+desc)
 venue_match=bool(place and len(place)>3 and place in doc)
 candidates=TASKS.get(key,{}).get('search_keywords','')
 eng_tokens=[x.lower() for x in re.findall(r'[a-z]{5,}',candidates) if x.lower() not in
            {'japan','international','terminal','station','airport','onsen','hotel','nature','travel','japanese','temple','garden'}]
 token_hits=[x for x in eng_tokens if x in file.lower()]
 if not ok:state='MISSING_OR_INVALID'
 elif contradiction:state='MISMATCH_REVIEW'
 elif not source:state='SOURCE_UNKNOWN'
 elif venue_match or token_hits:state='METADATA_MATCH_CANDIDATE'
 else:state='NEEDS_VISUAL_REVIEW'
 return dict(key=key,city=city,day=task['day'],step=task['step'],
             place=task.get('place',''),title=task['title'],kind=entry.get('kind',''),
             category=category,source=source,source_filename=file,photo_scope=desc,
             image_path=task['local_path'],image_ok=ok,dimensions=dimensions,
             status=state,metadata_matches=', '.join(token_hits),
             warnings='; '.join(contradiction),
             verified_place=False,verified_license=False,
             # Visual and license validation must be established separately.
             verified_method='filename_and_catalog_audit')
def contact_sheet(city,rows):
 photos=[r for r in rows if r['city']==city]
 width=1536;cw=300;ch=215;cols=5
 height=32+((len(photos)+cols-1)//cols)*ch
 board=Image.new('RGB',(width,height),(246,247,248))
 draw=ImageDraw.Draw(board)
 try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
 except Exception:font=ImageFont.load_default()
 draw.text((14,8),city+'  |  local schedule images / metadata audit',font=font,fill=(20,26,35))
 for j,r in enumerate(photos):
  x=10+(j%cols)*305;y=36+(j//cols)*ch
  p=ROOT/r['image_path']
  if r['image_ok']:
   try:
    with Image.open(p) as raw:
     img=ImageOps.fit(raw.convert('RGB'),(294,160),method=Image.Resampling.LANCZOS)
     board.paste(img,(x,y))
   except Exception:pass
  if not r['image_ok']:draw.rectangle((x,y,x+294,y+160),fill=(217,222,227))
  draw.text((x,y+162),r['key']+' '+r['status'][:11],font=font,fill=(35,40,48))
  name=(r['source_filename'] or 'NO SOURCE')[:45]
  draw.text((x,y+182),name,font=font,fill=(100,45,45) if r['warnings'] else (65,76,89))
 board.save(OUT/(city+'.jpg'),quality=80,optimize=True)
 return str(OUT.relative_to(ROOT)/(city+'.jpg'))
def main():
 data=[row_info(task) for task in ROWS]
 assert len(data)==281 and len({r['key'] for r in data})==281
 fields=list(data[0].keys())
 with (OUT/'semantic_audit_281.csv').open('w',encoding='utf-8-sig',newline='') as f:
  out=csv.DictWriter(f,fieldnames=fields);out.writeheader();out.writerows(data)
 counts=dict(Counter(x['status'] for x in data))
 summary={'total':len(data),'files_present':sum(x['image_ok'] for x in data),
          'status_counts':counts,'verified_place':0,
          'note':'Metadata audit is not a visually confirmed 281-image semantic check. All candidates require visual or original-source verification.',
          'city_previews':{city:contact_sheet(city,data) for city in CITIES},
          'items':data}
 (OUT/'semantic_audit_281.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')
 print('SEMANTIC PHOTO AUDIT:',json.dumps(counts,ensure_ascii=False))
 print('Validated local photos:',summary['files_present'],'/ 281')
 print('Saved 12 city contact sheets to photo_audit')
if __name__=='__main__':main()
