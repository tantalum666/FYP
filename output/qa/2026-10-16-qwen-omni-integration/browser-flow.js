async (page) => {
  const checks = { browser_plugin: "absent; regular Playwright CLI", url: page.url(), title: await page.title() };
  await page.setViewportSize({width:1440,height:1000});
  await page.evaluate(() => {
    if (!navigator.mediaDevices.getUserMedia.toString().includes("__syntheticMicCalls") || !navigator.mediaDevices.getDisplayMedia.toString().includes("__syntheticScreenCalls")) throw new Error("Synthetic media stubs are required");
    const fakeMic=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    Object.defineProperty(navigator.mediaDevices,"getUserMedia",{configurable:true,value:async()=>{ const stream=await fakeMic();window.__syntheticMicStream=stream;return stream; }});
  });
  checks.no_capture_before_start = await page.evaluate(() => !(window.__syntheticMicCalls || window.__syntheticScreenCalls));
  await page.getByRole("button",{name:"Start conversation",exact:true}).click();
  await page.getByRole("button",{name:"Share an image",exact:true}).waitFor({state:"visible"});
  await page.waitForTimeout(250);
  checks.voice_snapshot = await page.getByRole("dialog").ariaSnapshot();
  const picker=page.waitForEvent("filechooser");
  await page.getByRole("button",{name:"Share an image",exact:true}).click();
  await (await picker).setFiles("/Users/tantalum/.codex/worktrees/grok-review-merge-20261015/FYP/desk-companion/tests/fixtures/qwen-vision.jpg");
  await page.getByText(/1 image frames? sent/).waitFor();
  checks.single_image_accepted = true;
  await page.getByRole("button",{name:"Share selected screen",exact:true}).click();
  await page.getByRole("button",{name:"Stop screen sharing",exact:true}).waitFor();
  await page.waitForFunction(() => /[2-9] image frames sent/.test(document.body.innerText), undefined, {timeout:5000});
  checks.screen_sharing_active = true;
  await page.screenshot({path:"/Users/tantalum/.codex/worktrees/grok-review-merge-20261015/FYP/output/qa/2026-10-16-qwen-omni-integration/ui-desktop.png",fullPage:false});
  await page.getByRole("button",{name:"Stop screen sharing",exact:true}).click();
  await page.getByText("Screen sharing off",{exact:false}).waitFor();
  const count=await page.locator(".assistant-vision [role=status]").innerText();
  await page.waitForTimeout(1300);
  checks.stop_blocks_frames = count === await page.locator(".assistant-vision [role=status]").innerText();
  checks.screen_tracks_stopped = await page.evaluate(() => window.__syntheticScreenStream.getTracks().every(track=>track.readyState==="ended"));
  await page.setViewportSize({width:390,height:844});
  checks.no_horizontal_overflow = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  await page.screenshot({path:"/Users/tantalum/.codex/worktrees/grok-review-merge-20261015/FYP/output/qa/2026-10-16-qwen-omni-integration/ui-mobile.png",fullPage:false});
  await page.getByRole("button",{name:"End conversation",exact:true}).click();
  await page.getByRole("button",{name:"Start conversation",exact:true}).waitFor();
  checks.mic_tracks_stopped = await page.evaluate(() => window.__syntheticMicStream.getTracks().every(track=>track.readyState==="ended"));
  checks.javascript_errors = await page.evaluate(() => window.__qaErrors);
  checks.no_framework_overlay = await page.locator("vite-error-overlay").count()===0;
  console.log(JSON.stringify(checks));
}
