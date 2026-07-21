# Requirement

## Goal

Apply one model-generated, behavior-preserving refactor to the final production
source after an approved semantic review, then require the existing current-test
and full-suite gates before entering DONE.

## Acceptance criteria

- `agent refactor automated` uses the selected configured Provider.
- The model sees only a versioned Prompt, completion/review digests, the final
  production source, and the approved source-free semantic report.
- Output must replace that exact file; new files, test changes, empty/identical
  output, oversized output, and unsafe paths are rejected.
- Source/state writes use optimistic checks and atomic temporary files.
- The existing final verifier accepts only a digest-bound automated-refactor
  record and records before/after digests in DONE.
- Failed current or full-suite verification restores source and REFACTOR state.
- Legacy no-source-change `agent refactor` behavior remains compatible.

## Out of scope

- Multi-file refactors.
- API migration or behavior changes.
- Automatic refactoring without an approved semantic review.
