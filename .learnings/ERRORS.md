# Errors

Command failures and integration errors.

**Categories**: command_failure | integration_error | timeout | permission

---

## [ERR-20260509-001]
- **Priority**: high
- **Status**: resolved
- **Area**: tool
- **Summary**: Subagent timed out after 16 tool calls during wiki ingest operation
- **Details**: A subagent spawned for wiki content ingestion hit the 16-tool-call timeout limit mid-task, leaving the ingestion incomplete. The task had to be retried.
- **Suggested Fix**: Increase tool-call budget for subagents performing batch ingest, or split large ingest jobs into smaller chunks before spawning.
- **Metadata**: 2026-05-09T16:00:00-05:00, subagent:wiki-ingest

---

## [ERR-20260509-002]
- **Priority**: critical
- **Status**: resolved
- **Area**: tool
- **Summary**: `gh repo sync --force` overwrote local wiki infrastructure work
- **Details**: Running `gh repo sync --force` on the workspace repo force-pushed remote state, wiping newly created wiki infrastructure files (`.learnings/`, wiki setup). Local work was recovered via `git reflog`.
- **Suggested Fix**: Never use `--force` on sync without checking `git status` first. Add a workspace safeguard alias that checks for uncommitted changes before destructive syncs.
- **Metadata**: 2026-05-09T17:00:00-05:00, command:gh_repo_sync

---

## [ERR-20260509-003]
- **Priority**: medium
- **Status**: resolved
- **Area**: config
- **Summary**: Graphify semantic extraction failed due to missing `openai` package
- **Details**: Graphify's Ollama-compatible extraction path requires the `openai` Python package to be installed, even when using Ollama instead of OpenAI. The dependency was not documented in the install path.
- **Suggested Fix**: Ensure `openai` is in the workspace venv requirements, or document it explicitly for Ollama users.
- **Metadata**: 2026-05-09T17:30:00-05:00, tool:graphify

---

## [ERR-20260509-004]
- **Priority**: medium
- **Status**: resolved
- **Area**: infra
- **Summary**: Search index UNIQUE constraint violation required full rebuild
- **Details**: sqlite-vec search index threw a UNIQUE constraint failure during an update. The only recovery path was deleting the index file and rebuilding from scratch.
- **Suggested Fix**: Add upsert logic to the indexing script, or catch the constraint error and regenerate only the affected document embeddings instead of a full rebuild.
- **Metadata**: 2026-05-09T18:00:00-05:00, tool:sqlite-vec

---

## [ERR-20260509-005]
- **Priority**: medium
- **Status**: pending
- **Area**: infra
- **Summary**: Ollama semantic extraction is very slow with qwen3.6:35b
- **Details**: Graphify's semantic extraction step using Ollama backend (model: qwen3.6:35b) takes several minutes per extraction, making iterative graph updates impractical.
- **Suggested Fix**: Switch to a smaller/faster model for extraction (e.g., qwen2.5 or a dedicated embedding model), or run extraction asynchronously and cache results aggressively.
- **Metadata**: 2026-05-09T18:15:00-05:00, tool:graphify, model:qwen3.6:35b

---

## [ERR-20260509-006]
- **Priority**: low
- **Status**: pending
- **Area**: auth
- **Summary**: GOG keyring timed out waiting for D-Bus SecretService
- **Details**: gog CLI authentication attempt stalled waiting for the D-Bus SecretService to store/retrieve credentials. The service was unresponsive.
- **Suggested Fix**: Fallback to file-based token storage when keyring is unavailable, or pre-warm the SecretService before auth operations.
- **Metadata**: 2026-05-09T19:00:00-05:00, tool:gog, service:dbus

---

## [ERR-20260509-007]
- **Priority**: medium
- **Status**: resolved
- **Area**: auth
- **Summary**: GOG Drive API was not enabled in Google Cloud Console
- **Details**: Attempting to use GOG's Google Drive integration failed with an API-not-enabled error. Required manual enablement in the Google Cloud Console.
- **Suggested Fix**: Document the prerequisite steps (enable Drive API, configure OAuth consent screen) in the setup guide before attempting auth.
- **Metadata**: 2026-05-09T19:15:00-05:00, tool:gog, provider:google

---

## [ERR-20260509-008]
- **Priority**: medium
- **Status**: pending
- **Area**: auth
- **Summary**: Browser OAuth flow required manual user intervention
- **Details**: The authentication flow opened a browser window but required the user to manually click and approve the OAuth consent link. This breaks fully automated headless setups.
- **Suggested Fix**: Implement headless OAuth flow using device-code or service-account authentication for non-interactive environments.
- **Metadata**: 2026-05-09T19:30:00-05:00, tool:browser, flow:oauth

---

## [ERR-20260509-009]
- **Priority**: low
- **Status**: resolved
- **Area**: tool
- **Summary**: Chromium was denied permission to open a PDF file
- **Details**: Chromium browser process failed with a permission-denied error when attempting to open a PDF. Switching to `google-chrome` as the binary fallback resolved the issue.
- **Suggested Fix**: Detect the correct browser binary at runtime or add a configurable browser path override to handle permission/ sandbox differences between Chromium and Chrome.
- **Metadata**: 2026-05-09T20:00:00-05:00, tool:browser, binary:chromium
