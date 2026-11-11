import { chromium } from 'playwright';
import fs from 'node:fs';
import crypto from 'node:crypto';

const cities = ['hiroshima','shizuoka','sapporo','nagoya','okinawa','sendai',
                'fukuoka','osaka','tokyo','matsuyama','takamatsu','kumamoto'];
// Ensure that each visible schedule image represents distinct JPEG bytes, not a renamed duplicate.
// Confirm the displayed file is the same version described by its source Git blob SHA.
const manifest=JSON.parse(fs.readFileSync('assets/photo_manifest_281.json','utf-8'));
const mapped=JSON.parse(fs.readFileSync('assets/local_schedule_photos.json','utf-8'));
const jpegHashes=new Set();
if(manifest.length!==281||Object.keys(mapped).length!==281)throw Error('Photo manifest/index must both contain 281 images');
for(const entry of manifest){
  const photo=mapped[entry.key];
  if(!photo?.source||photo.url!=='./'+entry.local_path)throw Error('Missing source/index: '+entry.key);
  const bytes=fs.readFileSync(entry.local_path);
  const blobSHA=crypto.createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
  if(photo.source_proof_blob_sha!==blobSHA)throw Error('Image bytes diverged from their original source: '+entry.key);
  const hash=crypto.createHash('sha256').update(bytes).digest('hex');
  if(jpegHashes.has(hash))throw Error('Identical image repeated in a different itinerary slot: '+entry.key);
  jpegHashes.add(hash);
}
console.log('SOURCE-SHA VALIDATED AND UNIQUE PHOTOGRAPHS:',jpegHashes.size,'/281');
const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
const result = {checkedAt: new Date().toISOString(), cities:{}, checked:0,loaded:0,missing:[],errors:[],blogCards:0,lightboxes:0,searchButtons:0};
try {
  for (const city of cities) {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e=>errors.push(e.message));
    try {
      await page.goto('http://127.0.0.1:8765/?page=city&id='+city,{waitUntil:'networkidle',timeout:30000});
      await page.locator('.schedule-row').first().waitFor({timeout:20000});
      const rows = page.locator('.schedule-row');
      const count = await rows.count();
      const cityInfo={total:count,loaded:0,missing:[]};
      for(let i=0;i<count;i++){
        const row=rows.nth(i);
        const img=row.locator('.schedule-image img');
        if(await img.count()){
          await img.scrollIntoViewIfNeeded();
          await img.evaluate(el=>el.decode().catch(()=>{}));
        }
        const check=await row.evaluate(el=>{
          const img=el.querySelector('.schedule-image img');
          return {title:el.querySelector('h4')?.textContent?.trim()||'', 
                  src:img?.getAttribute('src')||'',
                  loaded:!!img&&!img.hidden&&img.complete&&img.naturalWidth>0};
        });
        result.checked++;
        if(check.loaded){cityInfo.loaded++;result.loaded++;}
        else {const missing={city,step:i+1,...check};cityInfo.missing.push(missing);result.missing.push(missing);}
      }
      // Every destination must have an actual 2-night/3-day post, not a bare URL.
      const blog=page.locator('#travel-blogs .blog-story');
      if(await page.locator('#travel-blogs').count()!==1)
        throw Error(city+': duplicate travel journal sections');
      if(await blog.count()<1) throw Error(city+': missing curated blog story card');
      for(const story of await blog.all()){
        if(!((await story.getAttribute('href'))||'').startsWith('https://'))
          throw Error(city+': blog article is not a real HTTPS URL');
        if(!(await story.locator('time[datetime]').count()))
          throw Error(city+': travel journal missing publication date');
      }
      if(!(await page.locator('#travel-blogs .blog-search-more').getAttribute('href')).includes('where=blog'))
        throw Error(city+': missing Naver travel review lookup');
      result.blogCards++;

      // Click photograph itself: verify centered lightbox, loaded full image, escape closing.
      const thumb=page.locator('.schedule-image .photo-open').first();
      if(!await thumb.count()) throw Error(city+': photo zoom button missing');
      await thumb.click();
      if(!await page.locator('#photoPreview').isVisible()) throw Error(city+': lightbox failed to open');
      const full=page.locator('#photoPreviewImage');
      await full.evaluate(el=>el.decode().catch(()=>{}));
      if(!await full.evaluate(el=>el.complete&&el.naturalWidth>0))
        throw Error(city+': modal preview image did not load');
      const box=await full.boundingBox(),viewport=page.viewportSize();
      if(!box||box.width>viewport.width||box.height>viewport.height)
        throw Error(city+': modal image overflows viewport');
      result.lightboxes++;
      if(city==='fukuoka') await page.screenshot({path:'browser-fukuoka-lightbox.png'});
      await page.keyboard.press('Escape');
      if(await page.locator('#photoPreview').isVisible())throw Error(city+': lightbox does not close on Escape');

      // The small image-search link is independent from photo zoom.
      const search=page.locator('.schedule-image .photo-search-btn').first();
      const searchUrl=await search.getAttribute('href');
      const target=await search.getAttribute('target');
      if(!searchUrl?.startsWith('https://www.google.com/search?')||!searchUrl.includes('tbm=isch')||target!=='_blank')
        throw Error(city+': image search button does not link directly to Google images');
      if(await search.getAttribute('data-safe-url'))
        throw Error(city+': image search unexpectedly triggers confirmation instead of a direct link');
      const [popup]=await Promise.all([page.waitForEvent('popup'),search.click()]);
      await popup.close();
      if(await page.locator('#photoPreview').isVisible())
        throw Error(city+': image search incorrectly opened photo lightbox');
      result.searchButtons++;
      if(city==='fukuoka')await page.locator('#travel-blogs').screenshot({path:'browser-fukuoka-blog-card.png'});
      result.cities[city]=cityInfo;
    }catch(e){result.errors.push({city,error:String(e)});}
    result.errors.push(...errors.map(error=>({city,error})));
    await page.close();
  }
}finally{await browser.close();}
fs.writeFileSync('browser-photo-audit.json',JSON.stringify(result,null,2)+'\n');
console.log('ACTUAL BROWSER PHOTO LOADS:',result.loaded+'/'+result.checked);
for(const [city,c] of Object.entries(result.cities))console.log(city,c.loaded+'/'+c.total);
console.log('MISSING:',result.missing.length,'JS ERRORS:',result.errors.length);for(const e of result.errors)console.error('BROWSER VERIFICATION ERROR:',JSON.stringify(e));console.log('BLOGS:',result.blogCards+'/12','MODALS:',result.lightboxes+'/12','SEARCH LINKS:',result.searchButtons+'/12');
if(result.checked!==281 || result.missing.length || result.errors.length || result.blogCards!==12 || result.lightboxes!==12 || result.searchButtons!==12) process.exitCode=1;
