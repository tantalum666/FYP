async (page) => {
  await page.unrouteAll({behavior:'ignoreErrors'});
  const origin='http://127.0.0.1:5191';
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(origin+'/');
  await page.getByRole('combobox',{name:'Language',exact:true}).selectOption('en');
  async function preference(mode){
    const saved=(await (await page.request.get(origin+'/api/workspace')).json()).calendar_extras.preferences;
    const {version,...preferences}=saved;preferences.avatar_display=mode;
    const response=await page.request.post(origin+'/api/workspace/preferences',{headers:{'X-Desk-Request':'1','X-Operation-Id':crypto.randomUUID(),'Origin':origin},data:{expected_version:version,preferences}});
    if(!response.ok())throw Error('fixture preference failed '+response.status());
  }
  await preference('companion');
  try {
    await page.goto(origin+'/?surface=device');
    await page.setViewportSize({width:1024,height:600});
    await page.locator('.a1-canvas[data-status=ready]').waitFor();
    if(await page.locator('canvas').count()!==1)throw Error('duplicate device character');
    const canvas=page.locator('.a1-canvas');
    await page.waitForFunction(()=>Number(document.querySelector('.a1-canvas').dataset.frames)>8);
    await page.screenshot({path:'output/qa/2026-10-17-assistant-simplify-avatar/device-single-a1.png'});
    await page.getByRole('button',{name:'Touch to manage',exact:true}).click();
    await page.getByRole('button',{name:'Assistant',exact:true}).click();
    await page.getByRole('textbox',{name:'Message the assistant',exact:true}).waitFor();
    await page.waitForTimeout(100);
    const frozen=Number(await canvas.getAttribute('data-frames'));
    await page.waitForTimeout(250);
    if(Number(await canvas.getAttribute('data-frames'))!==frozen)throw Error('blocked canvas still animates');
    await page.screenshot({path:'output/qa/2026-10-17-assistant-simplify-avatar/device-assistant.png'});
  } finally {await preference('calendar');}
  await page.goto(origin+'/?surface=avatar');
  await page.setViewportSize({width:1440,height:1000});
  await page.locator('.a1-canvas[data-status=ready]').waitFor();
  if(await page.locator('canvas').count()!==1)throw Error('duplicate standalone canvas');
  await page.getByRole('button',{name:'Walk in place',exact:true}).click();
  const start=Number(await page.locator('.a1-canvas').getAttribute('data-frames'));
  await page.waitForFunction(f=>Number(document.querySelector('.a1-canvas').dataset.frames)>f+8,start);
  await page.screenshot({path:'output/qa/2026-10-17-assistant-simplify-avatar/3d-walk-browser.png'});
  await page.getByRole('button',{name:'Rest',exact:true}).click();
  await page.screenshot({path:'output/qa/2026-10-17-assistant-simplify-avatar/3d-front-browser.png'});
  const source=await (await page.request.get(origin+'/companion/source.json')).json();
  const bytes=await (await page.request.get(origin+'/companion/a1-v2.glb')).body();
  if(bytes.length!==source.stats.file_bytes)throw Error('stale runtime asset');
  if(errors.length)throw Error(errors.join('\n'));
  return {deviceExactlyOneCanvas:true,devicePanelStopsAnimation:true,standaloneExactlyOneCanvas:true,walkClipRendered:true,finalAssetBytes:bytes.length,consoleErrors:errors};
}
