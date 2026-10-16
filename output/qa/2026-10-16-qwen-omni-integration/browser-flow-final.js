async (page) => {
  const checks = { browser_plugin: "absent; regular Playwright CLI", url: page.url(), title: await page.title() };
  await page.setViewportSize({width:1440,height:1000});
  await page.reload();
  await page.getByRole("button",{name:"Open assistant",exact:true}).click();
  checks.initial_dialog = await page.getByRole("dialog").ariaSnapshot();
  await page.evaluate(() => {
    window.__qaErrors=[];
    window.addEventListener("error", e=>window.__qaErrors.push(e.message));
    window.__syntheticMicCalls=0; window.__syntheticScreenCalls=0;
    window.__syntheticContexts=[];
    Object.defineProperty(navigator.mediaDevices,"getUserMedia",{configurable:true,value:async()=>{
      window.__syntheticMicCalls++;
      const context=new AudioContext();window.__syntheticContexts.push(context);
      const oscillator=context.createOscillator(),gain=context.createGain(),destination=context.createMediaStreamDestination();
      gain.gain.value=0;oscillator.connect(gain).connect(destination);oscillator.start();
      window.__syntheticMicStream=destination.stream;return destination.stream;
    }});
    Object.defineProperty(navigator.mediaDevices,"getDisplayMedia",{configurable:true,value:async()=>{
      window.__syntheticScreenCalls++;
      const canvas=document.createElement("canvas");canvas.width=640;canvas.height=360;
      const context=canvas.getContext("2d");context.fillStyle="#648cdc";context.fillRect(0,0,640,360);
      context.fillStyle="white";context.font="24px sans-serif";context.fillText("Synthetic screen fixture",36,60);
      window.__syntheticScreenStream=canvas.captureStream(1);return window.__syntheticScreenStream;
    }});
    const banner=document.createElement("div");banner.innerText="SYNTHETIC QA · no external provider calls";
    banner.style="position:fixed;bottom:4px;left:4px;z-index:99999;background:#dfe5f5;font:10px sans-serif;padding:4px";document.body.append(banner);
  });
  checks.no_capture_before_start = await page.evaluate(()=>window.__syntheticMicCalls===0 && window.__syntheticScreenCalls===0);
  await page.getByRole("button",{name:"Start conversation",exact:true}).click();
  await page.getByRole("button",{name:"Share an image",exact:true}).waitFor({state:"visible"});
  await page.waitForTimeout(250);
  checks.voice_snapshot = await page.getByRole("dialog").ariaSnapshot();
  await page.locator(".assistant-vision input[type=file]").setInputFiles("/Users/tantalum/.codex/worktrees/grok-review-merge-20261015/FYP/desk-companion/tests/fixtures/qwen-vision.jpg");
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
  await page.evaluate(value => { window.__omniQAChecks=value; for (const context of window.__syntheticContexts) void context.close(); }, checks);
  return checks;
}
