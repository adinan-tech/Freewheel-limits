# Automation guidelines

- Keep answers short and direct.
- Do not create, edit, rename, or delete files unless the user explicitly asks.
- Confirm the intended scope and inspect the current state before changing an automation.
- Make operations idempotent so reruns do not duplicate work or corrupt state.
- Validate inputs and fail clearly when required values are missing or invalid.
- Use least privilege; keep credentials out of code, logs, and committed files.
- Set timeouts and use bounded retries with backoff for transient failures.
- Log useful actions and errors without exposing sensitive data.
- Provide a dry-run option for changes with significant effects when practical.
- Test the success path and meaningful failure cases; report what was verified.
- Document prerequisites, configuration, expected effects, and recovery steps.
