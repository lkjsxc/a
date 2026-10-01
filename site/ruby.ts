import { readFileSync } from 'node:fs';
import { parseHTML } from 'linkedom';
import { escapeHTML } from './model.ts';

/** Editorial allowlist, never an automatic list of all kanji or card titles. */
export const glossary = JSON.parse(readFileSync(new URL('../editorial/ruby.json', import.meta.url), 'utf8')) as Record<string, string>;
for (const [word, reading] of Object.entries(glossary)) {
  if (!word || !/^[ぁ-ゖー・]+$/.test(reading)) throw new Error(`Invalid ruby entry: ${word}`);
}
const escaped = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const alternatives = Object.keys(glossary).sort((a, b) => b.length - a.length || a.localeCompare(b, 'ja')).map(escaped).join('|');
const boundary = '[\\p{Script=Han}々A-Za-z0-9ァ-ヶ]';
const pattern = new RegExp(`(?<!${boundary})(?:${alternatives})(?!${boundary})`, 'gu');

export function stripRuby(value: string): string {
  return value.replace(/<ruby\b[^>]*>([\s\S]*?)<\/ruby>/gi, (_, body: string) => body.replace(/<(rt|rp)\b[^>]*>[\s\S]*?<\/\1>/gi, ''));
}
function annotate(text: string, seen: Set<string>): string {
  return text.replace(pattern, word => {
    if (seen.has(word)) return word;
    seen.add(word);
    return `<ruby>${word}<rp>（</rp><rt>${glossary[word]}</rt><rp>）</rp></ruby>`;
  });
}
export function rubyText(value: string, seen = new Set<string>()): string {
  return annotate(escapeHTML(value), seen);
}

/** Normalizes old annotations before matching, so 二<ruby>酸化</ruby>炭素 stays one word. */
export function rubyHTML(value: string): string {
  const { document } = parseHTML(`<html><body>${value}</body></html>`);
  for (const old of Array.from(document.querySelectorAll('ruby'))) {
    if (old.closest('code,pre,script,style,textarea')) continue;
    old.querySelectorAll('rt,rp').forEach(el => el.remove());
    old.replaceWith(...Array.from(old.childNodes));
  }
  document.body.normalize();
  const skip = new Set(['code', 'pre', 'script', 'style', 'textarea', 'rt', 'rp', 'ruby']);
  const independent = new Set(['td', 'th', 'li', 'details', 'summary']);
  const section = { seen: new Set<string>() };
  const visit = (node: Node, scope: { seen: Set<string> }) => {
    if (node.nodeType === 3) {
      const text = node.textContent || '';
      const result = rubyText(text, scope.seen);
      if (result !== escapeHTML(text)) {
        const template = document.createElement('template'); template.innerHTML = result;
        node.parentNode!.replaceChild(template.content, node);
      }
      return;
    }
    if (node.nodeType !== 1) return;
    const el = node as Element;
    if (skip.has(el.localName)) return;
    const heading = /^h[1-6]$/.test(el.localName);
    if (heading) scope.seen = new Set();
    const innerScope = heading || independent.has(el.localName) ? { seen: new Set<string>() } : scope;
    for (const child of Array.from(el.childNodes)) visit(child, innerScope);
    if (heading) scope.seen = new Set();
  };
  for (const child of Array.from(document.body.childNodes)) visit(child, section);
  return document.body.innerHTML;
}

/** Preserve Markdown, links, HTML attributes, inline/fenced code, and original base text. */
export function rubyMarkdown(value: string): string {
  let seen = new Set<string>(); let fence = '';
  return value.split('\n').map(line => {
    const marker = /^\s*(`{3,}|~{3,})/.exec(line)?.[1];
    if (marker) { if (!fence) fence = marker[0]; else if (fence === marker[0]) fence = ''; return line; }
    if (fence) return line;
    // Preserve literal markup inside inline code before unwrapping old annotations.
    line = line.split(/(`+[^`]*`+)/g).map((part, i) => i % 2 ? part : stripRuby(part)).join('');
    const heading = /^\s*#{1,6}\s/.test(line);
    const independent = /^\s*(?:\||[-*+]\s|\d+\.\s|<details\b|<summary\b)/.test(line);
    if (heading) seen = new Set();
    const scope = independent ? new Set<string>() : seen;
    const protect = /(`+)[\s\S]*?\1|!?\[[^\]]*\]\([^\n]*?\)|<[^>]*>|https?:\/\/[^\s<>]+|&(?:#\w+|\w+);/g;
    let start = 0, result = '';
    for (const m of line.matchAll(protect)) {
      result += annotate(line.slice(start, m.index), scope) + m[0]; start = m.index! + m[0].length;
    }
    result += annotate(line.slice(start), scope);
    if (heading) seen = new Set();
    return result;
  }).join('\n');
}
