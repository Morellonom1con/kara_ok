const { chromium } = require('playwright');
const fs = require('fs');

async function main() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ storageState: 'spotify-session.json' });
  const page = await context.newPage();

  let lyricsCaptured = false;

  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/color-lyrics') && !lyricsCaptured) {
      lyricsCaptured = true;
      const json = await response.json();
      fs.writeFileSync('./lyrics.json', JSON.stringify(json, null, 2), 'utf-8');
      console.log(`📁 Lyrics JSON saved to ./lyrics.json`);
      await browser.close();
      return;
    }
  });

  const songUrl = process.argv[2];
  await page.goto(songUrl, { waitUntil: 'domcontentloaded' });

  if (lyricsCaptured) return;

  await page.waitForTimeout(7000);
  if (lyricsCaptured) return;

  console.log("Reloading page to trigger lyrics");
  await page.reload({ waitUntil: 'domcontentloaded' });
  if (lyricsCaptured) return;

  await page.waitForTimeout(5000);
  if (lyricsCaptured) return;

  const lyricsButton = await page.$('button[aria-label*="Lyrics"]');
  if (lyricsButton && !lyricsCaptured) {
    await lyricsButton.click();
    await page.waitForTimeout(2000);
  }

  let timeout = 0;
  while (!lyricsCaptured && timeout < 20000) {
    await page.waitForTimeout(1000);
    timeout += 1000;
  }

  if (!lyricsCaptured) {
    await browser.close();
  }
}

main().catch(() => {}); 
