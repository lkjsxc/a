import { marked } from 'marked';
import sanitize from 'sanitize-html';
import Slugger from 'github-slugger';
import { parseHTML } from 'linkedom';
import posix from 'node:path/posix';
import { route, type Page, groups } from './model.ts';
import { rubyHTML } from './ruby.ts';

export function clean(html: string): string {
  return sanitize(html, {
    allowedTags: [...sanitize.defaults.allowedTags, 'ruby', 'rt', 'rp', 'details', 'summary', 'img', 'figure', 'figcaption'],
    allowedAttributes: { '*': ['id', 'class'], a: ['href', 'title'], img: ['src', 'alt', 'width', 'height', 'loading', 'decoding'], th: ['align', 'colspan', 'rowspan', 'scope'], td: ['align', 'colspan', 'rowspan'], details: ['open'] },
    allowedSchemes: ['https', 'http', 'mailto'], allowProtocolRelative: false,
  });
}
export function plain(html: string, readings = false): string {
  const { document } = parseHTML(`<html><body>${html}</body></html>`);
  if (!readings) document.querySelectorAll('rt,rp').forEach(x => x.remove());
  return document.body.textContent!.replace(/\s+/g, ' ').trim();
}
export function localTarget(href: string, source: string): { path: string; suffix: string } | null {
  if (!href || href.startsWith('#') || /^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(href)) return null;
  const at = href.search(/[?#]/), name = at < 0 ? href : href.slice(0, at), suffix = at < 0 ? '' : href.slice(at);
  let decoded: string;
  try { decoded = decodeURIComponent(name); } catch { return null; }
  const path = posix.normalize(decoded.startsWith('/') ? decoded.slice(1) : posix.join(posix.dirname(source), decoded));
  if (path === '..' || path.startsWith('../') || path.includes('\\')) throw new Error(`Outside-repository URL in ${source}: ${href}`);
  return { path, suffix };
}
export function render(source: string, markdown: string, sources: Set<string>, files: Set<string>, images: Map<string, string>, base: string): Page {
  const { document } = parseHTML(`<html><body>${rubyHTML(clean(marked.parse(markdown, { async: false }) as string))}</body></html>`);
  const heading = document.querySelector('h1');
  const title = plain(heading?.innerHTML || posix.basename(source, '.md'));
  heading?.remove();
  const slugger = new Slugger();
  const headings: Page['headings'] = [];
  let haveH2 = false;
  for (const el of Array.from(document.querySelectorAll('h1'))) {
    const replacement = document.createElement('h2'); replacement.innerHTML = el.innerHTML; el.replaceWith(replacement);
  }
  for (const el of Array.from(document.querySelectorAll('h2,h3,h4,h5,h6'))) {
    // Some original lessons begin with h3; keep the initial reading sections at h2.
    if (el.localName === 'h2') haveH2 = true;
    let node = el;
    if (!haveH2 && el.localName === 'h3') {
      node = document.createElement('h2'); node.innerHTML = el.innerHTML; el.replaceWith(node);
    }
    const text = plain(node.innerHTML), id = slugger.slug(text);
    node.id = id;
    if (node.localName === 'h2' || node.localName === 'h3') headings.push({ id, text });
  }
  for (const anchor of document.querySelectorAll('a[href]')) {
    const href = anchor.getAttribute('href')!;
    const target = localTarget(href, source);
    if (!target) continue;
    const dirIndex = `${target.path.replace(/\/$/, '')}/README.md`;
    if (sources.has(target.path)) anchor.setAttribute('href', `${base}${encodeURI(route(target.path))}${target.suffix}`);
    else if (sources.has(dirIndex)) anchor.setAttribute('href', `${base}${encodeURI(route(dirIndex))}${target.suffix}`);
    else if (files.has(target.path)) anchor.setAttribute('href', `${base}${encodeURI(target.path)}${target.suffix}`);
    else anchor.setAttribute('href', `https://github.com/lkjsxc/a/blob/main/${encodeURI(target.path)}${target.suffix}`);
  }
  for (const image of document.querySelectorAll('img')) {
    const target = localTarget(image.getAttribute('src') || '', source);
    if (target) {
      if (!files.has(target.path)) throw new Error(`Missing image: ${source} -> ${target.path}`);
      image.setAttribute('src', `${base}${encodeURI(images.get(target.path) || target.path)}`);
    }
    image.setAttribute('loading', 'lazy'); image.setAttribute('decoding', 'async');
  }
  for (const table of document.querySelectorAll('table')) {
    const wrapper = document.createElement('div'); wrapper.className = 'table-scroll';
    wrapper.setAttribute('tabindex', '0'); wrapper.setAttribute('role', 'region'); wrapper.setAttribute('aria-label', '横にスクロールできる表');
    table.replaceWith(wrapper); wrapper.append(table);
    table.querySelectorAll('thead th').forEach(th => th.setAttribute('scope', 'col'));
  }
  for (const pre of document.querySelectorAll('pre')) pre.setAttribute('tabindex', '0');
  // A static print copy works even in engines that hide a closed details shadow tree.
  for (const details of Array.from(document.querySelectorAll('details'))) {
    if (details.parentElement?.closest('details')) continue;
    const printed = document.createElement('div'); printed.className = 'print-answer';
    for (const child of Array.from(details.children)) {
      if (child.localName === 'summary') {
        const label = document.createElement('p'); label.className = 'answer-label'; label.innerHTML = child.innerHTML; printed.append(label);
      } else printed.append(child.cloneNode(true));
    }
    printed.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
    details.after(printed);
  }
  const social = source.startsWith('social-studies/');
  const code = posix.basename(source, '.md');
  const category = source.split('/')[2];
  const lesson = social ? /^textbook\/[FGHC]\d\d\.md$/.test(source.slice(15)) : source.startsWith('000005/reading/') && !source.endsWith('README.md');
  return { source, path: route(source), title, section: social ? '社会' : '理科', group: social ? (groups[code[0]] && /^[FGHC]\d\d$/.test(code) ? groups[code[0]] : '社会の資料') : (groups[category] || '理科の資料'), body: document.body.innerHTML, headings, lesson };
}
