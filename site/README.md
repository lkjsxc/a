# a. まなびの図書室

Public website: **https://lkjsxc.github.io/a/**

## Architecture

The website is a progressively enhanced static site, not a hosted Node server. Existing Markdown is the reading source; original Anki packages and other downloads are copied byte-for-byte. The separate website build does not regenerate the existing Python-generated social-studies packages or change Anki note identities.

- Node 24 and TypeScript build the site into `_site/`.
- Markdown is sanitized before publication. Japanese ruby, disclosure answers, figures, and tables remain available.
- Relative Markdown links are rewritten to the GitHub Pages `/a/` project subpath. Unicode filenames, anchor links, and source links are preserved.
- PNG/JPEG pictures get optimized WebP copies for reading; originals are retained.
- Browser code is bundled once, minified, content-hashed, and loaded without a framework. No external fonts, advertising, analytics, or account backend.
- Search and deck JSON are fetched on demand. Reading and ordinary links work without JavaScript.
- Learning records are local to this project (`lkjsxc:a:learning:v1`), exportable/importable, and never sent to a server. Browser practice is self-assessment, not spaced-repetition scheduling.

## Develop and verify

```sh
npm ci
npm run verify
npx playwright install --with-deps chromium webkit
npm run test:browser
npm run preview
```

Preview: `http://127.0.0.1:4173/a/`. Node is only needed for authoring, verification and builds.

`npm run verify` checks types, unit tests, then builds and checks every generated internal link, fragment, image path, download identity, data count, HTML structure and basic size budgets. Browser tests exercise native navigation, blocked storage, search failures, responsive reading, import/export, practice, and automated WCAG checks on Chromium and mobile WebKit. Automated tests are not a guarantee of accessibility for every user or performance on physical devices.

To validate an already published deployment, build locally first, then run browser tests using `BASE_URL=https://lkjsxc.github.io/a/ npm run test:browser`. This may write test-only learning records in Playwright's isolated browser profiles, not a person's real browser.

## Edit content

Edit the existing Markdown for readings. Social-studies generated materials still have their existing `social-studies/source/` and `tools/` source-of-truth; follow that package's own instructions when changing its curriculum or Anki content. Preserve its stable card identifiers. The website automatically rebuilds from the committed outputs.

Website layout and behavior live in `site/`. CSS is in `style.css`, page templates in `templates.ts`, sanitization/link handling in `render.ts`, storage contract in `state.ts`. Do not edit `_site/` manually or commit it.

## Publication

Repository Settings → Pages uses **GitHub Actions**. `.github/workflows/pages.yml` runs verification for pull requests and for every push to `main`. Only a verified main-branch artifact can reach the `github-pages` environment; pull requests have no Pages-write or ID-token permission. Actions are pinned to commit hashes and npm uses a checked-in lockfile.

The only uploaded directory is `_site/`, built from an explicit content-extension allowlist. Repository internals, `.git`, dependencies, content-generation tools, and hidden files are never uploaded. No personal access token, deployment secret, or external hosting account is needed by the workflow.

`SITE_URL` can change the build's absolute canonical URL and project prefix (default `https://lkjsxc.github.io/a/`), but a new domain also requires the matching GitHub Pages/domain configuration. Preview supports the same variable. Browser acceptance tests intentionally test the actual `/a/` deployment.

To roll back, revert the unwanted source commit on `main`, then let the same checks and deploy workflow run. Avoid force-pushing history. A deployment is complete only when the workflow's deploy job succeeds and the live `build.json` revision matches the intended main commit.

## Offline and privacy boundaries

The entire website is not an offline application and has no service worker. Use the existing social-studies ZIP or Anki data offline. The ZIP's original interface does not include this website's search and local reading records. Learning records do not synchronize automatically; settings can export/import them. GitHub Pages still processes normal hosting requests according to GitHub's privacy policy.

Do not claim that a website/UI change re-validated every educational assertion in the source corpus. The original citations, source quality notes, and accuracy limitations remain part of the materials.
