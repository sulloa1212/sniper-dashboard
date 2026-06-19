const ALLOWED = [
  "https://mwtradecoach.com",
  "https://www.mwtradecoach.com",
];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const isDashboard = url.pathname.endsWith(".html") || url.pathname.endsWith(".png");
    const dest = request.headers.get("Sec-Fetch-Dest");

    // Block direct tab opens (and non-browser scrapers) of the dashboard files.
    if (isDashboard && (dest === "document" || dest === null)) {
      return new Response(
        "This dashboard is available to members inside the Snipers area only.",
        { status: 403, headers: { "content-type": "text/plain; charset=utf-8" } }
      );
    }

    // Serve the static files natively from the ASSETS binding
    const res = await env.ASSETS.fetch(request);
    const out = new Response(res.body, res);
    
    // Allow embedding only on your Kajabi domain.
    out.headers.set("Content-Security-Policy", "frame-ancestors " + ALLOWED.join(" "));
    return out;
  }
};
