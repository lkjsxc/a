import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { compareMaterial, inspectSocialMaterial, readAuthoredLessons, type AuthoredLesson } from '../social-artifact-audit.ts';

const lesson: AuthoredLesson = {
  id: 'F01', title: '社会の仕組み', paragraphs: ['### 用語', '本文の説明です。'],
  cards: [{ id: 'F01-01', front: '国' }],
  questions: [{ id: 'F01-Q01', prompt: '理由を説明してください。', answer: '解答です。', explanation: '根拠です。' }],
};
const fullText = '# F01 社会の仕組み\n### 用語\n本文の説明です。\n理由を説明してください。\n解答です。\n根拠です。';

test('artifact parity audit accepts matching content without writing files', () => {
  assert.equal(compareMaterial([lesson], [{ ID: 'F01-01', Keyword: '国' }], new Map([['F01', fullText]])).status, 'passed');
});
test('artifact parity detects missing and changed notes independently', () => {
  const added = { ...lesson, cards: [...lesson.cards, { id: 'F01-02', front: '政治' }] };
  const report = compareMaterial([added], [{ ID: 'F01-01', Keyword: '都市' }], new Map([['F01', fullText]]));
  assert.equal(report.status, 'failed');
  assert.deepEqual(report.missingNoteIds, ['F01-02']);
  assert.deepEqual(report.changedFrontIds, ['F01-01']);
});
test('artifact parity detects stale prose and answers even if note counts match', () => {
  for (const text of [fullText.replace('本文の説明です。', '古い本文'), fullText.replace('根拠です。', '古い解説')]) {
    const report = compareMaterial([lesson], [{ ID: 'F01-01', Keyword: '国' }], new Map([['F01', text]]));
    assert.equal(report.missingNoteIds.length, 0);
    assert.deepEqual(report.lessonsOutOfDate, ['F01']);
  }
});
test('artifact parity ignores ruby readings but not the underlying word', () => {
  const marked = fullText.replace('用語', '<ruby>用語<rp>（</rp><rt>ようご</rt><rp>）</rp></ruby>');
  assert.equal(compareMaterial([lesson], [{ ID: 'F01-01', Keyword: '国' }], new Map([['F01', marked]])).status, 'passed');
});
test('the expanded source still has every original unit and six questions each', () => {
  const lessons = readAuthoredLessons(path.resolve(import.meta.dirname, '../..'));
  assert.equal(lessons.length, 76);
  assert(lessons.every(lesson => lesson.questions.length === 6));
  assert.equal(lessons.reduce((n, lesson) => n + lesson.cards.length, 0), 2058);
});

test('published social materials must match the authored edition', () => {
  const report = inspectSocialMaterial(path.resolve(import.meta.dirname, '../..'));
  assert.equal(report.status, 'passed', `Generated social material is stale: ${report.missingNoteIds.length} missing notes, ${report.changedFrontIds.length} changed fronts, ${report.lessonsOutOfDate.length} outdated lessons. This is a release blocker, not a successful generation.`);
});
