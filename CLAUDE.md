# Project: solar-gemini

## Auto-PR Workflow

Nach jedem erfolgreichen `git push` auf einen Feature-Branch:

1. Mit `mcp__github__list_pull_requests` (head: `<branch-name>`, state: `open`) prüfen, ob für den aktuellen Branch bereits ein offener PR existiert.
2. Wenn **nein**: automatisch per `mcp__github__create_pull_request` einen neuen PR gegen `main` anlegen. Titel und Body aus den letzten Commits ableiten. Keine Nachfrage.
3. Wenn **ja**: kurz bestätigen, dass der bestehende PR aktualisiert wurde, URL ausgeben.

Gilt nicht für direkte Pushes auf `main`.
