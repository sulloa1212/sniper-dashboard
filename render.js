// Renders latest.png from latest.html and saves dated copies into /archive.
// Runs automatically in GitHub Actions whenever latest.html changes.
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
  // Today's date in US Eastern time (matches the market day)
  const date = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(new Date()); // -> YYYY-MM-DD

  const fileUrl = 'file://' + path.resolve('latest.html');

  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1240, height: 1600, deviceScaleFactor: 2 });
  await page.goto(fileUrl, { waitUntil: 'networkidle0' });

  // Let any in-page drawing (dials, bars) finish
  await new Promise(r => setTimeout(r, 2000));

  // Screenshot ONLY the clean dashboard card (#shareable), not the toolbar buttons
  const node = await page.$('#shareable');
  if (node) {
    await node.screenshot({ path: 'latest.png' });
  } else {
    await page.screenshot({ path: 'latest.png', fullPage: true });
  }
  await browser.close();

  // Dated archive copies
  fs.mkdirSync('archive', { recursive: true });
  fs.copyFileSync('latest.html', path.join('archive', `${date}.html`));
  fs.copyFileSync('latest.png',  path.join('archive', `${date}.png`));

  console.log('Rendered latest.png and archived ' + date);
})();
