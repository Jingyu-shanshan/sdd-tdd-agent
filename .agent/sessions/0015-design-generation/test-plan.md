# Test plan

## Request and rendering

- Load approved requirement, Prompt version/content, metadata, architecture, and
  conventions.
- Render every structured section in fixed order.
- Render empty optional tuples explicitly.

## Workflow

- Inject a fake generator and verify the exact typed request it receives.
- Write the validated proposal and enter `DESIGN_REVIEW`.
- Preserve existing Session keys and the human approval record.

## Failure safety

- Reject a wrong state before calling the generator.
- Reject missing approval and mismatched Session identity.
- Reject non-object state and invalid generator return type.
- Reject empty required fields and blank tuple members.
- Assert existing `design.md` and `state.json` stay byte-for-byte unchanged.

## Quality

- Run full pytest with configured coverage, Ruff format/check, and Pyright.
- Build source and wheel artifacts and compile the Python package.
- Validate all Session JSON with duplicate-key detection.
- Confirm `.gitignore` coverage and preserve the active PDF Session.
