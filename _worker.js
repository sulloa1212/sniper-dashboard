// Cloudflare Pages "advanced mode" worker — runs on EVERY request (unlike
// functions/_middleware.js, which never deployed, and unlike a path check on
// ".html", which Pages' pretty-URL redirect to /latest silently bypassed).
//
// The whole site is members-only: direct tab opens and non-browser scrapers
// are blocked for all paths; the dashboard only renders when embedded
// (iframe/image) on the allowed coaching domains.
//
//  - Sec-Fetch-Dest is set by the browser and can't be faked from page JS:
//    "iframe"/"image" for embedded loads, "document" for a direct tab open,
//    null for most non-browser clients.
//  - frame-ancestors locks iframe embedding to the allowed domains.

const ALLOWED = [
  "https://mwtradecoach.com",
  "https://www.mwtradecoach.com",
  "https://mwtradecoaching.com",
  "https://www.mwtradecoaching.com",
];

export default {
  async fetch(request, env) {
    const dest = request.headers.get("Sec-Fetch-Dest");

    if (dest === "document" || dest === null) {
      return new Response(
        "This dashboard is available to members inside the Snipers area only.",
        { status: 403, headers: { "content-type": "text/plain; charset=utf-8" } }
      );
    }

    const res = await env.ASSETS.fetch(request);
    const out = new Response(res.body, res);
    out.headers.set("Content-Security-Policy", "frame-ancestors " + ALLOWED.join(" "));
    return out;
  }
};
