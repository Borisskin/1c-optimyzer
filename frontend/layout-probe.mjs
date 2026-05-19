import { chromium } from "playwright";

const sizes = [
  { name: "1280x680 (worst case Sergey)", w: 1280, h: 680 },
  { name: "1280x720 (minHeight)", w: 1280, h: 720 },
  { name: "1440x900 (default)", w: 1440, h: 900 },
  { name: "1920x1080 (FHD maximize)", w: 1920, h: 1080 },
  { name: "2560x1440 (QHD maximize)", w: 2560, h: 1440 },
];

const browser = await chromium.launch({ headless: true });
try {
  for (const size of sizes) {
    const ctx = await browser.newContext({ viewport: { width: size.w, height: size.h } });
    const page = await ctx.newPage();
    await page.goto("http://localhost:1420/", { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    const m = await page.evaluate(() => {
      const r = (sel) => {
        const e = document.querySelector(sel);
        return e ? Math.round(e.getBoundingClientRect().height * 10) / 10 : null;
      };
      const sb = document.querySelector(".app").querySelectorAll(":scope > *");
      const statusbar = [...sb].find((el) => el.className?.includes?.("_statusbar"));
      const sbRect = statusbar?.getBoundingClientRect();
      return {
        viewport: window.innerHeight,
        app: r(".app"),
        main: r(".app__main"),
        statusbarTop: sbRect ? Math.round(sbRect.top) : null,
        statusbarBottom: sbRect ? Math.round(sbRect.bottom) : null,
        statusbarInView: sbRect && sbRect.bottom <= window.innerHeight && sbRect.top >= 0,
        bodyScroll: document.body.scrollHeight,
      };
    });
    console.log(`${size.name.padEnd(36)}  vp=${m.viewport} app=${m.app} main=${m.main} sb=${m.statusbarTop}-${m.statusbarBottom} inView=${m.statusbarInView} bodyScrollH=${m.bodyScroll}`);
    await ctx.close();
  }
} finally {
  await browser.close();
}
