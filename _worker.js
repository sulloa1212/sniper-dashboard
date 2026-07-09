// Cloudflare Pages "advanced mode" worker.
//
// Reports are link-shared: members get a link that lands them on this domain,
// so direct browser opens are allowed. The only restriction kept is
// frame-ancestors, so other websites can't iframe-embed the report on their
// own pages (the coaching domains still can).

const ALLOWED = [
  "https://mwtradecoach.com",
  "https://www.mwtradecoach.com",
  "https://mwtradecoaching.com",
  "https://www.mwtradecoaching.com",
];

export default {
  async fetch(request, env) {
    const res = await env.ASSETS.fetch(request);
    const out = new Response(res.body, res);
    out.headers.set("Content-Security-Policy", "frame-ancestors " + ALLOWED.join(" "));
    return out;
  },
};
