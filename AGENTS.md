# AGENTS.md — Agent guide for this repository

Purpose
- Brief guidance for AI coding agents working on this Django project.

Quick start (developer)
- Activate the provided virtualenv (PowerShell):

  & env_3_14_3\Scripts\Activate.ps1

- Run the dev server:

  python fullstack_prj/manage.py runserver

- Apply migrations:

  python fullstack_prj/manage.py migrate

- Run tests:

  python fullstack_prj/manage.py test

Key files
- Project entry: [fullstack_prj/manage.py](fullstack_prj/manage.py#L1)
- Django settings: [fullstack_prj/fullstack_prj/settings.py](fullstack_prj/fullstack_prj/settings.py#L1)
- Core app: [hello/apps.py](hello/apps.py#L1)
- Templates folder: [templates/index.html](templates/index.html#L1)
- Database (SQLite): db.sqlite3 (workspace root)

Agent instructions (concise)
- Use AGENTS.md rather than copying large docs; link to existing docs where possible.
- Follow "link, don't embed": reference files with links instead of duplicating content.
- Be minimal and actionable: include only commands and facts an agent cannot infer.
- When changing migrations or DB schema, run `migrate` and verify `db.sqlite3`.
- Prefer small, focused patches and mention test commands to run after changes.

Suggested next customizations
- Add a `.github/copilot-instructions.md` if you want organization-level rules.
- Create a `skills/` README if you want automated agent tasks (lint, format, tests).

If anything here is unclear, tell me what to expand or add (CI, formatting, tests).
