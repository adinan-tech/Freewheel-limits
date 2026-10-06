# Automation and repository guidelines

- Keep answers short and direct.
- Do not create, edit, rename, or delete files unless the user explicitly asks.
- At the start of each requested task, check the working tree, fetch `origin`, and compare local `main` with `origin/main` before editing.
- At the start of each task, read `PROJECT_PLAN.md` and work from its current phase.
- When a phase meets its completion criteria, mark it done in `PROJECT_PLAN.md` and record the evidence.
- If local changes or branch differences exist, inspect them before proceeding; do not overwrite or commit unrelated work.
- Do not commit or push after each task. Keep requested changes local until the daily sync checkpoint or an explicit request to sync sooner.
- At the daily 18:00 Europe/Bucharest checkpoint, review the diff, commit only requested changes, push to `origin/main`, and verify that local and remote `main` match. If no Codex session is active then, perform the checkpoint in the next active session. Report any failed sync.
- Confirm the intended scope and inspect the current state before changing an automation.
- Make operations idempotent so reruns do not duplicate work or corrupt state.
- Validate inputs and fail clearly when required values are missing or invalid.
- Use least privilege; keep credentials out of code, logs, and committed files.
- Set timeouts and use bounded retries with backoff for transient failures.
- Log useful actions and errors without exposing sensitive data.
- Provide a dry-run option for changes with significant effects when practical.
- Test the success path and meaningful failure cases; report what was verified.
- Document prerequisites, configuration, expected effects, and recovery steps.
