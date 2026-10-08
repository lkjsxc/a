/** Read-only parity audit: never generates content, modifies files, or publishes. */
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { parse } from 'csv-parse/sync';
import { stripRuby } from './ruby.ts';

export interface AuthoredLesson {
  id: string;
  title: string;
  paragraphs: string[];
  cards: { id: string; front: string }[];
  questions: { id: string; prompt: string; answer: string; explanation: string }[];
}
export interface ParityReport {
  status: 'passed' | 'failed';
  sourceLessons: number;
  sourceLessonNotes: number;
  sourceQuestions: number;
  artifactLessonNotes: number;
  missingNoteIds: string[];
  unexpectedNoteIds: string[];
  changedFrontIds: string[];
  lessonsOutOfDate: string[];
}

/** Parse the actual edition without depending on the unfinished Python builder. */
export function readAuthoredLessons(root: string): AuthoredLesson[] {
  const source = path.join(root, 'social-studies/source');
  const lessons = new Map<string, AuthoredLesson>();
  const extended = new Set<string>();
  function read(directory: string, extension: boolean): void {
    for (const name of readdirSync(directory).filter(n => n.endsWith('.txt')).sort()) {
      let current: AuthoredLesson | undefined;
      let section = '';
      const lines = readFileSync(path.join(directory, name), 'utf8').split(/\r?\n/);
      for (const [index, line] of lines.entries()) {
        const error = () => new Error(`Invalid source structure at ${name}:${index + 1}`);
        const prefix = extension ? '@extend ' : '@lesson ';
        if (line.startsWith(prefix)) {
          if (current) throw error();
          const fields = line.slice(prefix.length).split('|');
          if (fields.length !== (extension ? 1 : 6)) throw error();
          const id = fields[0];
          if (extension) {
            if (!lessons.has(id) || extended.has(id)) throw error();
            current = lessons.get(id)!; extended.add(id);
          } else {
            if (lessons.has(id)) throw error();
            current = { id, title: fields[1], paragraphs: [], cards: [], questions: [] };
            lessons.set(id, current);
          }
          section = '';
        } else if (['@text', '@cards', '@questions'].includes(line)) {
          if (!current) throw error();
          section = line.slice(1);
        } else if (line === '@end') {
          if (!current) throw error();
          current = undefined; section = '';
        } else if (line.startsWith('@')) {
          throw error();
        } else if (line.trim()) {
          if (!current) throw error();
          if (section === 'text') current.paragraphs.push(line);
          else {
            const fields = line.split('|');
            if (section === 'cards' && fields.length === 7 && fields.every(Boolean)) {
              current.cards.push({ id: `${current.id}-${fields[0]}`, front: fields[2] });
            } else if (section === 'questions' && fields.length === 6 && fields.every(Boolean)) {
              current.questions.push({ id: `${current.id}-Q${fields[0]}`, prompt: fields[3], answer: fields[4], explanation: fields[5] });
            } else throw error();
          }
        }
      }
      if (current) throw new Error(`Unclosed lesson in ${name}`);
    }
  }
  read(source, false);
  read(path.join(source, 'expansion'), true);
  return [...lessons.values()];
}

export function compareMaterial(
  lessons: AuthoredLesson[],
  noteRows: { ID: string; Keyword: string }[],
  documents: Map<string, string>,
): ParityReport {
  const expected = new Map(lessons.flatMap(lesson => lesson.cards.map(card => [card.id, card.front] as const)));
  const actualRows = noteRows.filter(row => /^[FGHC]\d{2}-/.test(row.ID));
  const actual = new Map(actualRows.map(row => [row.ID, row.Keyword]));
  if (expected.size !== lessons.reduce((n, lesson) => n + lesson.cards.length, 0)) throw new Error('Duplicate source note ID');
  if (actual.size !== actualRows.length) throw new Error('Duplicate generated note ID');
  const missingNoteIds = [...expected.keys()].filter(id => !actual.has(id));
  const unexpectedNoteIds = [...actual.keys()].filter(id => !expected.has(id));
  const changedFrontIds = [...expected.keys()].filter(id => actual.has(id) && actual.get(id) !== expected.get(id));
  const lessonsOutOfDate = lessons.filter(lesson => {
    const document = documents.get(lesson.id);
    if (document === undefined) return true;
    // Markdown renderer escapes answer HTML; normalize the common entities too.
    const text = stripRuby(document).replace(/&quot;/g, '"').replace(/&#x27;|&#39;/g, "'")
      .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
    return !text.includes(lesson.title)
      || lesson.paragraphs.some(paragraph => !text.includes(paragraph))
      || lesson.questions.some(q => !text.includes(q.prompt) || !text.includes(q.answer) || !text.includes(q.explanation));
  }).map(lesson => lesson.id);
  const mismatch = missingNoteIds.length + unexpectedNoteIds.length + changedFrontIds.length + lessonsOutOfDate.length;
  return { status: mismatch ? 'failed' : 'passed', sourceLessons: lessons.length,
    sourceLessonNotes: expected.size, sourceQuestions: lessons.reduce((n, lesson) => n + lesson.questions.length, 0),
    artifactLessonNotes: actual.size, missingNoteIds, unexpectedNoteIds, changedFrontIds, lessonsOutOfDate };
}

export function inspectSocialMaterial(root: string): ParityReport {
  const lessons = readAuthoredLessons(root);
  const notes = parse(readFileSync(path.join(root, 'social-studies/anki/notes-audit.csv'), 'utf8'), {
    columns: true, bom: true, skip_empty_lines: true,
  }) as { ID: string; Keyword: string }[];
  const documents = new Map(lessons.map(lesson => [lesson.id,
    readFileSync(path.join(root, `social-studies/textbook/${lesson.id}.md`), 'utf8')]));
  return compareMaterial(lessons, notes, documents);
}
