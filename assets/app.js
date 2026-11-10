"use strict";
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const esc=x=>String(x??'').replace(/[&<>"']/g,v=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[v]));
const getJSON=u=>fetch('./assets/'+u).then(r=>{if(!r.ok)throw Error(u+' HTTP '+r.status);return r.json()});
const googleImg=q=>'https://www.google.com/search?'+new URLSearchParams({tbm:'isch',q}).toString();
const googleMap=q=>'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(q);
const googleTransit=(a,b)=>'https://www.google.com/maps/dir/?api=1&'+new URLSearchParams({origin:a,destination:b,travelmode:'transit'}).toString();
const yen=n=>Number(n).toLocaleString('ko-KR')+'만원';
const money=n=>Math.round(n*10)/10;
const dates=['11월 27일 · 금','11월 28일 · 토','11월 29일 · 일'];
const IDsOriginal=['hiroshima','shizuoka','sapporo','nagoya','okinawa','sendai'];
const IDsNew=['fukuoka','osaka','tokyo','matsuyama','takamatsu','kumamoto'];
let B=null,OLD=null,NEW=null,PHOTOS=null,INDEX=new Map(),LOCAL_SCHEDULE=Object.create(null);
const gPhoto=(photo)=>{
 if(!photo)return null;
 if(typeof photo==='string') return /^(\.\/assets\/photos\/|https:\/\/)/.test(photo)?photo:null;
 if(typeof photo!=='object')return null;
 if(typeof photo.local==='string' && photo.local.startsWith('./assets/photos/') && photo.local_verified)return photo.local;
 if(typeof photo.file==='string' && photo.file.trim())return `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(photo.file)}?width=800`;
 return null;
};
function photoCatalog(id){const arr=INDEX.get(id)?.group==='원래 후보'?(PHOTOS[id]||[]):(NEW.cities[id]?.photos||[]);return [...arr].sort((a,b)=>Number(Boolean(b.local_verified))-Number(Boolean(a.local_verified)))}
function cardPhoto(id,place='',exact=null){let pool=photoCatalog(id);if(exact){let p=pool.find(v=>v.file===exact);if(p)return p;}if(place){let p=pool.find(v=>(v.place||'')===place);if(p)return p;}return null;}
function bannerPhoto(id){let pool=photoCatalog(id);return pool.find(p=>['자연','명소','거리'].includes(p.kind))||pool[0]||null;}
function photoBox(photo,search,alt='',classes=''){
  const src=gPhoto(photo),dest=googleImg(search),caption=esc(alt||photo?.title||search);
  const placeholder='<span class="photo-placeholder"><span>이미지 자료 확인 중</span><b>'+esc(search)+'</b></span>';
  const shown=src?'<img loading="lazy" decoding="async" src="'+esc(src)+'" alt="'+caption+'" onerror="this.hidden=true;this.nextElementSibling.hidden=false;this.closest(&#39;button&#39;).disabled=true"><span class="photo-placeholder" hidden><span>사진을 불러오지 못했습니다</span><b>'+esc(search)+'</b></span><span class="zoom-hint" aria-hidden="true">크게 보기 ⤢</span>':placeholder;
  return '<div class="photo-link '+esc(classes)+'"><button type="button" class="photo-open" '+(src?'':'disabled')+' data-photo-src="'+esc(src||'')+'" data-photo-alt="'+caption+'" aria-label="'+caption+' 사진 크게 보기">'+shown+'</button><a class="photo-search-btn" href="'+esc(dest)+'" data-safe-url="'+esc(dest)+'" target="_blank" rel="noopener noreferrer" aria-label="'+caption+' 이미지 검색">이미지 검색 ↗</a></div>';
}
function tag(text){return `<span class="tag">${esc(text)}</span>`}
function title(k,head,desc){return `<div class="heading"><div><p class="eyebrow">${esc(k)}</p><h2>${esc(head)}</h2><p>${esc(desc)}</p></div></div>`}
function categorySection(ids,code,titleText,desc,id){return `<section id="${id}" class="section">
${title(code,titleText,desc)}<div class="cards">${ids.map((cityId,i)=>{
let c=INDEX.get(cityId),pic=bannerPhoto(cityId);let min=Math.min(c.total2x2,c.total4);
return `<a class="city-card" href="?page=city&id=${c.id}" aria-label="${esc(c.name)} 상세 일정 및 예산 보기"><div class="city-visual">${pic?`<img loading="lazy" src="${esc(gPhoto(pic))}" alt="${esc(pic.title)}" onerror="this.hidden=true">`:`<div class="city-visual-empty">${esc(c.name)} 사진 확인</div>`}<span class="city-number">${String(i+1).padStart(2,'0')}</span></div><div class="city-details"><p class="eyebrow">${c.group==='원래 후보'?'ORIGINAL 6':'DISCOVER 6'} · ${esc(c.airport)}</p><h3>${esc(c.name)}</h3><p>${esc(c.landscape)}</p><div class="price-stamp"><span>4명 계획 예산</span><strong>${yen(min)}</strong></div><span class="card-cta">동선과 2가지 숙박 예산 비교 ↗</span></div></a>`}).join('')}</div>
<div class="budget-summary">${groupTable(ids)}</div></section>`}
function groupTable(ids){return `<div class="budget-note"><b>4명 · 금~일 2박 3일</b><span>왕복 항공, 2박 객실, 식비, 시내 교통, 온천·관광, 예비비 포함 · 확정 예약가 아님</span></div><div class="table-scroll"><table class="budget-table"><thead><tr><th>도시</th><th>2명씩 2객실 · 4명 총액</th><th>4명 1객실 · 4명 총액</th><th>계획상 저렴한 방식</th></tr></thead><tbody>${ids.map(id=>{let x=INDEX.get(id);return `<tr><th><a href="?page=city&id=${id}">${esc(x.name)} ↗</a></th><td>${yen(x.total2x2)} <small>(1인 ${yen(money(x.total2x2/4))})</small></td><td>${yen(x.total4)} <small>(1인 ${yen(money(x.total4/4))})</small></td><td>${x.total2x2===x.total4?'동일':x.total2x2<x.total4?'2객실':'4인실'}</td></tr>`}).join('')}</tbody></table></div>`}
function home(){let p=bannerPhoto('hiroshima');return `<div class="container"><section class="hero"><div class="hero-content"><span class="hero-brow">JAPAN ATLAS · 2026.11.27–29</span><h1>12개 도시,<br><em>4명이 떠나는</em> 2박 3일.</h1><p>대중교통 중심, 이동 도보 15분 이내를 목표로 짠 자연·온천 여행. 기존 후보 6곳과 신규 후보 6곳의 코스와 예산을 한눈에 비교하세요.</p><div class="hero-actions"><a href="#original" class="btn primary">기존 6개 도시 보기</a><a href="#new" class="btn outline">신규 6개 도시 보기</a></div><div class="hero-pills">${tag('총 4명')}${tag('2명 × 2객실')}${tag('4명 × 1객실')}${tag('차량·택시 없이 대중교통')}</div></div><div class="hero-pic">${p?`<img src="${esc(gPhoto(p))}" alt="히로시마 자연 풍경" onerror="this.hidden=true">`:''}<div class="hero-overlay">NATURE · ONSEN · TRANSIT</div></div></section><section class="assumption"><div class="assumption-dot">i</div><div><b>예산 일부는 공식가·검색가, 일부는 비교용 가정입니다.</b><p>네이버 항공권·네이버 호텔의 11/27–29 확정 예약가는 직접 확인되지 않았습니다. 항공사 월간 왕복 최저 표시가, 11/27·28 숙박 비교사이트 최저 표시가, 공식 온천·관광·음식 메뉴 가격은 근거로 활용하되 전체 합계는 가정값입니다. 신규 후보의 ‘오전 도착 사례’ 역시 해당 날짜 항공권 예매 가능성을 보증하지 않습니다.</p></div></section>${categorySection(IDsOriginal,'01 · ORIGINAL SIX','직접 추천 코스 · 기존 6개 도시','6개 후보는 첫날 현지 공항 09:00 도착을 일괄 가정합니다. 기존 조사 코스를 하나의 메뉴로 통합했습니다.','original')}${categorySection(IDsNew,'02 · EARLY FLIGHT CANDIDATES','신규 추천 6개 도시','최근 공개된 오전 항공편 운항 시간표를 단서로 선정했습니다. 11월 27일 실제 운항·잔여석은 예약 화면에서 확인해야 합니다.','new')}${title('03 · PHOTOS','여행지 사진 모음','도시별 대표 장소 실사진을 비교하고 상세 일정에서 지도·교통을 확인할 수 있습니다.')}<div class="gallery-preview">${[...IDsOriginal,...IDsNew].map(id=>{let c=INDEX.get(id),p=bannerPhoto(id);return `<a href="?page=photos&city=${id}" class="gallery-teaser">${p?`<img loading="lazy" src="${esc(gPhoto(p))}" alt="${esc(p.title)}" onerror="this.hidden=true">`:'<span>사진 검색</span>'}<strong>${esc(c.name)}</strong></a>`}).join('')}</div></div>`}
function expenseCard(c){
  const parts=[['항공권 왕복 / 1인',c.flight],['식비 3일 / 1인',c.meals],['대중교통 / 1인',c.ground],['온천·관광 / 1인',c.activities],['예비비 / 1인',c.buffer]];
  const evid=(list)=>list.map(v=>`<li><a href="${esc(v[2]||v[1])}" target="_blank" rel="noopener noreferrer" data-safe-url="${esc(v[2]||v[1])}">${esc(v[0])} ↗</a>${v[1]&&typeof v[1]==='number'?` · ¥${Number(v[1]).toLocaleString('ko-KR')}`:''}</li>`).join('');
  const link=(o)=>o.url?`<a href="${esc(o.url)}" target="_blank" rel="noopener noreferrer" data-safe-url="${esc(o.url)}">원문 확인 ↗</a>`:'';
  return `<section class="budget-card" id="budget"><div class="budget-head"><div><p class="eyebrow">RESEARCH-BASED PLANNING / 4 ADULTS</p><h2>${esc(c.name)} 여행경비</h2><p>성인 4명 · 왕복 항공 + 2박 + 식사·교통·온천·관광 · 11/27–29 가정</p></div><div class="scenario-tabs" role="group" aria-label="숙박 유형"><button type="button" data-scenario="split" class="active" aria-pressed="true">2인실 2개</button><button type="button" data-scenario="together" aria-pressed="false">4인 숙소 1개</button></div></div>
  <div class="budget-spotlight"><div><small>4명 전체 · 수정 계획예산</small><strong id="budgetTotal">${yen(c.total2x2)}</strong><span>예약 확정금액 아님</span></div><div><small>1인 부담액</small><strong id="budgetPer">${yen(money(c.total2x2/4))}</strong><span>4명 균등 분담</span></div></div>
  <div class="budget-breakdown">${parts.map(v=>`<div><span>${esc(v[0])}</span><strong>${yen(v[1])}</strong></div>`).join('')}<div class="lodging-row"><span>숙박 2박 · 4명 전체 <small id="roomCaption">2인실 2개 × 2박</small></span><strong id="budgetStay">${yen(c.twin*4)}</strong></div></div>
  <div class="budget-evidence"><h3>조사 근거와 미확인 비용</h3>
    <p><b>항공권 [계획값]:</b> ${esc(c.flight_source.observed||'11월 27–29일에 대응하는 운임 표본 미확인')} · ${esc(c.flight_source.note)} ${link(c.flight_source)}</p>
    <p><b>해외호텔(2인실) [일부 검색 사례]:</b> ${esc(c.hotel_source.observed)} · 표시 가격은 비교 사이트의 최저 사례이며 객실 수와 위치 조건을 충족하는 예약가가 아닙니다. ${link(c.hotel_source)}</p>
    <p><b>공유숙박/4인 숙소 [계획값]:</b> ${esc(c.hotel_shared_status)}</p>
    <p><b>식비:</b> 3일 일정에 사용 가능한 예산을 산정했습니다. 식당별 실제 주문·대기·메뉴 선택은 미확인. ${c.meal_evidence.length?'일부 공식 또는 메뉴 근거:':''}</p><ul>${evid(c.meal_evidence)}</ul>
    <p><b>관광·온천 공식 요금:</b> 아래는 일정 내 일부 유료 시설의 성인 기준 단가이며, 그 외 입장·버스투어 비용은 계획 가정입니다.</p><ul>${evid(c.verified_activities)}</ul>
    <p><b>교통:</b> 현지 전철·버스·페리 등 예상 사용액. 전체 구간의 실측 운임 합계는 미검증. ${c.transport_evidence.length?'공식 요금 사례:':''}</p><ul>${evid(c.transport_evidence)}</ul>
  </div>
  <details class="budget-adjust"><summary>실제 조회한 항공권·숙소 금액으로 재계산</summary><p>단위: 만원. 아래 초기값은 예약 견적이 아닙니다. 확인한 금액을 입력하면 4명 총액과 1인 부담액이 즉시 변경됩니다.</p><div class="budget-inputs"><label>왕복 항공권 / 1인<input id="realFlight" type="number" min="0" step="0.1" value="${c.flight}"></label><label>2인실 1객실 / 1박<input id="realTwin" type="number" min="0" step="0.1" value="${c.twin}"></label><label>4인 숙소 1개 / 1박<input id="realQuad" type="number" min="0" step="0.1" value="${c.quad}"></label><label>식비 / 1인 3일<input id="realMeals" type="number" min="0" step="0.1" value="${c.meals}"></label><label>교통 / 1인<input id="realGround" type="number" min="0" step="0.1" value="${c.ground}"></label><label>온천·관광 / 1인<input id="realAct" type="number" min="0" step="0.1" value="${c.activities}"></label></div></details>
  <div class="budget-disclaimer"><b>가격 등급:</b> 공식 시설 단가와 일부 항공사 월간 최저·숙박 비교사이트 일별 최저 사례만 확인됐습니다. 11/27–29 네이버 최종 예약가, 4인 객실 재고, 전체 식사·교통 합계 및 금~일 평균은 검증하지 못한 계획값입니다. 쇼핑·수하물·개인 구매·환전 수수료 제외. 엔화 환산은 1JPY≈8.46원 참고.</div></section>`;
}
function scenarioControl(c){let selected='split';function update(){let get=(id,fallback)=>{let el=document.getElementById(id);return el?Math.max(0,Number(el.value)||0):fallback};let fly=get('realFlight',c.flight),twin=get('realTwin',c.twin),quad=get('realQuad',c.quad),food=get('realMeals',c.meals),tr=get('realGround',c.ground),act=get('realAct',c.activities);
let stay=(selected==='split'?4*twin:2*quad);let total=4*(fly+food+tr+act+c.buffer)+stay;
$('#budgetTotal').textContent=yen(money(total));$('#budgetPer').textContent=yen(money(total/4));$('#budgetStay').textContent=yen(money(stay));$('#roomCaption').textContent=selected==='split'?'2인실 2개 × 2박':'4인 이용 가능 숙소 1개 × 2박';}
$$('[data-scenario]').forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.scenario;$$('[data-scenario]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});update()}));$$('.budget-adjust input').forEach(x=>x.addEventListener('input',update));update();}
function candidateDays(id){return INDEX.get(id).group==='원래 후보'?OLD.cities[id].days:NEW.cities[id].days}
function timeline(id,day){let c=INDEX.get(id),entries=candidateDays(id)[day]||[];let html=`<div class="timeline-head" id="day-${day+1}"><div><span class="eyebrow">DAY ${day+1} · ${dates[day]}</span><h3>${esc(c.name)} ${day+1}일차</h3></div><span>${entries.length}개 일정 · 세로 보기</span></div><div class="timeline">`;
 entries.forEach((e,i)=>{
 let key=id+'-d'+(day+1)+'-'+String(i+1).padStart(2,'0'),stored=LOCAL_SCHEDULE[key],photo=stored?{local:stored.url,local_verified:true,title:e.title,place:e.place,source:stored.source}:cardPhoto(id,e.place,e.photo_file),prev=entries.slice(0,i).reverse().find(v=>v.place&&v.place!==e.place),photoQuery=[e.place,e.title,c.name,'일본'].filter(Boolean).join(' ');let map=googleMap(e.place),transit=prev?googleTransit(prev.place,e.place):null;
 html+=`<article class="schedule-row"><div class="schedule-copy"><div class="schedule-time"><strong>${esc(e.start)}–${esc(e.end)}</strong><span>${String(i+1).padStart(2,'0')} / ${String(entries.length).padStart(2,'0')}</span></div><h4>${esc(e.title)}</h4><div class="schedule-labels">${tag(e.kind||'일정')}${e.walk!==null&&e.walk!==undefined?tag('이동 도보 '+e.walk+'분 · 계획값'):tag('도보 재확인 필요')}</div><p>${esc(e.note||'계획상 활동·이동 시간입니다. 현장 교통과 영업시간을 재확인하세요.')}</p><div class="schedule-links"><a href="${esc(map)}" data-safe-url="${esc(map)}">지도에서 위치 ↗</a>${transit?`<a href="${esc(transit)}" data-safe-url="${esc(transit)}">대중교통 경로 ↗</a>`:''}</div></div>${photoBox(photo,photoQuery,e.title,'schedule-image')}</article>`;
 });return html+'</div>'}
function cityPage(id){let c=INDEX.get(id),original=c.group==='원래 후보',r=original?OLD.cities[id]:NEW.cities[id],photos=photoCatalog(id).slice(0,5),hero=photos[0]||null;
 let lead=original?'09:00 현지 공항 도착 가정':'오전 11시 이전 도착 항공편 사례 기준';
 return `<div class="container detail"><div class="crumb"><a href="./">12개 도시 비교</a><span>›</span>${original?'기존 6개 도시':'신규 6개 도시'}<span>›</span>${esc(c.name)}</div><section class="city-hero"><div class="city-hero-copy"><p class="eyebrow">${original?'ORIGINAL SIX':'NEW EARLY FLIGHT'} · ${esc(c.airport)}</p><h1>${esc(c.name)}</h1><p>${esc(r.intro||c.landscape)}</p><div class="tag-row">${tag('♨ 온천 필수')}${tag('🌿 자연 필수')}${tag('🚉 대중교통만')}${tag(lead)}</div><a href="#budget" class="btn primary">4명 예상경비 보기 ↓</a></div><div class="city-hero-photo">${hero?`<img src="${esc(gPhoto(hero))}" alt="${esc(hero.title)}" onerror="this.hidden=true">`:'<div class="no-photo">정확한 장소 사진 확인 중</div>'}</div></section>${expenseCard(c)}<section class="detail-section">${title('IMAGES · TOP 5','여행지 대표 사진','정확한 장소 사진이 확보된 것만 표시합니다. 사진 클릭으로 크게 볼 수 있으며 오른쪽 아래 작은 버튼에서 별도 이미지 검색을 할 수 있습니다.')}<div class="photos-strip">${photos.length?photos.map(p=>`<div class="photo-item">${photoBox(p,[p.title,p.place,c.name].join(' '),p.title)}<span>${esc(p.title)}</span><a class="photo-credit" href="${esc(p.source)}" data-safe-url="${esc(p.source)}">출처·라이선스 ↗</a></div>`).join(''):'<p class="photo-empty">아직 검증 가능한 Wikimedia Commons 사진을 연결하지 못했습니다. 각 일정의 이미지 검색 링크를 이용할 수 있습니다.</p>'}</div></section><section class="detail-section" id="schedule">${title('DAY BY DAY · 2 NIGHTS','2박 3일 연속 일정','첫날과 둘째 날은 이동·식사·대기 시간을 포함해 빈칸 없이 배분한 여행 계획입니다. 실제 출발 분·도보 소요는 확정된 시간표가 아닙니다.')}<div class="day-buttons">${[0,1,2].map(n=>`<a href="#day-${n+1}" class="day-jump">${n+1}일차 · ${dates[n]} ↓</a>`).join('')}</div><div id="timelineHost"></div></section><section class="detail-section source-area"><h2>여행 실행 전 확인사항</h2><div class="notice"><b>항공권·객실 예약 여부는 아직 확인되지 않았습니다.</b><p>${original?'기존 6개 도시는 첫날 오전 09:00 도착을 가정합니다.':'신규 후보는 최근 공개 정기편에 오전 11시 이전 도착 사례가 있습니다. 11월 27일 실제 좌석·운임은 별도 확인이 필요합니다.'} 구체적인 교통 연결·걷는 시간·야간 영업은 이동 전 구글지도에서 다시 확인하세요. 여행 자체의 트레킹은 연결 도보 15분 제한에서 제외했습니다.</p></div><div class="source-links">${(r.sources||[]).filter(a=>Array.isArray(a)).map(a=>`<a href="${esc(a[1])}" data-safe-url="${esc(a[1])}">${esc(a[0])} ↗</a>`).join('')}</div></section></div>`;
}
function galleryPage(){let q=new URLSearchParams(location.search),active=q.get('city')||'all';let ids=[...IDsOriginal,...IDsNew];let selected=active==='all'?ids:ids.includes(active)?[active]:ids;return `<div class="container"><div class="crumb"><a href="./">12개 도시 비교</a><span>›</span>사진 모음</div><section class="section">${title('03 · PHOTOS','도시별 사진 모음','대표 장소 사진만 연결하고, 같은 도시의 동일 파일은 한 번만 표시합니다.')}<div class="filterbar"><a href="?page=photos" class="${active==='all'?'active':''}">전체</a>${ids.map(id=>`<a class="${active===id?'active':''}" href="?page=photos&city=${id}">${esc(INDEX.get(id).name)}</a>`).join('')}</div><div class="gallery-grid">${selected.flatMap(id=>{let seen=new Set();return photoCatalog(id).filter(p=>{if(seen.has(p.file))return false;seen.add(p.file);return true;}).map(p=>`<article class="gallery-unit">${photoBox(p,[p.title,p.place,INDEX.get(id).name].join(' '),p.title)}<div><span>${esc(INDEX.get(id).name)}</span><h3>${esc(p.title)}</h3><a href="?page=city&id=${id}">상세 일정 확인 ↗</a> · <a href="${esc(p.source)}" data-safe-url="${esc(p.source)}">원본·라이선스 ↗</a></div></article>`) }).join('')}</div></section></div>`;}
const goodHosts=new Set(['www.google.com','commons.wikimedia.org','namiha.jp','www.crossroadfukuoka.jp','naniwanoyu.com','osaka-info.jp','en.www.laqua.jp','www.gotokyo.org','dogo.jp','matsuyama-sightseeing.com','busshozan.com','www.art-takamatsu.com','www.kumamoto-guide.mom','kumamoto-guide.jp','miyajima-ropeway.info','www.honoyu.jp','www.kusanagino-yu.com','jozankei.jp','www.jotetsu.co.jp','www.resorts.co.jp','akiugrand.com','takeyakotsu.jp','cerulean-blue.co.jp','p-castle.co.jp','www.japan-guide.com','www.koreanair.com','www.tour.ne.jp','www.motu-ooyama.com','sv1.ichiran.com','www.nagoyajo.city.nagoya.jp','www.laqua.jp','itsukushimajinja.jp','jr-miyajimaferry.co.jp','www.city.matsuyama.ehime.jp','www.yulax.info','static.churaumi.oc-am.net','www.akiugrand.com','www.tokyometro.jp','subway.osakametro.co.jp','www.laqua.jp','tabelog.com']);
let safeNext=null;
let photoPreviewReturnFocus=null;
function setupPhotoPreview(){
  const modal=$('#photoPreview'),image=$('#photoPreviewImage'),caption=$('#photoPreviewCaption'),closeButton=$('#photoPreviewClose');
  function close(){
    if(modal.hidden)return;
    modal.hidden=true;
    image.removeAttribute('src');
    document.body.classList.remove('photo-preview-active');
    if(photoPreviewReturnFocus&&photoPreviewReturnFocus.isConnected)photoPreviewReturnFocus.focus();
    photoPreviewReturnFocus=null;
  }
  document.addEventListener('click',event=>{
    if(event.target.closest('[data-preview-close]')){close();return;}
    const open=event.target.closest('.photo-open');
    if(!open||open.disabled||!modal.hidden)return;
    const url=open.dataset.photoSrc||'';
    if(!url.startsWith('./assets/photos/')&&!url.startsWith('https://'))return;
    const thumbnail=open.querySelector('img');
    if(!thumbnail||thumbnail.hidden||!thumbnail.complete||!thumbnail.naturalWidth)return;
    photoPreviewReturnFocus=open;
    image.src=url;
    image.alt=open.dataset.photoAlt||'여행지 사진';
    caption.textContent=image.alt;
    modal.hidden=false;
    document.body.classList.add('photo-preview-active');
    closeButton.focus();
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&!modal.hidden){event.preventDefault();close();}
    if(event.key==='Tab'&&!modal.hidden){event.preventDefault();closeButton.focus();}
  });
}
function secureInit(){document.addEventListener('click',e=>{let a=e.target.closest('a[data-safe-url]');if(!a)return;e.preventDefault();try{const url=new URL(a.href);if(url.protocol!=='https:'||url.username||url.password||!goodHosts.has(url.hostname))return;if(url.hostname==='www.google.com'&&!((url.pathname==='/search'&&url.searchParams.get('tbm')==='isch')||url.pathname.startsWith('/maps/')))return;safeNext=url.href;$('#externalDomain').textContent=url.hostname+' · HTTPS';$('#externalModal').hidden=false;$('#externalContinue').focus();}catch{}});$$('[data-close]').forEach(el=>el.addEventListener('click',()=>{$('#externalModal').hidden=true;safeNext=null}));$('#externalContinue').addEventListener('click',()=>{if(safeNext)window.open(safeNext,'_blank','noopener,noreferrer');$('#externalModal').hidden=true;safeNext=null;});}
async function init(){try{let [bb,old,nn,photos,localPhotos]=await Promise.all([getJSON('budgets.json'),getJSON('recommended.json'),getJSON('new_routes.json'),getJSON('gallery.json'),getJSON('local_schedule_photos.json').catch(()=>({}))]);B=bb;OLD=old;NEW=nn;PHOTOS=photos;LOCAL_SCHEDULE=localPhotos||{};INDEX=new Map(B.cities.map(c=>[c.id,c]));let q=new URLSearchParams(location.search);let page=q.get('page');let id=q.get('id');if(page==='photos')$('#app').innerHTML=galleryPage();else if(page==='city'&&INDEX.has(id)){$('#app').innerHTML=cityPage(id);scenarioControl(INDEX.get(id));$('#timelineHost').innerHTML=[0,1,2].map(n=>timeline(id,n)).join('')}else $('#app').innerHTML=home();secureInit();setupPhotoPreview();}catch(e){$('#app').innerHTML=`<div class="container error">페이지를 불러오지 못했습니다: ${esc(e.message)}<p>index.html과 assets 폴더를 저장소 최상위에 함께 업로드했는지 확인하세요.</p></div>`;}}
init();
