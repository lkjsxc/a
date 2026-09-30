import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '../_site');
const base = new URL(process.env.SITE_URL || 'https://lkjsxc.github.io/a/').pathname;
const port = Number(process.env.PORT || 4173);
const types: Record<string, string> = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.xml': 'application/xml', '.csv': 'text/csv; charset=utf-8', '.tsv': 'text/tab-separated-values; charset=utf-8' };
const server = createServer(async (request, response) => {
  if (!['GET', 'HEAD'].includes(request.method || '')) { response.writeHead(405); response.end(); return; }
  try {
    const requested = decodeURIComponent(new URL(request.url!, 'http://localhost').pathname);
    if (requested === base.slice(0, -1)) { response.writeHead(308, { location: base }); response.end(); return; }
    if (!requested.startsWith(base)) { response.writeHead(404); response.end('Not found'); return; }
    let target = path.resolve(root, requested.slice(base.length) || '.');
    if (target !== root && !target.startsWith(`${root}${path.sep}`)) { response.writeHead(403); response.end(); return; }
    if ((await stat(target)).isDirectory()) target = path.join(target, 'index.html');
    const bytes = await readFile(target);
    response.writeHead(200, { 'Content-Type': types[path.extname(target)] || 'application/octet-stream', 'Content-Length': bytes.length, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    response.end(request.method === 'HEAD' ? undefined : bytes);
  } catch {
    response.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
    response.end(await readFile(path.join(root, '404.html')));
  }
});
server.listen(port, '127.0.0.1', () => console.log(`Preview: http://127.0.0.1:${port}${base}`));
process.on('SIGTERM', () => server.close());
process.on('SIGINT', () => server.close());
