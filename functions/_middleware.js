const ALLOWED = [
  "https://mwtradecoach.com",
  "https://www.mwtradecoach.com",
];

export async function onRequest({ request, next }) {
  const dest = request.headers.get("Sec-Fetch-Dest");

  // Only allow embedded loads (iframe / image) from the Kajabi page.
  // Block everything else: direct opens (root included), scrapers, etc.
  if (dest !== "iframe" && dest !== "image") {
    return new Response(
      "This dashboard is available to members inside the Snipers area only.",
      { status: 403, headers: { "content-type": "text/plain; charset=utf-8" } }
    );
  }

  const res = await next();
  const out = new Response(res.body, res);
  out.headers.set("Content-Security-Policy", "frame-ancestors " + ALLOWED.join(" "));
  return out;
}
