#!/usr/bin/env python3
"""Inspect real onsen facility photos: export contacts with actual exact source URL.
DO NOT auto-assign a photo by filename; require visual review first.
"""
from __future__ import annotations
import json,io,re,time,html
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'photo_audit/onsen_candidates'
OUT.mkdir(parents=True,exist_ok=True)
VENUES={
 'hiroshima-d2-08':'https://www.honoyu.jp/ujina/',
 'shizuoka-d2-06':'https://www.kusanagino-yu.com/bath/index.html',
 'okinawa-d1-06':'https://www.resorts.co.jp/senaga/ryujinhotspring',
 'sendai-d2-05':'https://akiugrand.com/',
 'takamatsu-d1-06':'https://busshozan.com/'
}
session=requests.Session()
session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; TripPhotoCheck/1.0; contact via GitHub)','Accept':'text/html,image/*'})
def getpage(url):
 resp=session.get(url,timeout=25)
 resp.raise_for_status()
 resp.encoding=resp.apparent_encoding or resp.encoding
 return resp
def get_candidates(url):
 response=getpage(url)
 soup=BeautifulSoup(response.text,'html.parser')
 found=[]
 for x in soup.select('img,source,meta[property="og:image"],meta[name="twitter:image"]'):
  alt=x.get('alt','') or x.get('title','')
  vals=[]
  for name in ('src','data-src','data-original','data-lazy-src','content','srcset','data-srcset'):
   val=x.get(name)
   if val:
    vals.extend([part.strip().split(' ')[0] for part in val.split(',')] if 'srcset' in name else [val.strip()])
  for val in vals:
   full=urljoin(response.url,val)
   if not full.startswith('https://'):continue
   if not re.search(r'\.(jpe?g|png|webp|avif)(?:[?#]|$)',full,re.I):continue
   found.append({'url':full,'alt':alt,'page':response.url})
 for x in soup.select('[style]'):
  style=x.get('style','')
  for name in re.findall(r'url\([\'"]?([^\'")]+)',style):
   full=urljoin(response.url,name)
   if full.startswith('https://') and re.search(r'\.(jpg|jpeg|png|webp)(?:[?#]|$)',full,re.I):
    found.append({'url':full,'alt':x.get_text(' ',strip=True)[:85],'page':response.url})
 result=[];seen=set()
 for item in found:
  if item['url'] not in seen:
   seen.add(item['url']);result.append(item)
 # Prefer baths/hot spring/venue images but include exact site's architectural shots.
 def score(item):
  s=(item['url']+' '+item['alt']).lower()
  return sum(3 if key in s else 0 for key in ('roten','bath','spa','onsen','ryujin','温泉','露天','内湯','湯','fuji','kusanagi','honoyu','busshozan'))-sum(4 for key in ('logo','icon','banner','sns','map','button') if key in s)
 return sorted(result,key=score,reverse=True)[:28]
def capture(key,url):
 city=key.split('-')[0]
 result={'key':key,'facility':url,'candidates':[],'errors':[]}
 try:items=get_candidates(url)
 except Exception as ex:
  result['errors'].append('HTML fetch: '+str(ex)[:150])
  return result
 thumbnails=[]
 for item in items:
  try:
   time.sleep(.22)
   res=session.get(item['url'],timeout=16)
   res.raise_for_status()
   if len(res.content)>20_000_000:continue
   with Image.open(io.BytesIO(res.content)) as original:
    if original.width<240 or original.height<160:continue
    pic=ImageOps.fit(original.convert('RGB'),(270,165),method=Image.Resampling.LANCZOS)
    result['candidates'].append({**item,'width':original.width,'height':original.height,'size':len(res.content)})
    thumbnails.append(pic)
   if len(thumbnails)>=16:break
  except Exception as ex:
   result['errors'].append(item['url'][:85]+' '+str(ex)[:90])
 if not thumbnails:return result
 cols=4;w=1120;h=24+((len(thumbnails)+3)//cols)*215
 canvas=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(canvas)
 try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
 except:font=ImageFont.load_default()
 d.text((12,5),key+' | official photo candidates',fill=(28,42,56),font=font)
 for i,img in enumerate(thumbnails):
  xx=5+(i%4)*280;yy=24+(i//4)*215;canvas.paste(img,(xx,yy))
  meta=result['candidates'][i]
  d.text((xx,yy+168),str(i+1)+' '+meta['alt'][:37],font=font,fill=(32,40,49))
  d.text((xx,yy+185),meta['url'].split('/')[-1][:35],font=font,fill=(92,96,99))
 canvas.save(OUT/(key+'.jpg'),quality=84)
 return result
def main():
 summary=[]
 for key,url in VENUES.items():
  print('CAPTURE:',key,url,flush=True)
  result=capture(key,url)
  summary.append(result)
  print('PHOTOS',len(result['candidates']),'ERRORS',len(result['errors']),flush=True)
 (OUT/'official_site_candidates.json').write_text(
  json.dumps({'total':len(summary),'items':summary},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
