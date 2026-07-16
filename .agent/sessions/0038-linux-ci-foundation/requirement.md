# Requirement

## User request

Continue the roadmap with the next complete SDD/TDD task and keep development
moving without routine approval pauses.

## Requirements

- Add automatic Linux CI on an explicit GitHub-hosted Ubuntu release.
- Test the supported Python 3.9, 3.10, and 3.12 versions.
- Exercise the repository test suite through both Bash and Zsh.
- Run Ruff lint, Ruff format validation, Pyright, pytest with coverage, and a
  package build in CI.
- Pin every external GitHub Action to a verified immutable commit.
- Use least-privilege workflow permissions.
- Add a manual Linux Mint workflow targeting a real, explicitly labelled
  self-hosted runner.
- Verify the self-hosted host reports Linux Mint and runtime readiness before
  running its quality gates.
- Never imply that Ubuntu emulates or proves Linux Mint compatibility.
- Document Linux Mint as pending real-run validation until a matching runner
  completes the workflow.
- Preserve the active user Session and inspect `.gitignore` requirements.

## Out of scope

- Provisioning or registering a Linux Mint host for the repository owner.
- Claiming successful Linux Mint validation without a real workflow run.
- Installing JavaScript or Java toolchains solely for this increment.
- Adding unneeded YAML parsing or CI helper dependencies.
