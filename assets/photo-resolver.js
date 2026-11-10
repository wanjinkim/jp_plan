/* JAPAN ATLAS — schedule-keyword photo resolver, 2026-11-10.
 * No keys, no Google scraping, no fabricated images: Wikimedia Commons searches.
 * Failed or absent existing photos are replaced only after an actual image loads.
 * The existing app.js, pricing, timelines and UI are left untouched.
 */
(() => {
  'use strict';
  const PREFIX = './assets/';
  const api = 'https://wikimedia.org';
  const wikiApi = 'https://wikipedia.org';
  const ovApi = 'https://openverse.org';
  const params = new URLSearchParams(location.search);
  const city = params.get('id') || '';
  const RATE = 4;
  const CACHE_DAYS = 2 * 86400000;
  const cachePrefix = 'japan-atlas-photo-v4:';
  const queryResults = new Map();
  const busy = new Set();
  const queue = [];
  let active = 0;
  let items = Object.create(null);
  let ready = false;
  let observer;
  let photoView;
  let scanScheduled = false;

  function safeHtml(x) { const e=document.createElement('div'); e.textContent=String(x ?? ''); return e.innerHTML; }
  function fromCache(k) {
    try { const r=JSON.parse(localStorage.getItem(cachePrefix+k)); if(r && r.expires>Date.now()) return r.value; } catch (_){}
    return null;
  }
  function toCache(k, val) {try {localStorage.setItem(cachePrefix+k,JSON.stringify({expires:Date.now()+CACHE_DAYS,value:val}));}catch (_){} }
  function plain(x) {return String(x||'').replace(/<[^>]*>/g,' ').replace(/&[^;]+;/g,' ').replace(/\s+/g,' ').trim();}
  function tokens(s) {return (String(s||'').toLowerCase().match(/[a-z]{4,}|[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]{2,}/gu)||[]).filter(s=>!['japan','photo','city','travel','japanese','example','station','airport','international','terminal','temple','park','garden','street','restaurant','onsen','shrine'].includes(s));}
  function licensed(i) {
    const info=i?.extmetadata||{};
    const lic=plain(info.LicenseShortName?.value||'').toLowerCase();
    const link=plain(info.LicenseUrl?.value||'');
    const phrase=lic+' '+link;
    return !/(non.?commercial|no.?derivatives|fair.?use|all rights reserved|unknown)/.test(phrase) && /(cc\s?by|cc\s?0|cc0|public domain|pd\b|pdm|creative commons)/.test(phrase);
  }
  function photoFromPage(p, task) {
    const i=p.imageinfo?.[0];
    if(!i || !licensed(i) || !/^image\/(jpeg|png|webp)$/.test(i.mime||'')) return null;
    const url=i.thumburl||i.url;
    if(!url || !/^https:\/\/(upload\.wikimedia\.org|commons\.wikimedia\.org)\//.test(url))return null;
    const file=p.title||'';
    const txt=(file+' '+plain(i.extmetadata?.ImageDescription?.value||'')).toLowerCase();
    const keyTokens=tokens(task?.queries?.[0]||task?.place||'');
    let matches=0;
    for(const k of new Set(keyTokens))if(txt.includes(k))matches++;
    const place=(task?.place||'').replace(/\s+/g,'').toLowerCase();
    if(place.length>=3 && txt.replace(/\s+/g,'').includes(place))matches+=4;
    const source='https://wikimedia.org(file.replace(/ /g,'_')).replace(/%3A/i,':');
    return {url,file,source,license:plain(i.extmetadata?.LicenseShortName?.value||''),author:plain(i.extmetadata?.Artist?.value||''),matches};
  }
  async function json(url, timeout=12000) {
    const c=new AbortController();const h=setTimeout(()=>c.abort(),timeout);
    try {const r=await fetch(url,{signal:c.signal,mode:'cors',credentials:'omit'});if(!r.ok)throw Error('HTTP '+r.status);return await r.json();}
    finally{clearTimeout(h);}
  }
  function commonsUrl(term) {
    return api+'?'+new URLSearchParams({action:'query',format:'json',formatversion:'2',origin:'*',generator:'search',gsrsearch:term,gsrnamespace:'6',gsrlimit:'12',prop:'imageinfo',iiprop:'url|mime|extmetadata',iiurlwidth:'780'});
  }
  async function commons(term, task) {
    const k='commons|'+term;
    if(!queryResults.has(k)) queryResults.set(k,json(commonsUrl(term)).then(j=>(j.query?.pages||[]).map(p=>photoFromPage(p,task)).filter(Boolean)).catch(()=>[]));
    return await queryResults.get(k);
  }
  async function openverse(term, task) {
    const cacheKey='ov|'+term;
    if(!queryResults.has(cacheKey)) {
      const url=ovApi+'?'+new URLSearchParams({q:term,page_size:'12',license:'by,by-sa,cc0,pdm'});
      queryResults.set(cacheKey,json(url,4000).then(j=>(j.results||[]).filter(p=>
        ['by','by-sa','cc0','pdm'].includes((p.license||'').toLowerCase()) &&
        /^https:\/\//.test(p.thumbnail||p.url||'') && /^https:\/\//.test(p.foreign_landing_url||p.detail_url||'')
      ).map(p=>({url:p.thumbnail||p.url,source:p.foreign_landing_url||p.detail_url,
          file:p.title||'', license:(p.license||'').toUpperCase(), author:p.creator||'',
          matches:tokens(task?.queries?.[0]||task?.place||'').filter(t=>(p.title||'').toLowerCase().includes(t)).length
      }))).catch(()=>[]));
    }
    return await queryResults.get(cacheKey);
  }
  function knownFiles(task) {
    return [...new Set(task.files||[])].map(fn=>({
      url:'https://wikimedia.org',
      source:'https://wikimedia.org(fn.replace(/ /g,'_')),
      file:fn,license:'원본 Commons 확인',author:'',matches:4,scope:'place'
    }));
  }
  async function searchWiki(task) {
    // Exact named place: Wikipedia article's representative image -> inspect its Commons license.
    if(!task.place || task.place.length<2) return [];
    const u=wikiApi+'?'+new URLSearchParams({action:'query',format:'json',formatversion:'2',origin:'*',titles:task.place,redirects:'1',prop:'pageimages',piprop:'name'});
    try{
      const j=await json(u,8500);
      const file=(j.query?.pages||[]).map(p=>p.pageimage).find(Boolean);
      if(!file)return [];
      const v=api+'?'+new URLSearchParams({action:'query',format:'json',formatversion:'2',origin:'*',titles:'File:'+file,prop:'imageinfo',iiprop:'url|mime|extmetadata',iiurlwidth:'780'});
      const jj=await json(v,8500);
      return (jj.query?.pages||[]).map(p=>photoFromPage(p,task)).filter(Boolean).map(p=>({...p,matches:p.matches+4}));
    }catch(_){return [];}
  }
  function searchTerms(task) {
    const terms=[];
    (task.queries||[]).forEach(t=>t&&terms.push({q:t,scope:'place'}));
    if(task.city_en && task.type) terms.push({q:task.city_en+' '+task.type,scope:'category'});
    if(task.city_jp && task.type) terms.push({q:task.city_jp+' '+task.type,scope:'category'});
    if(task.city_en) terms.push({q:task.city_en+' Japan travel',scope:'city'});
    return [...new Map(terms.map(t=>[t.q,t])).values()].slice(0,6);
  }
  async function choose(task, load) {
    const cacheKey='result|'+(task.place||'')+'|'+(task.title||'');
    const known=fromCache(cacheKey);
    if(known && known.url && await load(known.url))return known;
    const used=new Set();
    // Trusted curated filenames first: avoid search API on the common easy cases.
    for(const p of knownFiles(task)) {
      if(used.has(p.url))continue;used.add(p.url);
      if(await load(p.url)){toCache(cacheKey,p);return p;}
    }
    try{
      const w=await searchWiki(task);
      for(const p of w){if(used.has(p.url))continue;used.add(p.url);const pic={...p,scope:'place'};if(await load(pic.url)){toCache(cacheKey,pic);return pic;}}
    }catch(_){}
    for(const {q,scope} of searchTerms(task)){
      let results=await commons(q,task);
      results=results.sort((a,b)=>b.matches-a.matches);
      // Reject blatantly unrelated uploads, only fallback under truthful reference label.
      for(const p of results.slice(0,5)) {
        if(used.has(p.url))continue;used.add(p.url);
        const pic={...p,scope:scope==='place' && p.matches>0?'place':'reference'};
        if(await load(pic.url)){toCache(cacheKey,pic);return pic;}
      }
      // A second independent provider is essential when Wikimedia returns 403/429.
      if(scope!=='city' && /[a-z]/i.test(q)) {
        const ov=await openverse(q,task);
        for(const p of ov.slice(0,5)) {
          if(used.has(p.url))continue;used.add(p.url);
          const pic={...p,scope:scope==='place' && p.matches>0?'place':'reference'};
          if(await load(pic.url)){toCache(cacheKey,pic);return pic;}
        }
      }
    }
    return null;
  }
  function checkImage(url) {
    if (typeof url !== 'string' || !/^https?:\/\//.test(url)) return Promise.resolve(false);
    return new Promise(resolve=>{
      let settled=false;
      const im=new Image();
      const timer=setTimeout(()=>{if(!settled){settled=true;im.src='';resolve(false);}},6500);
      im.onload=()=>{if(settled)return;settled=true;clearTimeout(timer);resolve(im.naturalWidth>120&&im.naturalHeight>100);};
      im.onerror=()=>{if(settled)return;settled=true;clearTimeout(timer);resolve(false);};
      im.referrerPolicy='no-referrer'; im.src=url;
    });
  }
  function cleanupTag(el){el.querySelectorAll('.resolved-photo-source').forEach(n=>n.remove());}
  function apply(el,pic,task) {
    const placeholder=el.querySelector('.photo-placeholder');
    let img=el.querySelector('img');
    if(!img){img=document.createElement('img');img.loading='lazy';img.decoding='async';el.insertBefore(img,el.firstChild);}
    img.onerror=null; img.removeAttribute('onerror');
    img.src=pic.url;img.hidden=false;img.alt=(task.place||task.title||'일정 장소')+' 사진';
    img.referrerPolicy='no-referrer';
    if(placeholder)placeholder.hidden=true;
    cleanupTag(el);
    const badge=document.createElement('span');
    badge.className='resolved-photo-source';
    badge.textContent=pic.scope==='place'?'실제 검색 사진':'관련 참고사진';
    badge.title='사진 제공처 원본 · '+pic.license+' · 원본에서 저작자 확인';
    el.appendChild(badge);
    if(el.matches('a.photo-link')) {
      // Existing click still opens the place's Google Images search, as requested.
      const source=document.createElement('a');source.className='resolved-photo-credit';
      source.href=pic.source;source.target='_blank';source.rel='noopener noreferrer';
