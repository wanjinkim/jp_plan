#!/usr/bin/env python3
"""Inject a single defer script into the CURRENT deployed index, without replacing it."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
p=root/'index.html'
s=p.read_text(encoding='utf-8')
if 'assets/photo-resolver.js' in s:
 print('Photo-resolver already installed; no change to index.html')
else:
 script='<script defer src="./assets/photo-resolver.js?v=20261110d"></script>'
 pattern=r'(<script\s+defer\s+src=["\']\./assets/app\.js["\'][^>]*></script>)'
 updated,num=re.subn(pattern,lambda m:m.group(1)+script,s,count=1,flags=re.I)
 if num!=1:
  if '</head>' not in s.lower():raise RuntimeError('No </head>; cannot safely insert the resolver')
  updated=re.sub('</head>',script+'</head>',s,count=1,flags=re.I)
 p.write_text(updated,encoding='utf-8')
 print('Installed photo-resolver while retaining all current index.html elements')
