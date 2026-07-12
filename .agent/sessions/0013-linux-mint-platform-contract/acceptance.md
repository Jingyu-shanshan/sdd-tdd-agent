# Acceptance criteria

- [x] Linux Mint is identified only from valid `ID=linuxmint` data.
- [x] Other Linux distributions are compatible-untested, not Linux Mint.
- [x] macOS remains supported and unsupported systems are explicit.
- [x] Python >=3.9 and temporary-directory health are independently reported.
- [x] Malformed, duplicate, or unsafe os-release values fail safely.
- [x] `platform doctor` is deterministic and read-only.
- [x] Production probes clean up all temporary artifacts.
- [x] No new dependency or hidden environment mutation is introduced.
- [x] `.gitignore` needs no new generated-artifact pattern.
