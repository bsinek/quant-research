# quant-research

Monorepo of independent quantitative research projects. Each top-level directory (e.g. `vol-surface/`) is a self-contained project with its own `CLAUDE.md`, `docs/`, and conventions — work in it as if it lived in its own isolated repo. When inside a project, that project's `CLAUDE.md` governs; this root file only states the monorepo convention.

`README.md` is the index into the projects.

## Commits
- Conventional commits with the project dir as scope: `type(vol-surface): summary`. Repo-wide changes drop the scope (`chore: ...`).
- Types: feat / fix / refactor / docs / test / perf / chore.
- Subject: lowercase, imperative, no trailing period, ~50 chars.
- Body: concise why-focused bullets, only when detail is warranted.
