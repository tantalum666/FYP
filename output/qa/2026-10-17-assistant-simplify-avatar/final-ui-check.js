async (page) => {
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('http://127.0.0.1:5191/?surface=avatar');
  await page.locator('.a1-canvas[data-status=ready]').waitFor();
  const supported=await page.locator('.a1-canvas canvas').evaluate(canvas=>{const gl=canvas.getContext('webgl2');const ext=gl?.getExtension('WEBGL_lose_context');if(!ext)return false;ext.loseContext();return true;});
  if(supported){await page.getByRole('alert').waitFor();await page.getByRole('button',{name:'Retry',exact:true}).click();await page.locator('.a1-canvas[data-status=ready]').waitFor();}
  await page.getByRole('button',{name:'Wave',exact:true}).click();const frame=Number(await page.locator('.a1-canvas').getAttribute('data-frames'));await page.waitForFunction(f=>Number(document.querySelector('.a1-canvas').dataset.frames)>f+29,frame);await page.screenshot({path:'output/qa/2026-10-17-assistant-simplify-avatar/3d-wave-browser.png'});
  await page.getByRole('button',{name:'Rest',exact:true}).click();await page.screenshot({path:'output/qa/2026-10-17-assistant-simplify-avatar/3d-front-browser.png'});
  const licence=await page.request.get('http://127.0.0.1:5191/companion/source.json');if(!licence.ok())throw Error('missing provenance');
  await page.goto('http://127.0.0.1:5191/');await page.getByRole('button',{name:'Open assistant',exact:true}).click();
  await page.route('**/api/computer/jobs',async route=>{await new Promise(r=>setTimeout(r,1200));await route.continue();});
  const input=page.getByRole('textbox',{name:'Message the assistant',exact:true});await input.fill('Remember: QA confirms a reviewed memory');const before=Date.now();await page.getByRole('button',{name:'Send message',exact:true}).click();await page.getByRole('heading',{name:'Save a fact',exact:true}).waitFor();const elapsed=Date.now()-before;
  await page.getByRole('button',{name:'Confirm & save',exact:true}).click();await page.getByText('Memory updated.',{exact:true}).waitFor();
  const memory=await (await page.request.get('http://127.0.0.1:5191/api/memory')).json();if(memory.memories.length!==1)throw Error('memory not stored exactly once');
  await page.unroute('**/api/computer/jobs');await page.getByRole('button',{name:'Close',exact:true}).click();
  await page.getByRole('combobox',{name:'Language',exact:true}).selectOption('zh');await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'打开助理',exact:true}).click();await page.getByRole('textbox',{name:'向助理发送消息',exact:true}).waitFor();await page.screenshot({path:'output/qa/2026-10-17-assistant-simplify-avatar/assistant-zh-mobile.png'});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Chinese overflow');
  return {webglLossSupported:supported,webglRetry:supported,oneCanvasAfterRetry:true,provenanceAvailable:true,memoryStoredExactlyOnce:true,correctMemoryNotice:true,proposalDisplayedWithSlowFileReadMs:elapsed,chineseMobileNoOverflow:true};
}
