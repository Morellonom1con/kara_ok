const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ storageState: 'spotify-session.json' });
  const page = await context.newPage();

  await page.goto(process.argv[2], { waitUntil: 'domcontentloaded' });
  
  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/color-lyrics')) {
      try {
        const json = await response.json();
        const path = './lyrics.json'; // or any path you prefer
        fs.writeFileSync(path, JSON.stringify(json, null, 2), 'utf-8');
        console.log(`📁 Lyrics JSON saved to ${path}`);
      } catch (e) {
        console.error('⚠️ Failed to parse lyrics JSON:', e);
      } finally {
        await browser.close();
      }
    }
  });


  await page.waitForTimeout(120000);
  await browser.close();
})();