// Cloudflare Pages gate: the dashboard only loads when EMBEDDED inside your
// Kajabi site. Opening latest.html or latest.png directly in a browser tab,
// or embedding it on any other website, is blocked.
//
// How it works:
//  - Sec-Fetch-Dest tells us how the file is being requested. A browser sends
//    "iframe" / "image" for embedded loads, and "document" for a direct tab open.
//    These headers are set by the browser and can't be faked from page JavaScript.
//  - frame-ancestors locks iframe embedding to your domain only.

const ALLOWED = [
  "https://mwtradecoach.com",
  "https://www.mwtradecoach.com",
];

export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  const isDashboard = url.pathname.endsWith(".html") || url.pathname.endsWith(".png");
  const dest = request.headers.get("Sec-Fetch-Dest"); // iframe | image | document | null

  // Block direct tab opens (and non-browser scrapers) of the dashboard files.
  if (isDashboard && (dest === "document" || dest === null)) {
    return new Response(
      "This dashboard is available to members inside the Snipers area only.",
      { status: 403, headers: { "content-type": "text/plain; charset=utf-8" } }
    );
  }

  const res = await next();
  const out = new Response(res.body, res);
  // Allow embedding only on your Kajabi domain.
  out.headers.set("Content-Security-Policy", "frame-ancestors " + ALLOWED.join(" "));
  return out;
}
