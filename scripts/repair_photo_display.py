#!/usr/bin/env python3
"""Repair display only. Use from a checkout of the user's existing GitHub repo.
Never modify itineraries, prices, downloaded photos, or photo-credits data.
"""
from pathlib import Path
from PIL import Image
import json, re, sys

ROOT=Path(__file__).resolve().parents[1]
HTML=ROOT/'index.html'
APP=ROOT/'assets/app.js'
OUT=ROOT/'assets/photo-file-index.json'
VERSION='20261110-safe-photo-4'
if not HTML.is_file() or not APP.is_file():
    sys.exit('Missing original index.html or assets/app.js; abort without changes')

# Read current files BEFORE writing anything. Patch only a recognized implementation.
a=APP.read_text('utf-8')
h=HTML.read_text('utf-8')

# Handle all shapes currently produced by gallery.json/recommended.json/new_routes.json.
GPHOTO=r'''const gPhoto = photo => {
  const string = x => typeof x === 'string' && x.trim() && x !== '[object Object]';
  if (!photo) return '';
  if (string(photo)) {
    if (/^https:\/\//.test(photo)) return photo;
    if (/^(?:\.\/)?assets\/photos\//.test(photo)) return './'+photo.replace(/^\.\//,'');
    return '';
  }
  if (typeof photo !== 'object' || Array.isArray(photo)) return '';
  const f = photo.file;
  const local = [photo.local,photo.local_path,photo.path,
    f && typeof f === 'object' && f.local,
    f && typeof f === 'object' && f.path].find(string);
  if (local && /^(?:\.\/)?assets\/photos\//.test(local))
    return './'+local.replace(/^\.\//,'');
  if (local && /^https:\/\//.test(local)) return local;
  const filename = string(f) ? f : (f && typeof f === 'object' && string(f.file) ? f.file : '');
  if (!filename) {
    const direct = [photo.url,photo.src,photo.image_url].find(x=>string(x) && /^https:\/\//.test(x));
    return direct || '';
  }
  if (/^(?:\.\/)?assets\/photos\//.test(filename)) return './'+filename.replace(/^\.\//,'');
  if (/^https:\/\//.test(filename)) return filename;
  const m=/^LOCAL-([a-z]+)-d([1-3])-(\d{2})\.(?:jpg|jpeg)$/i.exec(filename);
  if (m) return `./assets/photos/schedules/${m[1]}/d${m[2]}-${m[3]}.jpg`;
  if (/^LOCAL-|\[object Object\]/i.test(filename)) return '';
  return 'https://commons.wikimedia.org/wiki/Special:FilePath/'+encodeURIComponent(filename)+'?width=800';
};'''
if re.search(r'const\\s+gPhoto\\s*=\\s*(?:\\(\\s*photo\\s*\\)|photo)\\s*=>\\s*\\{',a):
    # Modern multi-line resolver: preserve it rather than matching only single lines.
    print('Recognized existing multi-line gPhoto; preserve its implementation')
elif 'const gPhoto=' in a:
    # Only rewrite the old one-line resolver when the entire line is recognized.
    a,count=re.subn(r'(?m)^const\\s+gPhoto\\s*=\\s*[^\\n]*?;\\s*
# This is a safety improvement: malformed photo object must not produce empty or invalid img src.
a=a.replace('${photo?`<img', '${photo&&gPhoto(photo)?`<img')
# Remove precisely the resolver that calls CORS-blocked Openverse in the browser.
h,removed = re.subn(r'<script\b[^>]*\bsrc=["\'][^"\']*photo-resolver\.js[^"\']*["\'][^>]*>\s*</script>', '', h, flags=re.I)
print('Removed browser-only photo-resolver scripts:',removed)
# Cache-bust app.js to purge old [object Object] code.
h,appcount = re.subn(r'(<script\b[^>]*\bsrc=["\'])\./assets/app\.js(?:\?[^"\']*)?(["\'][^>]*>\s*</script>)',
    lambda m:m.group(1)+'./assets/app.js?v='+VERSION+m.group(2),h, count=1, flags=re.I)
if appcount != 1:
    sys.exit('index.html has an unknown app.js script tag; abort without modifying files')
# Reinstall exactly one local loader.
h=re.sub(r'<script\b[^>]*\bsrc=["\'][^"\']*photo-local-fix\.js[^"\']*["\'][^>]*>\s*</script>', '', h, flags=re.I)
if not re.search(r'</head>',h,re.I):
    sys.exit('Cannot find closing head; no files changed')
h=re.sub(r'</head>', f'<script defer src="./assets/photo-local-fix.js?v={VERSION}"></script></head>',h,count=1,flags=re.I)

# Build a truthful manifest of actual, readable JPEG files, keyed to itinerary slots.
base=ROOT/'assets/photos/schedules'
cities=['hiroshima','shizuoka','sapporo','nagoya','sendai','okinawa','fukuoka','osaka','tokyo','matsuyama','takamatsu','kumamoto']
index={'version':VERSION, 'cities':{}, 'counts':{}}
allcount=0
for city in cities:
    entries={}
    folder=base/city
    for f in sorted(folder.glob('d?-??.jpg')) if folder.exists() else []:
        if not re.fullmatch(r'd[123]-\d\d\.jpg', f.name): continue
        try:
            if f.stat().st_size < 800: continue
            with Image.open(f) as img:
                img.verify()
            with Image.open(f) as img:
                if img.width < 100 or img.height < 90: continue
            entries[f.stem]=f'./assets/photos/schedules/{city}/{f.name}'
        except (ValueError, OSError, SyntaxError):
            print('BAD image skipped:',f)
    index['cities'][city]=entries
    index['counts'][city]=len(entries)
    allcount+=len(entries)
index['total']=allcount

# Single atomic-ish write after all syntax checks.
APP.write_text(a,encoding='utf-8')
HTML.write_text(h,encoding='utf-8')
OUT.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('VALID SAVED JPEG IMAGES:', allcount)
print('BY CITY:', index['counts'])
print('Updated:', APP,HTML,OUT)
# Neutralize the old installer that other workflows may run later.
old=ROOT/'scripts/install_photo_resolver.py'
if old.exists():
    old.write_text('#!/usr/bin/env python3\nprint("Browser live image search disabled; local downloaded photos are used.")\n',encoding='utf-8')
,lambda m:GPHOTO,a,count=1)
    if count != 1:
        sys.exit('app.js uses an unknown gPhoto implementation; no files changed')
else:
    print('NOTE: gPhoto not found; DOM repair will use known saved file paths')
# This is a safety improvement: malformed photo object must not produce empty or invalid img src.
a=a.replace('${photo?`<img', '${photo&&gPhoto(photo)?`<img')
# Remove precisely the resolver that calls CORS-blocked Openverse in the browser.
h,removed = re.subn(r'<script\b[^>]*\bsrc=["\'][^"\']*photo-resolver\.js[^"\']*["\'][^>]*>\s*</script>', '', h, flags=re.I)
print('Removed browser-only photo-resolver scripts:',removed)
# Cache-bust app.js to purge old [object Object] code.
h,appcount = re.subn(r'(<script\b[^>]*\bsrc=["\'])\./assets/app\.js(?:\?[^"\']*)?(["\'][^>]*>\s*</script>)',
    lambda m:m.group(1)+'./assets/app.js?v='+VERSION+m.group(2),h, count=1, flags=re.I)
if appcount != 1:
    sys.exit('index.html has an unknown app.js script tag; abort without modifying files')
# Reinstall exactly one local loader.
h=re.sub(r'<script\b[^>]*\bsrc=["\'][^"\']*photo-local-fix\.js[^"\']*["\'][^>]*>\s*</script>', '', h, flags=re.I)
if not re.search(r'</head>',h,re.I):
    sys.exit('Cannot find closing head; no files changed')
h=re.sub(r'</head>', f'<script defer src="./assets/photo-local-fix.js?v={VERSION}"></script></head>',h,count=1,flags=re.I)

# Build a truthful manifest of actual, readable JPEG files, keyed to itinerary slots.
base=ROOT/'assets/photos/schedules'
cities=['hiroshima','shizuoka','sapporo','nagoya','sendai','okinawa','fukuoka','osaka','tokyo','matsuyama','takamatsu','kumamoto']
index={'version':VERSION, 'cities':{}, 'counts':{}}
allcount=0
for city in cities:
    entries={}
    folder=base/city
    for f in sorted(folder.glob('d?-??.jpg')) if folder.exists() else []:
        if not re.fullmatch(r'd[123]-\d\d\.jpg', f.name): continue
        try:
            if f.stat().st_size < 800: continue
            with Image.open(f) as img:
                img.verify()
            with Image.open(f) as img:
                if img.width < 100 or img.height < 90: continue
            entries[f.stem]=f'./assets/photos/schedules/{city}/{f.name}'
        except (ValueError, OSError, SyntaxError):
            print('BAD image skipped:',f)
    index['cities'][city]=entries
    index['counts'][city]=len(entries)
    allcount+=len(entries)
index['total']=allcount

# Single atomic-ish write after all syntax checks.
APP.write_text(a,encoding='utf-8')
HTML.write_text(h,encoding='utf-8')
OUT.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('VALID SAVED JPEG IMAGES:', allcount)
print('BY CITY:', index['counts'])
print('Updated:', APP,HTML,OUT)
# Neutralize the old installer that other workflows may run later.
old=ROOT/'scripts/install_photo_resolver.py'
if old.exists():
    old.write_text('#!/usr/bin/env python3\nprint("Browser live image search disabled; local downloaded photos are used.")\n',encoding='utf-8')
