import type { Card } from './model.ts';

export function shuffled<T>(items: readonly T[], random = Math.random): T[] {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) { const j = Math.floor(random() * (i + 1)); [result[i], result[j]] = [result[j], result[i]]; }
  return result;
}
export function initReview(base: string): void {
  if (!document.querySelector('#review-app')) return;
  const q = <T extends HTMLElement>(selector: string) => document.querySelector<T>(selector)!;
  const set = q<HTMLSelectElement>('#review-set'), count = q<HTMLSelectElement>('#review-count'), start = q<HTMLButtonElement>('#review-start');
  const status = q('#review-status'), flash = q('#flashcard'), finish = q('#review-finish'), front = q('#card-front'), answer = q('#card-answer');
  const reveal = q<HTMLButtonElement>('#reveal-card'), grade = q('#grade-card'), retry = q<HTMLButtonElement>('#retry-cards');
  const params = new URLSearchParams(location.search);
  if (Array.from(set.options).some(o => o.value === params.get('set'))) set.value = params.get('set')!;
  let unit = set.value === 'social' && /^[FGHC]\d\d$/.test(params.get('unit') || '') ? params.get('unit')! : '';
  if (unit) status.textContent = `${unit} のカードを練習します。`;
  const cache = new Map<string, Card[]>();
  let session: Card[] = [], again: Card[] = [], position = 0, known = 0, generation = 0;
  function show() {
    const card = session[position];
    flash.hidden = false; finish.hidden = true;
    q('#card-position').textContent = `${position + 1} / ${session.length}${unit ? ` · ${unit}` : ''}`;
    front.innerHTML = card.front; answer.innerHTML = card.back;
    answer.hidden = true; grade.hidden = true; reveal.hidden = false; reveal.disabled = false;
    front.focus();
  }
  function begin(cards: Card[]) {
    session = cards; again = []; position = 0; known = 0;
    status.textContent = '答えを見る前に、自分のことばで説明してみましょう。';
    show();
  }
  async function load() {
    const token = ++generation; start.disabled = true;
    status.textContent = 'カードを読み込んでいます…'; flash.hidden = true; finish.hidden = true;
    try {
      const id = set.value;
      let cards = cache.get(id);
      if (!cards) {
        const response = await fetch(`${base}data/${encodeURIComponent(id)}.json`);
        if (!response.ok) throw new Error('データを取得できませんでした。');
        const data: unknown = await response.json();
        if (!Array.isArray(data) || !data.length || data.length > 10000 || !data.every(c => c && typeof c.front === 'string' && typeof c.back === 'string' && typeof c.tags === 'string')) throw new Error('カードの形式を確認できませんでした。');
        cards = data as Card[]; cache.set(id, cards);
      }
      if (token !== generation) return;
      const pool = unit ? cards.filter(c => c.tags.split(/\s+/).includes(`単元::${unit}`)) : cards;
      if (!pool.length) throw new Error('この単元に対応するカードがありません。教材を選び直してください。');
      begin(shuffled(pool).slice(0, Number(count.value)));
    } catch (error) {
      if (token === generation) status.textContent = `${error instanceof Error ? error.message : '読み込みに失敗しました。'} 通信を確認し、「練習をはじめる」で再試行できます。`;
    } finally { if (token === generation) start.disabled = false; }
  }
  start.addEventListener('click', load);
  set.addEventListener('change', () => { generation++; unit = ''; start.disabled = false; flash.hidden = true; finish.hidden = true; status.textContent = '新しい教材を選びました。「練習をはじめる」で開始します。'; history.replaceState(null, '', `${location.pathname}?set=${encodeURIComponent(set.value)}`); });
  reveal.addEventListener('click', () => { answer.hidden = false; reveal.hidden = true; grade.hidden = false; q<HTMLButtonElement>('#card-known').focus(); });
  function rate(remembered: boolean) {
    if (grade.hidden || !session[position]) return;
    grade.hidden = true;
    if (remembered) known++; else again.push(session[position]);
    position++;
    if (position < session.length) { show(); return; }
    flash.hidden = true; finish.hidden = false;
    q('#review-summary').textContent = `${session.length}枚のうち、${known}枚を「思い出せた」と確認しました。${again.length ? ` ${again.length}枚をもう一度練習できます。` : ' 別の単元にも進んでみましょう。'}`;
    status.textContent = '今回の練習は終了です。'; retry.hidden = again.length === 0;
    finish.querySelector<HTMLElement>('h2')!.focus();
  }
  q('#card-again').addEventListener('click', () => rate(false));
  q('#card-known').addEventListener('click', () => rate(true));
  retry.addEventListener('click', () => begin([...again]));
  q('#restart-cards').addEventListener('click', load);
}
