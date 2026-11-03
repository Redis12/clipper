// Rend la scène 3D palier par palier : PS2 → 720p → 1080p → 1440p → 4K → 4K + shader boost
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
(async () => {
  const out = process.argv[2] || 'poc.mp4';
  const segS = parseFloat(process.argv[3] || '6.5'), fps = parseInt(process.argv[4] || '30');
  const steps = [[240, 'PS2', 0], [720, '720p', 0], [1080, '1080p', 0], [1440, '1440p', 0], [1920, '4K', 0], [1920, '4K + shader boost', 1]];
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('console', m => console.log('page:', m.text()));
  await page.goto('file://' + path.resolve(__dirname, 'scene.html'));
  await page.waitForFunction(() => window.ready === true, null, { timeout: 30000 });
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (const [res, label, boost] of steps) {
    for (let f = 0; f < Math.round(segS * fps); f++) {
      await page.evaluate(([t, r, l, b]) => window.renderFrame(t, r, l, b), [f / fps, res, label, boost]);
      const buf = await page.screenshot({ type: 'jpeg', quality: 90 });
      ff.stdin.write(buf);
    }
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('ok', out, ((Date.now() - t0) / 1000).toFixed(1) + 's');
})();
