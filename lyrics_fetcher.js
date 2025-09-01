const { chromium } = require('playwright');
const fs = require('fs');

async function main() {
  const songUrl = process.argv[2];
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: 'spotify-session.json' });
  const page = await context.newPage();

  let foundLyrics = false;

  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/color-lyrics') && !foundLyrics) {
      try {
        const json = await response.json();
        if (!json?.lyrics?.lines?.length) {
          console.log("🫥 No lyrics found for this track.");
          await browser.close();
          process.exit(2);
        }
        foundLyrics = true;
        fs.writeFileSync('./lyrics.json', JSON.stringify(json, null, 2), 'utf-8');
        console.log("📁 Lyrics JSON saved to ./lyrics.json");
        await browser.close();
        process.exit(0);
      } catch (e) {
        console.error("❌ Failed to parse lyrics JSON:", e.message);
        await browser.close();
        process.exit(1);
      }
    }
  });

  await page.goto(songUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(7000);
  if (!foundLyrics) {
    console.log("❌ Lyrics not found after timeout.");
    await browser.close();
    process.exit(1);
  }
}

main().catch(err => {
  console.error("💥 Unexpected crash in lyrics fetcher:", err);
  process.exit(1);
});
