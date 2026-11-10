import { chromium } from 'playwright';
import fs from 'node:fs';

const cities = ['hiroshima','shizuoka','sapporo','nagoya','okinawa','sendai',
                'fukuoka','osaka','tokyo','matsuyama','takamatsu','kumamoto'];
const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
const result = {checkedAt: new Date().toISOString(), cities:{}, checked:0,loaded:0,missing:[],errors:[]};
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
      result.cities[city]=cityInfo;
    }catch(e){result.errors.push({city,error:String(e)});}
    result.errors.push(...errors.map(error=>({city,error})));
    await page.close();
  }
}finally{await browser.close();}
fs.writeFileSync('browser-photo-audit.json',JSON.stringify(result,null,2)+'\n');
console.log('ACTUAL BROWSER PHOTO LOADS:',result.loaded+'/'+result.checked);
for(const [city,c] of Object.entries(result.cities))console.log(city,c.loaded+'/'+c.total);
console.log('MISSING:',result.missing.length,'JS ERRORS:',result.errors.length);
if(result.checked!==281 || result.missing.length || result.errors.length) process.exitCode=1;
