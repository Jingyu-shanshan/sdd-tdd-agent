# Test Plan

- Prove implementation completion records exact ordered IDs and canonical
  GREEN/test/production digests before REVIEW.
- Prove exact valid REVIEW generates deterministic source/output-free Markdown,
  records both report/completion digests, and enters REFACTOR.
- Prove `agent review` output and absence of model/test/process calls.
- Prove missing/extra/wrong completion fields, reordered IDs, stale final test,
  evidence changes, and artifact-digest changes preserve REVIEW.
- Prove missing, user-edited, oversized, invalid UTF-8, or symlinked `review.md`
  fails safely.
- Prove state/report changes and either atomic temporary collision preserve
  REVIEW without partial replacement.
- Prove non-REVIEW Sessions and missing active Sessions are rejected.
