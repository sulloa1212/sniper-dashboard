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

  // Maintain 5 most recent days and create manifest
  const files = fs.readdirSync('archive');
  const htmlFiles = files.filter(f => f.match(/^\d{4}-\d{2}-\d{2}\.html$/)).sort().reverse();
  
  const recent = htmlFiles.slice(0, 5);
  const toDelete = htmlFiles.slice(5);

  toDelete.forEach(f => {
    fs.unlinkSync(path.join('archive', f));
    const pngFile = f.replace('.html', '.png');
    if (fs.existsSync(path.join('archive', pngFile))) {
      fs.unlinkSync(path.join('archive', pngFile));
    }
  });

  const manifest = recent.map(f => {
    const d = f.replace('.html', '');
    // Parse date safely treating it as UTC noon to avoid timezone shifts
    const dateObj = new Date(d + 'T12:00:00Z');
    // Format to "Thu Jun 18"
    const label = new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
      .format(dateObj)
      .replace(',', ''); // remove comma if present
      
    return {
      date: d,
      file: `archive/${f}`,
      label: label
    };
  });

  fs.writeFileSync(path.join('archive', 'index.json'), JSON.stringify(manifest, null, 2));

  console.log('Rendered latest.png and archived ' + date);
})();
