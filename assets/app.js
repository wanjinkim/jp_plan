'use strict';
/* GitHub Pages static edition: query-based routes work under any repository subpath. No password, login or server. */
const $=s=>document.querySelector(s);
const sanitize=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const codes={hiroshima:{airport:'HIJ',name:'히로시마',stay:'히로시마역·핫초보리'},shizuoka:{airport:'FSZ',name:'시즈오카',stay:'시즈오카역'},sapporo:{airport:'CTS',name:'삿포로',stay:'삿포로역·스스키노'},nagoya:{airport:'NGO',name:'나고야',stay:'나고야역·사카에'},sendai:{airport:'SDJ',name:'센다이',stay:'센다이역'},okinawa:{airport:'OKA',name:'오키나와',stay:'나하 국제거리·겐초마에'}};
const dates=['11.27 (금)','11.28 (토)','11.29 (일)'];
let DATA=null,GALLERY=null;
const maps=q=>'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(q||'일본');
const transit=(from,to)=>'https://www.google.com/maps/dir/?api=1&'+new URLSearchParams({origin:from,destination:to,travelmode:'transit'}).toString();
const photoUrl=(p,width=900)=>p.downloaded&&p.local?'./assets/photos/'+p.local.replace(/^assets\/photos\//,''):'https://commons.wikimedia.org/wiki/Special:FilePath/'+encodeURIComponent(p.file)+'?width='+width;
const image=(p,alt='',extra='')=>p?`<img loading="lazy" alt="${sanitize(alt||p.title)}" src="${sanitize(photoUrl(p,900))}" ${extra}>`:`<div class="noimage">사진 정보 확인 중</div>`;
function externalLink(url,text,cls=''){return `<a class="${sanitize(cls)}" href="${sanitize(url)}" data-external="1" rel="noopener noreferrer" target="_blank">${sanitize(text)}</a>`;}
function cityGallery(id){return GALLERY[id]||[];}
function featured(id){let g=cityGallery(id),chosen=[],used=new Set();for(const kind of ['명소','자연','온천','거리','실내','음식','식당','숙소']){
  const candidate=g.find(p=>p.kind===kind&&!used.has(p.file));if(candidate){chosen.push(candidate);used.add(candidate.file);}if(chosen.length>=5)break;
}for(const p of g){if(chosen.length>=5)break;if(!used.has(p.file)){chosen.push(p);used.add(p.file);}}return chosen.slice(0,5);}
function photoFor(entry,id){const g=cityGallery(id);if(!g.length)return {p:null,scope:'이미지 없음'};
 const place=(entry.place||'').replace(/\s/g,'');
 const exact=g.find(p=>place.length>2&&p.place&&p.place.replace(/\s/g,'')===place);
 if(exact)return {p:exact,scope:exact.scope||'실제 장소 참고 사진'};
 const partial=g.find(p=>place.length>3&&p.place&&p.place.includes(place)&&p.place.length>2);
 if(partial)return {p:partial,scope:(partial.scope||'실제 장소')+' · 위치 재확인'};
 let kind=entry.kind||'';
 const target=/온천/.test(entry.title)?'온천':/숙소|호텔|체크인|체크아웃/.test(entry.title)?'숙소':/식사|점심|저녁|라멘|카레|덮밥|우동|규탄|스시|초밥|야키|소바|오코노미|오뎅|카츠|맥주|이자카야|음식/.test(kind+' '+entry.title)?'음식':/전망|바다|산책|정원|숲|계곡|풍경|공원/.test(entry.title)?'자연':'명소';
 let found=g.find(p=>p.kind===target)||(target==='음식'?g.find(p=>p.kind==='식당'):null)||(target==='명소'?g.find(p=>p.kind==='실내'||p.kind==='거리'):null);
 return {p:found||g[0],scope:target==='음식'?'지역 음식 참고 사진 · 해당 식당 메뉴와 다를 수 있음':target==='숙소'?'숙박 권역 참고 사진 · 예약 호텔 아님':'해당 도시 참고 사진 · 이 일정 장소의 사진과 다를 수 있음'};
}
function heading(no,small,title,desc,aside=''){
 return `<div class="section-head"><div><div class="number">${no} / ${sanitize(small)}</div><h2>${sanitize(title)}</h2><p>${sanitize(desc)}</p></div>${aside?`<div class="section-aside">${sanitize(aside)}</div>`:''}</div>`;
}
function bookingPanel(initialId=null){return `<section class="main-section" id="bookSearch">${heading('01','FLIGHT & STAY','항공권과 숙소, 한 번에 준비','날짜·인원을 선택해 네이버 공식 검색으로 이동합니다. 검색 결과와 가격은 네이버에서 확인하세요.','네이버 공개 API의 실시간 가격 조회는 지원하지 않습니다.')}
<div class="booking-layout"><form class="glass-card booking-form" id="bookingForm"><div class="kicker">SELECT DESTINATION</div><div class="city-picks" id="bookingCityPicks">${DATA.cities.map(c=>`<button type="button" data-book-city="${c.id}" class="${initialId===c.id?'selected':''}">${sanitize(c.name)}</button>`).join('')}</div>
<div class="formgrid"><div class="field wide"><label for="origin">한국 출발 공항</label><select id="origin"><option value="ICN">인천국제공항 (ICN)</option><option value="GMP">김포국제공항 (GMP)</option><option value="PUS">김해국제공항 (PUS)</option></select></div><div class="field wide"><label for="destination">도착 도시</label><select id="destination"><option value="">도시를 선택해 주세요</option>${DATA.cities.map(c=>`<option value="${c.id}" ${initialId===c.id?'selected':''}>${sanitize(c.name)} · ${codes[c.id].airport}</option>`).join('')}</select></div>
<div class="field half"><label for="depart">출발일</label><input id="depart" type="date" value="2026-11-27" required></div><div class="field half"><label for="arrive">귀국일</label><input id="arrive" type="date" value="2026-11-29" required></div><div class="field third"><label for="adults">성인</label><select id="adults">${[1,2,3,4,5,6].map(x=>`<option value="${x}" ${x===2?'selected':''}>${x}명</option>`).join('')}</select></div><div class="field third"><label for="rooms">객실</label><select id="rooms">${[1,2,3].map(x=>`<option value="${x}">${x}실</option>`).join('')}</select></div></div>
<div class="formbottom"><label><input id="direct" type="checkbox" checked>직항 항공편 우선</label><span class="small-line">조건 변경 즉시 검색 링크가 변경됩니다.</span></div></form>
<div class="glass-card booking-side"><div><div class="kicker">BOOKING SUMMARY</div><h3 id="bookingTitle">여행지를 선택해 주세요</h3><p id="bookingSubtitle">한국 출발 · 2박 3일 · 현지 오전 9시 도착을 목표로 검토</p><div id="bookingRoute" class="route">ICN → 선택 대기</div><p id="bookingDates">2026.11.27 — 11.29</p></div><div><div id="bookingAlert" class="alert">실제 해당 시각의 항공편이 존재하는지 검색 결과에서 확인하세요.</div><div class="booking-btns"><a id="flightButton" class="btn peach" data-external="1" href="https://flight.naver.com/" target="_blank" rel="noopener noreferrer">네이버 왕복 항공권 검색 ↗</a><a id="hotelButton" class="btn light" data-external="1" href="https://hotels.naver.com/" target="_blank" rel="noopener noreferrer">네이버 호텔 검색 ↗</a><button type="button" id="copyBooking" class="btn blue">선택한 검색 조건 복사</button></div></div></div></div></section>`;}
function cityGrid(){return `<section class="main-section" id="sixCities">${heading('02','SIX CITIES','6개 도시, 실행성 우선 순위','관광지·온천·자연의 조합과 대중교통 접근성을 함께 고려했습니다. 후보를 누르면 그 도시의 상세 페이지로 이동합니다.','순위는 여행 기획상 비교 의견이며 객관적인 보증이 아닙니다.')}
<div class="card-grid">${DATA.cities.map(c=>{const p=featured(c.id)[0];return `<a class="city-card" href="?page=city&id=${c.id}" aria-label="${sanitize(c.name)} 상세 일정 보기"><div class="image">${image(p,c.name+' 대표 풍경')}<span class="rank">${c.rank}위 · ${sanitize(c.type==='conditional'?'조건부 추천':c.type==='replan'?'재조정 필요':'후보')}</span></div><div class="body"><div class="kicker">${sanitize(c.eng||'JAPAN')}</div><h3>${sanitize(c.name)}</h3><p>${sanitize(c.tagline||c.summary||'')}</p><div class="meta"><span>♨ 온천</span><span>🌿 자연</span><span>🚉 대중교통</span></div><div class="more">상세 일정·사진 보기 <span>↗</span></div></div></a>`;}).join('')}</div></section>`;}
function homeGallery(){return `<section class="main-section" id="photosPreview">${heading('03','PHOTO COLLECTION','여행 후보, 사진으로 미리 보기','6개 도시의 풍경을 모았습니다. 도시별 사진 모음에서 자연·온천·음식 사진을 더 볼 수 있습니다.')}
<div class="gallery-grid">${DATA.cities.map(c=>{const p=featured(c.id)[1]||featured(c.id)[0];return `<a class="photo-tile" href="?page=photos&city=${c.id}" aria-label="${sanitize(c.name)} 사진 모음 보기">${image(p,c.name+' '+(p?p.title:''))}<div class="overlay"><strong>${sanitize(c.name)}</strong><small>${sanitize(p?.title||'명소 사진')}</small></div></a>`;}).join('')}</div><p class="small-line">Wikimedia Commons 실사진 링크를 사용합니다. 사진의 촬영 계절이 실제 여행 시기와 다를 수 있습니다. 출처·라이선스는 각 사진의 원본 페이지에서 확인하세요.</p><div class="hero-actions"><a class="btn light" href="?page=photos">사진 모음 전체 보기 ↗</a></div></section>`;}
function home(){let p=featured('shizuoka')[0];return `<div class="shell"><section class="hero"><div class="hero-text"><div class="chip-row"><span class="chip">NOV 27—29 · 2박 3일</span><span class="chip">6 CITIES · TRAVEL EDITION</span></div><h1>여행은 가볍게,<br><span>선택은 더 선명하게.</span></h1><p>도보 이동 최대 15분, 대중교통 중심, 자연과 온천 필수. 6개 도시의 분위기와 현실적인 동선을 비교하고, 마음에 드는 여행지를 선택해 보세요.</p><div class="hero-actions"><a class="btn peach" href="#sixCities">6개 후보 비교하기 ↗</a><a class="btn light" href="#bookSearch">항공·숙소 검색</a></div></div><div class="hero-media"><div class="photo-frame">${image(p,'시즈오카 풍경 사진')}<span class="caption-chip">6 Cities, one unforgettable trip.</span></div></div></section>${bookingPanel()}${cityGrid()}${homeGallery()}</div>`;}
function bookingPage(){return `<div class="shell"><div class="page-top"><a href="./" class="crumb">홈</a><span class="crumb">/ 항공·숙소 검색</span></div>${bookingPanel()}<section class="main-section">${heading('','TRAVEL NOTE','예약 전 확인사항','오전 09:00 현지 착륙, 대중교통 환승과 15분 도보 조건을 일정에 적용하려면 실제 항공편 확정이 먼저 필요합니다.')}
<div class="note-box">네이버 항공권에서 조회되는 운임·직항 여부·운항일은 실시간 결과에 따릅니다. 호텔은 선택한 날짜와 인원을 공식 사이트에서 다시 지정해야 합니다. 외부 사이트에서 프로그램 설치나 브라우저 알림 허용을 요구하면 진행하지 마세요.</div></section></div>`;}
function cityPage(c){const id=c.id,imgs=featured(id),main=imgs[0];return `<div class="shell"><div class="page-top"><a href="./" class="crumb">여행 후보</a><span class="crumb">/ ${sanitize(c.name)}</span></div><section class="city-intro"><div><div class="kicker">RANK ${c.rank} / SIX JAPAN DESTINATIONS</div><h1>${sanitize(c.name)}</h1><p>${sanitize(c.summary||c.tagline)}<br><strong>온천 + 자연 + 대중교통</strong>을 중심으로 검토한 여행 코스입니다.</p><div class="chip-row"><span class="chip">♨ 온천 필수</span><span class="chip">🌿 자연 필수</span><span class="chip">🚉 환승 도보 15분 이내 목표</span></div><div class="hero-actions"><a class="btn peach" href="#schedule">날짜별 일정 보기 ↓</a><a class="btn light" href="?page=booking&city=${id}">이 도시 항공·숙소 검색 ↗</a><a class="btn light" href="./">다른 후보 비교</a></div></div><div class="image">${image(main,c.name+' 대표 풍경')}<span class="caption-chip">${sanitize(main?.title||c.tagline)}</span></div></section>
<section class="detail-section">${heading('','BEST FIVE PHOTOS','대표 사진 5장','사진을 먼저 살펴보고, 일정별 실제 방문 장소는 아래에서 확인해 보세요.')}
<div class="city-featured">${imgs.map(p=>`<div class="featured-photo">${image(p,p.title)}<div class="t"><strong>${sanitize(p.title)}</strong><span>${sanitize(p.scope||p.subtitle||'Commons 사진')}</span><br>${externalLink(p.source,'원본·라이선스 ↗')}</div></div>`).join('')}</div></section>
<section class="detail-section" id="schedule">${heading('','DAY-BY-DAY','2박 3일 상세 동선','날짜 탭을 선택하면 해당 일차만 표시됩니다. 각 일정 옆 사진은 실제 장소 사진인지 참고 이미지인지 구분했습니다.')}
<div class="day-tabs" id="dayTabs">${[1,2,3].map((x,i)=>`<button type="button" data-day="${i}" class="${i===0?'active':''}">${x}일차 · ${dates[i]}</button>`).join('')}</div><div id="daySchedule"></div></section>
<section class="detail-section">${heading('','EXECUTION CHECK','실행 가능성 및 수정 사항','원본 PDF를 실제로 실행하려면 아래 사항들을 추가 확인해야 합니다.')}
<div class="verification"><div class="panel"><h3>꼭 확인할 내용</h3><ul>${(c.fixes||[]).map(x=>`<li>${sanitize(typeof x==='string'?x:JSON.stringify(x))}</li>`).join('')}</ul></div><div class="panel"><h3>판정·실행 조건</h3><p class="small-line">${sanitize(c.verdict||'조건부 가능')}</p><ul>${(c.evidence||[]).map(x=>`<li>${sanitize(typeof x==='string'?x:(x.label||'공식 자료 확인'))}</li>`).join('')}</ul></div></div><div class="note-box">항공편·기상·식당 대기·실제 호텔 위치를 확정하기 전에는 분 단위 실행을 보증할 수 없습니다. 이동 도보 15분 기준은 트레킹 등 관광 자체의 걷기와 별개입니다.</div></section></div>`;}
function timelineMarkup(c,idx){const entries=c.corrected_days[idx]||[];return `<div class="day-overview"><h3>${idx+1}일차 · ${sanitize(c.day_titles?.[idx]||'상세 일정')}</h3><p>2026.${idx===0?'11.27':idx===1?'11.28':'11.29'} · 이동 구간과 사진 출처를 함께 확인하세요. 시간은 현장 여건에 따라 달라집니다.</p></div><div class="timeline">${entries.map((e,i)=>{
 const prev=entries.slice(0,i).reverse().find(x=>x.place&&x.place!==e.place);
 const m=e.place?maps(e.place):null;
 const travel=e.place&&prev?transit(prev.place,e.place):null;
 const photo=photoFor(e,c.id);let labels=`<span>${sanitize(e.kind||'일정')}</span>`;
 if(typeof e.walk==='number')labels+=`<span class="${e.walk>15?'warning':''}">이동 도보 ${e.walk}분 ${e.walk>15?'· 재조정 필요':''}</span>`;
 labels+=`<span class="${e.verified?'':'warning'}">${e.verified?'자료 확인':'출발 전 확인'}</span>`;
 return `<article class="timeline-row"><div class="time">${sanitize(e.start)}–${sanitize(e.end)}<small>${String(idx+1)}일차 · ${i+1}번째</small></div><div class="it-body"><h4>${sanitize(e.title)}</h4><div class="badge-line">${labels}</div>${e.note?`<p>${sanitize(e.note)}</p>`:''}<div class="it-links">${m?externalLink(m,'구글지도 위치 ↗'):''}${travel?externalLink(travel,'대중교통 길찾기 ↗'):''}${photo.p?externalLink(photo.p.source,'사진 출처 ↗'):''}</div></div><div class="timeline-image">${image(photo.p,e.title)}<span class="scope">${sanitize(photo.scope)}</span></div></article>`;
 }).join('')}</div>`;}
function photosPage(){const id=new URLSearchParams(location.search).get('city')||'all';let current=id in codes?id:'all';return `<div class="shell"><div class="page-top"><a class="crumb" href="./">여행 후보</a><span class="crumb">/ 사진 모음</span></div><section class="main-section">${heading('03','PHOTO GALLERY','6개 도시 사진 아카이브','풍경·온천·음식·숙박 권역 참고사진 등 83개 사진 항목을 도시별로 탐색합니다.','사진마다 출처를 제공하며 특정 식당·숙소의 실제 사진 여부를 별도로 표기합니다.')}
<div id="galleryFilters" class="gallery-tools"><button type="button" data-gallery="all" class="${current==='all'?'active':''}">모든 도시</button>${DATA.cities.map(c=>`<button type="button" data-gallery="${c.id}" class="${current===c.id?'active':''}">${sanitize(c.name)}</button>`).join('')}</div><div id="galleryResults" class="full-gallery"></div><p class="small-line">사진은 Wikimedia Commons에서 공개된 자료를 연결했습니다. 일부 이미지는 네트워크나 원본 변경으로 표시되지 않을 수 있습니다. 라이선스·저작자 표기는 원본에서 확인하세요.</p></section></div>`;}
function galleryCards(id){let cityIds=id==='all'?DATA.cities.map(c=>c.id):[id];let pics=cityIds.flatMap(cid=>cityGallery(cid).map(p=>({cid,p})));return pics.map(({cid,p})=>`<article class="gallery-card"><div class="photo">${image(p,p.title)}</div><div class="bottom"><div class="kicker">${sanitize(codes[cid].name)} · ${sanitize(p.kind)}</div><h3>${sanitize(p.title)}</h3><p>${sanitize(p.scope||p.subtitle||'참고 이미지')}<br>${sanitize(p.subtitle||'')}<br>사진: ${sanitize(p.author||'저작자 원본 확인')}</p>${externalLink(p.source,'원본 사진·라이선스 ↗')} · ${externalLink(maps(p.place),'구글지도 ↗')}</div></article>`).join('');}
function updateGallery(id){const container=$('#galleryResults');if(!container)return;container.innerHTML=galleryCards(id);$$('#galleryFilters button').forEach(b=>b.classList.toggle('active',b.dataset.gallery===id));attachFallback(container);}
function $$(q){return [...document.querySelectorAll(q)];}
function attachFallback(root=document){root.querySelectorAll('img').forEach(img=>{if(img.dataset.bound)return;img.dataset.bound='1';img.addEventListener('error',()=>{img.style.display='none';const ph=document.createElement('span');ph.className='noimage';ph.textContent='사진 표시 불가 · 원본 링크를 확인하세요';img.parentNode?.append(ph);});});}
function attachBooking(){const f=$('#bookingForm');if(!f)return;
 const origin=$('#origin'),dest=$('#destination'),depart=$('#depart'),arrive=$('#arrive'),adults=$('#adults'),rooms=$('#rooms'),direct=$('#direct');
 const allowed=id=>!!codes[id];
 function update(){const id=dest.value,chosen=allowed(id),d0=depart.value.replaceAll('-',''),d1=arrive.value.replaceAll('-',''),from=origin.value,to=chosen?codes[id].airport:'';
  $$('#bookingCityPicks button').forEach(b=>b.classList.toggle('selected',b.dataset.bookCity===id));
  $('#bookingTitle').textContent=chosen?codes[id].name+' 여행 준비':'여행지를 선택해 주세요';
  $('#bookingSubtitle').textContent=chosen?`숙박 추천 권역: ${codes[id].stay}`:'도시 6개 중 하나를 선택해 주세요.';
  $('#bookingRoute').textContent=`${from} → ${to||'선택 대기'}`;
  $('#bookingDates').textContent=`${depart.value||'?'} — ${arrive.value||'?'}, 성인 ${adults.value}명 / ${rooms.value}객실`;
  const valid=!!(chosen&&depart.value&&arrive.value&&depart.value<arrive.value&&/^\d{8}$/.test(d0)&&/^\d{8}$/.test(d1));
  const flight=valid?`https://flight.naver.com/flights/international/${from}:airport-${to}:airport-${d0}/${to}:airport-${from}:airport-${d1}?`+new URLSearchParams({adult:adults.value,isDirect:String(direct.checked),fareType:'Y'}):'https://flight.naver.com/';
  $('#flightButton').href=flight;$('#hotelButton').href='https://hotels.naver.com/';
  const changed=depart.value!=='2026-11-27'||arrive.value!=='2026-11-29';
  $('#bookingAlert').textContent=!valid?'날짜와 여행지를 선택해 주세요. 귀국일은 출발일 이후여야 합니다.':changed?'여행 날짜를 변경했습니다. 기존 2026.11.27~29 일정과 교통·영업 조건은 새 날짜에 맞춰 다시 확인해야 합니다.':'09:00 현지 공항 도착을 가정한 일정입니다. 실제 해당 항공편 존재 여부를 네이버에서 확인해 주세요.';
  $('#copyBooking').disabled=!valid;
 }
 f.addEventListener('submit',e=>e.preventDefault());
 f.querySelectorAll('input,select').forEach(el=>el.addEventListener('change',update));
 $$('#bookingCityPicks button').forEach(b=>b.addEventListener('click',()=>{dest.value=b.dataset.bookCity;update();}));
 $('#copyBooking').addEventListener('click',async()=>{
  const id=dest.value;if(!allowed(id))return;
  const s=`[일본 여행 검색 조건]\n${codes[id].name} / ${origin.value} → ${codes[id].airport}\n출발 ${depart.value}, 귀국 ${arrive.value}\n성인 ${adults.value}명 / 객실 ${rooms.value}실 / 직항 ${direct.checked?'우선':'무관'}\n숙소 권역 ${codes[id].stay}\n호텔 검색: https://hotels.naver.com/`;
  try{await navigator.clipboard.writeText(s);$('#copyBooking').textContent='검색 조건 복사 완료 ✓';setTimeout(()=>$('#copyBooking').textContent='선택한 검색 조건 복사',2200);}catch{$('#copyBooking').textContent='복사 불가 · HTTPS 접속을 확인하세요';}
 });
 const qs=new URLSearchParams(location.search).get('city');if(allowed(qs))dest.value=qs;update();
}
const allowedExternalHosts=new Set(['www.google.com','flight.naver.com','hotels.naver.com','commons.wikimedia.org']);
let outboundUrl=null;function openOutbound(url){let u;try{u=new URL(url,location.href);}catch{return;}
 if(u.protocol!=='https:'||!allowedExternalHosts.has(u.hostname))return;
 if(u.hostname==='www.google.com'&&!u.pathname.startsWith('/maps/'))return;
 if(u.hostname==='commons.wikimedia.org'&&!u.pathname.startsWith('/wiki/'))return;
 if(u.hostname==='flight.naver.com'&&!(u.pathname==='/'||u.pathname.startsWith('/flights/')))return;
 if(u.hostname==='hotels.naver.com'&&u.pathname!=='/')return;
 outboundUrl=u.href;$('#outDomain').textContent=u.hostname+' · HTTPS';$('#outbound').hidden=false;$('#outCancel').focus();
}
function initOutbound(){document.addEventListener('click',ev=>{const anchor=ev.target.closest('a[data-external]');if(!anchor)return;ev.preventDefault();openOutbound(anchor.href);});
 $('#outCancel').addEventListener('click',()=>{$('#outbound').hidden=true;outboundUrl=null;});
 $('#outProceed').addEventListener('click',()=>{if(outboundUrl){window.open(outboundUrl,'_blank','noopener,noreferrer');}$('#outbound').hidden=true;outboundUrl=null;});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('#outbound').hidden=true;outboundUrl=null;}});
 $('.outbound-backdrop').addEventListener('click',()=>{$('#outbound').hidden=true;outboundUrl=null;});
}
async function init(){try{
 const [d,g]=await Promise.all([fetch('./assets/itinerary.json'),fetch('./assets/gallery.json')]);
 if(!d.ok||!g.ok)throw Error('여행 데이터를 읽지 못했습니다');
 DATA=await d.json();GALLERY=await g.json();
 const params=new URLSearchParams(location.search); const p=params.get('page')==='city'?'/city/'+(params.get('id')||''):params.get('page')==='booking'?'/booking':params.get('page')==='photos'?'/photos':'/';
 if(p==='/')$('#app').innerHTML=home();
 else if(p==='/booking')$('#app').innerHTML=bookingPage();
 else if(p==='/photos')$('#app').innerHTML=photosPage();
 else if(p.startsWith('/city/')){const c=DATA.cities.find(x=>x.id===p.slice(6));if(!c)throw Error('도시를 찾을 수 없습니다');
  $('#app').innerHTML=cityPage(c);let day=0;const setDay=i=>{day=i;$('#daySchedule').innerHTML=timelineMarkup(c,i);$$('#dayTabs button').forEach(b=>b.classList.toggle('active',Number(b.dataset.day)===i));attachFallback($('#daySchedule'));};
  $$('#dayTabs button').forEach(b=>b.addEventListener('click',()=>setDay(Number(b.dataset.day))));setDay(0);
 }
 else throw Error('존재하지 않는 페이지입니다');
 if(p==='/photos'){const city=new URLSearchParams(location.search).get('city');updateGallery(city&&codes[city]?city:'all');$$('#galleryFilters button').forEach(b=>b.addEventListener('click',()=>{let v=b.dataset.gallery;history.replaceState(null,'',v==='all'?'?page=photos':'?page=photos&city='+encodeURIComponent(v));updateGallery(v);}));}
 $$('.navlinks a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')===(p==='/'?'./':'?page='+p.slice(1))));
 attachBooking();attachFallback();initOutbound();
 }catch(e){$('#app').innerHTML=`<div class="shell"><div class="panel error-panel"><h2>화면을 불러오지 못했습니다</h2><p>${sanitize(e.message)}</p><a href="./" class="btn light">홈으로 돌아가기</a></div></div>`;}}
init();
