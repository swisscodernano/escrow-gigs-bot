---
name: "Codex Task"
about: "Structured spec for Codex to implement"
title: "[<type>] <short imperative task title>"
labels: ["codex"]
---

## Context
<!-- Short description of current state and why we need this change -->

## Goal / Desired Behavior
<!-- What should happen when this is done? -->
- [ ] ...

## Acceptance Criteria
<!-- Tick-able list Codex can verify before PR -->
- [ ] All user-facing strings in English
- [ ] No changes to public APIs unless stated
- [ ] Tests updated/added for new logic
- [ ] `./codex-setup.sh` passes locally

## Constraints
<!-- E.g., don't touch certain files, keep backward compatibility -->
- ...

## Implementation Notes (optional)
<!-- Any pointers, file paths, or relevant commands -->
- Likely changes in: `app/telegram_bot.py`, `app/_autostart.py`
- Run locally with:
  ```bash
  uvicorn app.app:app --reload
