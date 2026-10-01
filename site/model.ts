export type Section = '社会' | '理科';
export type Page = {
  source: string; path: string; title: string; section: Section;
  group: string; body: string;
  headings: { id: string; text: string }[]; lesson: boolean;
};
export type Card = { front: string; back: string; tags: string };
export type Deck = { id: string; name: string; cards: Card[] };
export const groups: Record<string, string> = {
  F: '基礎', G: '地理', H: '歴史', C: '公民',
  inquiry: '科学的探究', physics: '物理', chemistry: '化学',
  biology: '生物', earth_science: '地学',
  '00_start_here': '学習案内', '01_skills': '実験・計算', '02_grade_maps': '学年別教材',
};
export const escapeHTML = (value: string): string => value.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
export const route = (source: string): string => source.replace(/(^|\/)README\.md$/, '$1index.html').replace(/\.md$/, '.html');
