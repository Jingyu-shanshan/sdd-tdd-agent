# Design

## Official Codex plan

The current official Codex CLI page documents the macOS/Linux standalone
installer at `https://chatgpt.com/codex/install.sh`. The published pipe is split
into two explicit operations so the platform never invokes a command shell:

```text
curl -fsSL --output <private-temp>/install.sh <official-url>
sh <private-temp>/install.sh
```

The default/current stable version is chosen by the official installer. The
platform neither constructs an unverified version URL nor modifies PATH.

## Typed boundaries

- `ProviderExecutableLocator`: returns an executable path or `None`.
- `ProviderDoctor`: checks Registry state, location, and `--version` health.
- `ProviderInstaller`: executes a Registry-owned install plan through the
  injected `ProcessRunner` and verifies the installed executable.
- `ProviderCommandDependencies`: supplies input, runner, and locator to CLI
  composition without global mutation or monkey-patching.

## Selection flow

1. Validate Registry key, Adapter status, and command/install metadata.
2. If the executable exists, select normally.
3. If stdin is non-interactive, preserve existing explicit selection behavior
   and never install; `provider doctor` remains available for automation.
4. If interactive and missing, render the confirmation prompt.
5. Anything except `y` or `yes` cancels without configuration mutation.
6. On confirmation, download, execute, re-locate, and verify `--version`.
7. Atomically select the Provider only after all checks pass.

## Failure behavior

Unknown/planned Providers, missing install plans, download/installer failures,
missing post-install executables, and version failures return safe typed errors.
No process content, URL response body, Prompt, credentials, or environment data
is exposed.
