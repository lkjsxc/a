export type Section = '社会' | '理科';
export type Page = {
  source: string; path: string; title: string; section: Section;
  group: string; body: string; text: string; minutes: number;
  headings: { id: string; text: string }[]; lesson: boolean;
};
export type Card = { front: string; back: string; tags: string };
export type Deck = { id: string; name: string; cards: Card[] };
export const groups: Record<string, string> = {
  F: '入口', G: '地理', H: '歴史', C: '公民',
  inquiry: '科学的探究', physics: '物理', chemistry: '化学',
  biology: '生物', earth_science: '地学',
  '00_start_here': '理科の学び方', '01_skills': '実験・計算', '02_grade_maps': '学年別マップ',
};
export const escapeHTML = (value: string): string => value.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
export const route = (source: string): string => source.replace(/(^|\/)README\.md$/, '$1index.html').replace(/\.md$/, '.html');
export const normalize = (value: string): string => value.normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60)).replace(/\s+/g, ' ').trim();
export type SearchItem = { path: string; title: string; section: string; text: string };
export function search(items: SearchItem[], query: string, section = ''): SearchItem[] {
  const terms = normalize(query).split(' ').filter(Boolean).slice(0, 8);
  if (!terms.length) return [];
  return items.filter(p => !section || p.section === section).map(p => {
    const title = normalize(p.title), haystack = `${title} ${normalize(p.text)}`;
    return { p, score: terms.every(t => haystack.includes(t)) ? terms.reduce((n, t) => n + (title.includes(t) ? 20 : 1), 0) + (title === normalize(query) ? 100 : 0) : 0 };
  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score || a.p.path.localeCompare(b.p.path, 'ja')).slice(0, 30).map(x => x.p);
}
