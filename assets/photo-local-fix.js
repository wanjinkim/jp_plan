/* Saved-file-first itinerary image repair. No cross-origin image API calls. */
(() => {
  'use strict';
  const city = new URLSearchParams(location.search).get('id') || '';
  const allowed = new Set(['hiroshima','shizuoka','sapporo','nagoya','sendai','okinawa','fukuoka','osaka','tokyo','matsuyama','takamatsu','kumamoto']);
  if (!allowed.has(city)) return;
  let photos = null;
  let obs;
  let scheduled = false;
  const processed = new WeakMap();
  const validSrc = s => typeof s === 'string' && /^\.\/assets\/photos\/schedules\/[a-z]+\/d[1-3]-\d\d\.jpg$/.test(s);
  function makeImage(link, src, title) {
    let img = link.querySelector('img');
    if (!img) {
      img = document.createElement('img');
      link.insertBefore(img, link.firstChild);
    }
    img.removeAttribute('onerror');
    img.onload = () => {
      if (img.naturalWidth <= 0) return;
      img.hidden = false;
      const placeholder = link.querySelector('.photo-placeholder');
      if (placeholder) placeholder.hidden = true;
      link.dataset.savedPhoto = 'loaded';
    };
    img.onerror = () => {
      img.hidden = true;
      const placeholder = link.querySelector('.photo-placeholder');
      if (placeholder) placeholder.hidden = false;
      link.dataset.savedPhoto = 'failed';
    };
    img.alt = title ? title+' 관련 일정 사진' : '여행 일정 사진';
    img.loading = 'lazy';
    img.decoding = 'async';
    img.src = src;
    if (img.complete && img.naturalWidth > 0) img.onload();
  }
  function scan() {
    scheduled = false;
    if (!photos) return;
    const host = document.querySelector('#timelineHost');
    if (!host) return;
    const days = host.querySelectorAll('.timeline');
    days.forEach((timeline, d) => {
      const rows = timeline.querySelectorAll('.schedule-row');
      rows.forEach((row, r) => {
        const link = row.querySelector('a.schedule-image');
        if (!link) return;
        const key=`d${d+1}-${String(r+1).padStart(2,'0')}`;
        const src=photos[key];
        // No file in repository: preserve original place Google Images link, do not use random image.
        if (!validSrc(src)) return;
        if (processed.get(link) === src) return;
        processed.set(link, src);
        makeImage(link,src,row.querySelector('h4')?.textContent?.trim() || '');
      });
    });
  }
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(scan);
  }
  async function init() {
    try {
      const res = await fetch('./assets/photo-file-index.json?v=20261110-safe-photo-4', {cache:'no-store'});
      if (!res.ok) throw new Error('Photo index HTTP '+res.status);
      const index=await res.json();
      photos=index.cities?.[city] || {};
      console.info('JAPAN ATLAS photos: locally validated files for',city,Object.keys(photos).length,'/ 3-day schedule; no browser Openverse API.');
    } catch (e) {
      photos={};
      console.warn('JAPAN ATLAS: local index unavailable. Existing pictures left unchanged.', e);
    }
    const app=document.getElementById('app');
    if (!app) return;
    obs=new MutationObserver(schedule);
    obs.observe(app,{childList:true,subtree:true});
    schedule();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
