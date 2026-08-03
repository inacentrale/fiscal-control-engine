---
name: todo-plan-tracker
description: Keep project todo files synchronized during planning and implementation. Use whenever Codex creates, completes, defers, splits, or reprioritizes work in todo.md, api/todo.md, front/todo.md, or another domain todo file.
---

# Todo Plan Tracker

## Workflow

1. Read the relevant todo files before changing a plan:
   - `todo.md` for global milestones.
   - `api/todo.md` for API/backend work.
   - `front/todo.md` when frontend work exists.
2. Identify the active section and exact checklist lines affected.
3. Update the todo in the same turn as the work or decision.
4. Keep root `todo.md` high level; move detailed work into the domain todo.
5. Record deferrals as unchecked items with a short reason.
6. Mark items done only when the work is actually complete.

## Update Rules

- Keep bullets concrete and actionable.
- Prefer short checklist lines over broad status prose.
- Keep paths relative and readable, such as `api/todo.md`.
- Do not create todo files under `docs/`.
- If a todo moves from root to a domain file, replace the root detail with a pointer to the domain todo.
- If a decision changes the stack or architecture, update affected todos and rules together.
- If validation commands run, record the result under the relevant domain todo.
- If work is blocked, leave it unchecked and add the blocker in the same bullet or a short note.

## Required Final Check

Before final response after todo-related work, verify:

- The changed todo file reflects completed, deferred, and next work accurately.
- Root and domain todos do not contradict each other.
- No todo was created in `docs/`.
- The next unchecked task is clear.
