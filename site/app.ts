import { emptyState, parseState, mergeState, safePage, STORAGE_KEY, type State } from './state.ts';
import { search, type SearchItem } from './model.ts';
import { initReview } from './review.ts';

const html = document.documentElement;
const base = html.dataset.base!;
let memory = emptyState(), storageFailed = false;
function read(): State {
  try { const raw = localStorage.getItem(STORAGE_KEY); if (raw) memory = parseState(raw); }
  catch { storageFailed = true; }
  return memory;
}
function save(change: (state: State) => State) {
  memory = change(read());
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(memory)); }
  catch { storageFailed = true; }
  refresh();
}
const get = <T extends HTMLElement>(selector: string) => document.querySelector<T>(selector);
const page = html.dataset.page;
let currentFilter = 'all';
function filterLibrary(state: State) {
  let visible = 0;
  document.querySelectorAll<HTMLElement>('[data-library-item]').forEach(item => {
    const p = item.dataset.path!;
    const show = currentFilter === 'all' || currentFilter === item.dataset.section || (currentFilter === 'bookmarks' && state.bookmarks[p]) || (currentFilter === 'unread' && !state.completed[p]);
    item.hidden = !show; if (show) visible++;
  });
  document.querySelectorAll<HTMLElement>('[data-library-group]').forEach(group => { group.hidden = !group.querySelector('[data-library-item]:not([hidden])'); });
  const status = get('#library-status'); if (status) status.textContent = `${visible}件の読み物を表示しています。`;
  const empty = get('#library-empty'); if (empty) empty.hidden = visible !== 0;
}
function refresh() {
  const state = read();
  html.dataset.theme = state.theme; html.dataset.font = state.font;
  document.querySelectorAll<HTMLInputElement>('input[name="theme"],input[name="font"]').forEach(input => { input.checked = state[input.name as 'theme' | 'font'] === input.value; });
  document.querySelectorAll<HTMLButtonElement>('[data-complete]').forEach(button => { const yes = !!(page && state.completed[page]); button.setAttribute('aria-pressed', String(yes)); button.textContent = yes ? '読了を取り消す' : '読み終えた'; });
  document.querySelectorAll<HTMLButtonElement>('[data-bookmark]').forEach(button => { const yes = !!(page && state.bookmarks[page]); button.setAttribute('aria-pressed', String(yes)); button.textContent = yes ? 'あとで読むから外す' : 'あとで読む'; });
  document.querySelectorAll<HTMLElement>('[data-record-path]').forEach(link => { const marker = link.querySelector<HTMLElement>('.read-marker'); if (marker) marker.hidden = !state.completed[link.dataset.recordPath!]; });
  const panel = get('#continue-panel'), link = get<HTMLAnchorElement>('#continue-link');
  if (panel && link) {
    panel.hidden = !state.last;
    if (state.last) { link.href = `${base}${encodeURI(state.last.path)}`; get('#continue-title')!.textContent = state.last.title; }
  }
  if (storageFailed) { const status = get('[data-storage-status]'); if (status) status.textContent = 'このブラウザーでは記録を保存・読み込みできない場合があります。必要な記録は表示設定から書き出してください。'; }
  filterLibrary(state);
}
read();
if (safePage(page)) save(state => ({ ...state, last: { path: page, title: html.dataset.title || page, at: Date.now() } }));
else refresh();
document.querySelectorAll<HTMLElement>('[data-enhanced]').forEach(el => { el.hidden = false; });
document.querySelectorAll<HTMLElement>('[data-complete],[data-bookmark]').forEach(button => button.addEventListener('click', () => {
  if (!safePage(page)) return;
  const key = button.hasAttribute('data-complete') ? 'completed' : 'bookmarks';
  save(state => { if (state[key][page]) delete state[key][page]; else state[key][page] = true; return state; });
}));
document.querySelectorAll<HTMLElement>('[data-print]').forEach(button => button.addEventListener('click', () => window.print()));
document.querySelectorAll<HTMLElement>('[data-filter]').forEach(button => button.addEventListener('click', () => {
  currentFilter = button.dataset.filter!;
  document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
  filterLibrary(read());
}));
window.addEventListener('storage', event => { if (event.key === STORAGE_KEY) { memory = emptyState(); refresh(); } });

document.querySelectorAll<HTMLElement>('[data-close-dialog]').forEach(button => button.addEventListener('click', () => button.closest('dialog')!.close()));
document.querySelectorAll<HTMLDialogElement>('dialog').forEach(dialog => dialog.addEventListener('click', event => {
  if (event.target !== dialog) return;
  const r = dialog.getBoundingClientRect();
  if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
}));
const settings = get<HTMLDialogElement>('#settings-dialog')!;
document.querySelectorAll('[data-open-settings]').forEach(b => b.addEventListener('click', () => { refresh(); settings.showModal(); }));
document.querySelectorAll<HTMLInputElement>('input[name="theme"],input[name="font"]').forEach(input => input.addEventListener('change', () => {
  if (input.name === 'theme') save(state => ({ ...state, theme: input.value as State['theme'] }));
  else save(state => ({ ...state, font: input.value as State['font'] }));
}));
get('#export-state')!.addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(read(), null, 2)], { type: 'application/json' });
  const objectURL = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = objectURL; link.download = `a-learning-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(objectURL), 1000);
  get('#settings-status')!.textContent = '学習記録を書き出しました。ダウンロードしたファイルを保管してください。';
});
get<HTMLInputElement>('#import-state')!.addEventListener('change', async event => {
  const input = event.target as HTMLInputElement, file = input.files?.[0]; if (!file) return;
  try {
    if (file.size > 256_000) throw new Error('記録ファイルが大きすぎます。');
    const incoming = parseState(await file.text());
    save(current => mergeState(current, incoming));
    get('#settings-status')!.textContent = '読了・あとで読む記録を取り込みました。元の記録と表示設定は残しています。';
  } catch (error) { get('#settings-status')!.textContent = `取り込めませんでした。${error instanceof Error ? error.message : ''} 元の記録は変更していません。`; }
  input.value = '';
});
get('#reset-state')!.addEventListener('click', () => {
  if (!confirm('このブラウザーにある、このサイトの学習記録と表示設定を消しますか？')) return;
  try { localStorage.removeItem(STORAGE_KEY); } catch { storageFailed = true; }
  memory = emptyState(); refresh(); get('#settings-status')!.textContent = 'このサイトの学習記録を消去しました。';
});

const dialog = get<HTMLDialogElement>('#search-dialog')!, input = get<HTMLInputElement>('#search-input')!, section = get<HTMLSelectElement>('#search-section')!, status = get('#search-status')!, results = get('#search-results')!;
let index: SearchItem[] | null = null, fetching: Promise<SearchItem[]> | null = null, queryVersion = 0;
async function find() {
  const version = ++queryVersion;
  const query = input.value.trim(); results.replaceChildren();
  if (!query) { status.textContent = 'ことばを入力すると、本文も含めて検索できます。'; return; }
  status.textContent = '教材を検索しています…';
  try {
    if (!index) {
      fetching ||= fetch(`${base}search.json`).then(async response => { if (!response.ok) throw new Error(); return await response.json() as SearchItem[]; }).catch(error => { fetching = null; throw error; });
      index = await fetching;
    }
    if (version !== queryVersion) return;
    const matches = search(index, query, section.value);
    status.textContent = matches.length ? `${matches.length}件${matches.length === 30 ? '（上位30件）' : ''}の教材が見つかりました。` : '見つかりませんでした。短いことばや、別の表記で試してください。';
    for (const match of matches) {
      const li = document.createElement('li'), link = document.createElement('a'), label = document.createElement('strong'), meta = document.createElement('small'), excerpt = document.createElement('p');
      link.href = `${base}${encodeURI(match.path)}`; label.textContent = match.title; meta.textContent = match.section;
      const at = match.text.indexOf(query.split(/\s+/)[0]);
      excerpt.textContent = `${at > 40 ? '…' : ''}${match.text.slice(Math.max(0, at - 40), Math.max(0, at - 40) + 145)}…`;
      link.append(meta, label, excerpt); li.append(link); results.append(li);
    }
  } catch { if (version === queryVersion) status.textContent = '検索データを読み込めませんでした。通信を確認して再入力してください。教材一覧からはそのまま探せます。'; }
}
let timer: ReturnType<typeof setTimeout>;
input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(find, 120); });
section.addEventListener('change', find);
function openSearch() { if (!dialog.open) dialog.showModal(); input.focus(); }
document.querySelectorAll('[data-open-search]').forEach(button => button.addEventListener('click', openSearch));
document.addEventListener('keydown', event => {
  const target = event.target as HTMLElement;
  if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !settings.open && !target.closest('input,textarea,select,[contenteditable="true"]')) { event.preventDefault(); openSearch(); }
});
initReview(base);
