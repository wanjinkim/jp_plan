#!/usr/bin/env python3
"""Targeted semantic repair for visibly mismatched itinerary photos.

Use Wikimedia Commons licensed bytes, Wikipedia page images, and Wikidata P18,
never unrelated stock or other onsen. Every replacement records its actual source.
"""
from __future__ import annotations
import argparse, json, re, sys, time, urllib.parse
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repair_all_schedule_photos import Sources, CITIES, image_bytes_ok, get, normal, exact_venue

VISUAL=ROOT/'photo_audit/visual_screening_281.json'
DATA=ROOT/'assets'
# Deliberately specific English variants for names that are absent from original photo tasks.
SEARCH={
'hiroshima-d1-08':['Nagarekawa Hiroshima street at night','流川 広島 夜景'],
'hiroshima-d1-09':['Hiroshima hotel guest room','広島 ホテル 客室'],
'hiroshima-d2-08':['宇品天然温泉 ほの湯','Ujina Honoyu hot spring Hiroshima'],
'hiroshima-d2-09':['Hiroshima okonomiyaki food','広島 お好み焼き'],
'hiroshima-d2-10':['Hiroshima hotel guest room','広島 ホテル'],
'hiroshima-d3-04':['Hiroshima okonomiyaki','Hiroshima ramen'],
'hiroshima-d3-05':['Hiroshima station airport bus','広島駅 空港リムジン バス'],
'shizuoka-d1-08':['Hotel Shizuoka station','静岡駅 ホテル'],
'shizuoka-d2-05':['草薙駅','Kusanagi Station Shizuoka'],
'shizuoka-d2-06':['あおい温泉 草薙の湯','Kusanagi no Yu onsen Shizuoka'],
'shizuoka-d2-07':['Shizuoka oden dish','静岡 おでん'],
'shizuoka-d2-08':['Shizuoka dessert night','静岡 抹茶 ジェラート'],
'shizuoka-d2-09':['Shizuoka station hotel','静岡 ホテル'],
'shizuoka-d3-04':['Shizuoka Station bus terminal','静岡駅 空港バス'],
'sapporo-d1-07':['Sapporo Ramen Yokocho','元祖さっぽろラーメン横丁'],
'sapporo-d1-08':['Sapporo Station hotel','札幌駅 ホテル'],
'sapporo-d2-05':['Jozankei onsen day bath','定山渓温泉 日帰り入浴'],
'sapporo-d2-09':['Sapporo station hotel','札幌駅 ホテル'],
'nagoya-d2-03':['Hitsumabushi Nagoya grilled eel','ひつまぶし 名古屋'],
'nagoya-d2-05':['Urban Quar onsen Nagoya','天然温泉 アーバンクア'],
'nagoya-d2-06':['Nagoya Station Japanese dinner','名古屋駅 名古屋めし'],
'nagoya-d3-04':['Meitetsu Nagoya Station','名鉄名古屋駅'],
'okinawa-d1-06':['Ryukyu Onsen Ryujin no Yu Okinawa','琉球温泉 龍神の湯'],
'okinawa-d2-05':['Okashigoten Onna store Okinawa','御菓子御殿 恩納店'],
'okinawa-d2-09':['Okinawa taco rice','タコライス 那覇'],
'okinawa-d2-10':['Kokusai dori Okinawa night','国際通り 夜景'],
'sendai-d2-02':['Akiu Onsen Sendai','秋保温泉'],
'sendai-d2-05':['Akiu Grand Hotel onsen','秋保グランドホテル 温泉'],
'sendai-d2-10':['Sendai Station hotel','仙台駅 ホテル'],
'sendai-d3-04':['Sendai gyutan teishoku','仙台 牛タン定食'],
'fukuoka-d2-02':['Meinohama Ferry Terminal Fukuoka','姪浜渡船場'],
'fukuoka-d2-04':['Nokonoshima Island Park restaurant','のこのしまアイランドパーク レストラン'],
'fukuoka-d2-05':['Nokonoshima Fukuoka Hakata bay','能古島 博多湾'],
'fukuoka-d2-07':['Hakata cafe coffee','博多駅 カフェ'],
'fukuoka-d2-08':['Hakata izakaya Japanese dinner','博多 居酒屋'],
'fukuoka-d2-09':['Nakasu Fukuoka river night','中洲 夜景'],
'fukuoka-d2-10':['Hakata hotel room','博多 ホテル'],
'fukuoka-d3-02':['Sumiyoshi Shrine Fukuoka','住吉神社 福岡'],
'fukuoka-d3-03':['Hakata ramen','博多ラーメン'],
'osaka-d1-01':['Kansai International Airport terminal','関西国際空港'],
'osaka-d1-07':['Tenjinbashisuji kushikatsu Osaka','天神橋筋 串カツ'],
'osaka-d1-08':['Naniwa no Yu Osaka onsen','天然温泉 なにわの湯'],
'osaka-d2-07':['Umeda izakaya Japanese dinner','梅田 居酒屋'],
'osaka-d3-05':['Kansai International Airport departure lobby','関西空港 出発'],
'tokyo-d1-04':['Ueno Park autumn foliage','上野恩賜公園 紅葉'],
'tokyo-d1-07':['Spa LaQua Tokyo Dome onsen','東京ドーム天然温泉 Spa LaQua'],
'tokyo-d2-02':['Shinjuku Gyoen autumn foliage','新宿御苑 紅葉'],
'tokyo-d2-09':['Ueno Station hotel','上野駅 ホテル'],
'tokyo-d3-04':['Asakusa Japanese food restaurant','浅草 食事'],
'matsuyama-d1-01':['Matsuyama Airport Ehime terminal','松山空港'],
'matsuyama-d1-03':['Matsuyama Castle Ropeway','松山城ロープウェイ'],
'matsuyama-d1-05':['Ehime tai meshi fish rice','愛媛 鯛めし'],
'matsuyama-d1-08':['Ehime local food Matsuyama','道後 郷土料理'],
'matsuyama-d2-08':['Dogo Onsen Station at night','道後温泉駅 夜景'],
'matsuyama-d3-03':['Matsuyama tai meshi lunch','松山 鯛めし'],
'matsuyama-d3-05':['Matsuyama Airport departure terminal','松山空港 出発'],
'takamatsu-d1-03':['Sanuki Udon Takamatsu','讃岐うどん 高松'],
'takamatsu-d1-06':['Busshozan Onsen Tenpyouyu','仏生山温泉 天平湯'],
'takamatsu-d1-08':['Takamatsu hotel night','高松駅 ホテル'],
'takamatsu-d2-03':['Kotohira udon restaurant','琴平 うどん'],
'takamatsu-d2-05':['Sunport Takamatsu harbour','サンポート高松'],
'takamatsu-d2-09':['Takamatsu Station hotel','高松駅 ホテル'],
'takamatsu-d3-03':['Sanuki Udon Takamatsu','讃岐うどん'],
'takamatsu-d3-04':['Takamatsu Airport limousine bus','高松空港 リムジンバス'],
'kumamoto-d1-07':['Kumamoto horse meat sashimi','熊本 馬刺し'],
'kumamoto-d2-04':['Kumamoto lake Ezu lunch','江津湖 レストラン'],
'kumamoto-d2-08':['Kumamoto Shimotori dinner','下通 熊本 食事'],
'kumamoto-d2-09':['Hanabata Square Kumamoto night','花畑広場 夜景'],
'kumamoto-d3-03':['Kumamoto ramen dish','熊本ラーメン']
}
# Require these distinctive words/venue phrases in file title or Commons description.
# A city name by itself is not evidence of the requested facility/activity.
REQUIRED={
'hiroshima-d2-08':['honoyu','honoyu','ほの湯','宇品天然温泉'],
'shizuoka-d2-06':['草薙の湯','kusanaginoyu','kusanagi no yu'],
'sapporo-d2-05':['jozankei','定山渓'],
'nagoya-d2-05':['urban quar','urbanquar','アーバンクア'],
'okinawa-d1-06':['ryujin no yu','龍神の湯','琉球温泉'],
'sendai-d2-05':['akiu grand','秋保グランドホテル'],
'fukuoka-d3-02':['住吉神社','sumiyoshi shrine'],
'osaka-d1-08':['naniwa no yu','なにわの湯','naniwanoyu'],
'tokyo-d1-07':['laqua','ラクーア'],
'takamatsu-d1-06':['仏生山温泉','busshozan onsen'],
}
CATEGORY={
'onsen':['onsen','温泉','yu','湯','spa','bath'],
'meal':['ramen','ラーメン','udon','うどん','soba','そば','yakitori','food','dish','teishoku',
        'gyutan','牛タン','beef','fish','sashimi','寿司','okonomiyaki','お好み焼き','curry',
        'izakaya','居酒屋','鯛めし','海鮮','丼','天ぷら','tempura','katsu','restaurant'],
'station':['station','駅','terminal','rail','train','bus','shuttle','ferry','港'],
'airport':['airport','空港','terminal','departure','departure hall'],
'hotel':['hotel','ホテル','inn','room','ryokan','旅館','guest'],
'park':['park','garden','公園','庭園','autumn','foliage','sea','bay','湖','river','harbor','port'],
'other':[]
}
ENGLISH_STOP={'japan','japanese','travel','photo','image','international','station','airport',
              'terminal','the','and','from','for','city','onsen','hotel','park','restaurant','of'}
def plain(s):
 return re.sub(r'\s+',' ',str(s or '')).lower()
def normalized(s):return re.sub(r'[^\w一-龯ぁ-んァ-ン]+','',plain(s),flags=re.UNICODE)
def strict_match(photo,key,title,task):
 subject=plain(photo['title']+' '+photo.get('desc',''))
 stripped=normalized(subject)
 required=REQUIRED.get(key)
 if required and not any(normalized(q) in stripped for q in required):
  return False,0
 # Do not pick different named hot springs or generic city photos.
 if key in REQUIRED and any(x in title for x in ['온천','湯']) and not any(x in subject for x in CATEGORY['onsen']):
  if key not in ('fukuoka-d3-02',):return False,0
 termlist=SEARCH.get(key,[])
 english=[w.lower() for q in termlist for w in re.findall(r'[a-zA-Z]{4,}',q)
          if w.lower() not in ENGLISH_STOP]
 matches=set(w for w in english if w in subject)
 place=task['place']
 exact=bool(place and len(normalized(place))>=4 and normalized(place) in stripped)
 if key in ('tokyo-d1-04','tokyo-d2-02') and any(x in subject for x in ['sakura','cherry','spring','桜']):
  return False,0
 if '야경' in title or 'night' in plain(title):
  if not any(x in subject for x in ['night','evening','dusk','sunset','夜景','夜間','夜']):
   return False,0
 # Distinctive venue or keyword evidence required: no generic placeholder images.
 if not exact and not matches and not required:return False,0
 # Generic activity photos must depict the requested type, not a district road.
 title_low=plain(title)
 if re.search('점심|저녁|음식|라멘|우동|미식|밥',title):
  if not any(x in subject for x in CATEGORY['meal']):return False,0
 if re.search('온천|입욕|노천탕',title):
  if not any(x in subject for x in CATEGORY['onsen']):return False,0
 if re.search('호텔|숙소',title) and not any(x in subject for x in CATEGORY['hotel']):
  return False,0
 score=10*int(exact)+min(5,len(matches))*2+5*int(bool(required))
 return (score>=2),score
def candidates(src,key,task):
 # Wiki encyclopedia entity page is independent from the Commons search index.
 aliases=REQUIRED.get(key,[])
 if aliases:
  for term in (task['place'],)+tuple(aliases[:2]):
   for p in src.wikipedia_search(term,aliases):
    yield p
   for p in src.wikidata_image(term,aliases):
    yield p
 else:
  for p in src.wikipedia_image(task['place']):yield p
 seen=set()
 for query in SEARCH.get(key,[task['place']]):
  if query in seen:continue
  seen.add(query)
  for p in src.search_commons(query):
   yield p
def run(limit=0):
 screen=json.loads(VISUAL.read_text(encoding='utf-8'))['rows']
 manifest={m['key']:m for m in json.loads((DATA/'photo_manifest_281.json').read_text(encoding='utf-8'))}
 indices=json.loads((DATA/'local_schedule_photos.json').read_text(encoding='utf-8'))
 old=json.loads((DATA/'recommended.json').read_text(encoding='utf-8'))
 new=json.loads((DATA/'new_routes.json').read_text(encoding='utf-8'))
 gallery=json.loads((DATA/'gallery.json').read_text(encoding='utf-8'))
 source=Sources()
 target=[x for x in screen if x['visual_status'] in ('MISMATCH','MISSING')]
 if limit:target=target[:limit]
 rows=[];updated=0
 for number,review in enumerate(target,1):
  key=review['id'];task=manifest[key]
  files=sorted(((p,sc) for p in candidates(source,key,task)
    if (check:=strict_match(p,key,review['title'],task))[0]
    for sc in [check[1]]),key=lambda x:x[1],reverse=True)
  urls=set();rec={'id':key,'status':'UNRESOLVED','old_source':indices.get(key,{}).get('source',''),'new_source':'','score':0}
  for photo,score in files[:14]:
   if photo['url'] in urls:continue
   urls.add(photo['url'])
   try:
    raw=get(photo['url'],accept='image/*',timeout=18,retries=2)
    if not image_bytes_ok(raw,ROOT/task['local_path']):continue
    obj=new if task['category']=='new' else old
    place=obj['cities'][task['city']]
    schedule=place['days'][task['day']-1][task['step']-1]
    item={'file':'LOCAL-'+key+'.jpg','title':task['title'],'place':task['place'],'kind':schedule.get('kind','일정'),
          'local':'./'+task['local_path'],'local_verified':True,
          'source':photo['source'],'author':photo.get('author',''),'license':photo['license'],
          'license_url':photo.get('license_url',''),'scope':'장소·활동 메타데이터 일치 후보 (사진 재검토 필요)'}
    pool=place['photos'] if task['category']=='new' else gallery[task['city']]
    pool[:]=[p for p in pool if p.get('file')!=item['file']]+[item]
    schedule['photo_file']=item['file']
    schedule['photo_match']=item['scope']
    indices[key]={'url':'./'+task['local_path'],'place':task['place'],
      'source':photo['source'],'author':photo.get('author',''),
      'license':photo['license'],'license_url':photo.get('license_url',''),
      'match':'metadata_candidate','source_verified_by':'direct_commons_download'}
    rec.update(status='REPLACED',new_source=photo['source'],score=score)
    updated+=1
    break
   except Exception as exc:rec['error']=str(exc)[:120]
  rows.append(rec)
  print(f'[{number}/{len(target)}] {key} {rec["status"]}',flush=True)
  if number%10==0:save(old,new,gallery,indices,rows)
 save(old,new,gallery,indices,rows)
 print('RESULT replacements:',updated,'remaining:',sum(x['status']!='REPLACED' for x in rows),'API errors',dict(source.errors))
def save(old,new,gallery,index,rows):
 for filename,data in [('recommended.json',old),('new_routes.json',new),('gallery.json',gallery),
                       ('local_schedule_photos.json',index)]:
  (DATA/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 result={'total_reviewed':len(rows),'replaced':sum(x['status']=='REPLACED' for x in rows),
         'unresolved':sum(x['status']!='REPLACED' for x in rows),'items':rows}
 (ROOT/'photo_audit/relevance_repairs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--limit',type=int,default=0)
 opts=p.parse_args()
 run(opts.limit)
