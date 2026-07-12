# Implementation log

## Official documentation verification

The Codex manual helper rejected the remote response because its expected
integrity header was absent, and the installed Docs MCP was not loaded in this
task. Official-domain fallback verified the current Codex CLI page and its
macOS/Linux standalone installer URL. No installer was downloaded or run.

## `.gitignore` baseline

Installer files will use an operating-system private temporary directory and be
removed automatically. Repository config continues to use the existing nested
`.agent/**/*.tmp` rule, so no new ignore pattern is expected.

## Cycle 1: Provider Doctor

### RED

The diagnostic tests failed during collection because `provider_tools` did not
exist. The CLI test then failed because no injected Provider dependency
container existed.

### GREEN

Typed locator, diagnostic, Doctor, renderer, and CLI dependencies now
distinguish installed, missing, unhealthy, manual-config, and planned states.
Doctor uses the existing explicit timeout and never mutates selection or Session
state. The real command reports the installed Codex CLI version.

## Cycle 2: Guarded Codex installer

### RED

The installer contract test failed during collection because no guarded
Provider installer existed.

### GREEN

The Registry owns the verified Codex standalone URL and tokenized plan. The
Installer uses a private OS temporary directory, separate `curl` and `sh`
processes, the injected timeout, post-install location, and version verification.
Eight failure tests cover unavailable adapters, download/execute errors, missing
script/executable, and invalid/failed version output without leaking content.

## Cycle 3: Interactive missing-CLI selection

### RED

Six interactive tests showed `provider use` still selected immediately instead
of prompting, cancelling, installing, or rolling back. The non-interactive
compatibility test was already GREEN.

### GREEN

The service validates before side effects, skips install in non-interactive
mode, prompts only on a TTY, accepts only `y`/`yes`, verifies before atomic
selection, and preserves config/Session state on cancellation or failure.

## Cycle 4: Output and platform safety

A RED test proved ANSI control sequences from a version could be rendered.
Shared validation now accepts only one non-empty printable line up to 200 chars.

Review also found the macOS/Linux installer could otherwise run on Windows. A
failing test added an explicit platform dependency. Missing-CLI installation now
maps `darwin` to `macos`, `linux` to `linux-mint`, and rejects other platforms
before prompt/download; the Installer revalidates this boundary.

## Current verification

- Ruff lint passes; Pyright reports zero errors and warnings.
- All 109 tests pass with 94.97% total coverage.
- Provider Registry coverage is 98%; Provider tools coverage is 95%.
- Source/wheel builds and Python 3.9 compilation pass.
- Real Doctor reports Codex CLI 0.144.0-alpha.4 installed.
- `.gitignore` needs no new pattern.
- The active product Session remains at `REQUIREMENT_REVIEW`.

Final `ruff format --check` awaits human review because four new test files need
mechanical formatting and repository rules prohibit modifying existing tests.
