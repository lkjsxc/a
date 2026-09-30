export const STORAGE_KEY = 'lkjsxc:a:learning:v1';
export type State = {
  version: 1;
  completed: Record<string, true>;
  bookmarks: Record<string, true>;
  last: { path: string; title: string; at: number } | null;
  theme: 'auto' | 'light' | 'dark';
  font: 'normal' | 'large';
};
export const emptyState = (): State => ({ version: 1, completed: {}, bookmarks: {}, last: null, theme: 'auto', font: 'normal' });
export function safePage(path: unknown): path is string {
  return typeof path === 'string' && path.length < 300 && /^(social-studies|000005)\/[\p{L}\p{N}_/ .-]+\.html$/u.test(path) && !path.split('/').some(x => x === '.' || x === '..') && !path.includes('://');
}
export function parseState(raw: string): State {
  if (raw.length > 256_000) throw new Error('記録ファイルが大きすぎます。');
  const data = JSON.parse(raw) as Record<string, unknown>;
  if (!data || typeof data !== 'object' || data.version !== 1) throw new Error('対応していない記録形式です。');
  const state = emptyState();
  for (const key of ['completed', 'bookmarks'] as const) {
    const value = data[key];
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length > 1500) throw new Error('記録の内容を確認してください。');
    for (const [path, flag] of Object.entries(value)) {
      if (!safePage(path) || flag !== true) throw new Error('記録に無効なページが含まれています。');
      state[key][path] = true;
    }
  }
  if (data.last !== null && data.last !== undefined) {
    const last = data.last as Record<string, unknown>;
    if (!safePage(last.path) || typeof last.title !== 'string' || last.title.length > 300 || typeof last.at !== 'number' || !Number.isFinite(last.at)) throw new Error('最近読んだページの記録が無効です。');
    state.last = { path: last.path, title: last.title, at: last.at };
  }
  if (!['auto', 'light', 'dark'].includes(String(data.theme)) || !['normal', 'large'].includes(String(data.font))) throw new Error('表示設定が無効です。');
  state.theme = data.theme as State['theme']; state.font = data.font as State['font'];
  return state;
}
export function mergeState(current: State, incoming: State): State {
  return { ...current, completed: { ...current.completed, ...incoming.completed }, bookmarks: { ...current.bookmarks, ...incoming.bookmarks }, last: !current.last || (incoming.last && incoming.last.at > current.last.at) ? incoming.last : current.last };
}
