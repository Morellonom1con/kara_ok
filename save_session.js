const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto('https://accounts.spotify.com/login');
  console.log('Log in manually, then close the browser to save session.');

  // Instead of fixed timeout, let’s pause until you manually resume:
  await page.pause();

  // Save storage state (cookies, localStorage, etc)
  await context.storageState({ path: 'spotify-session.json' });
  console.log('Session saved as spotify-session.json');

  await browser.close();
})();
