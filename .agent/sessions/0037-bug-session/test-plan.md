# Test Plan

- Prove an explicit safe ID creates exactly eight artifacts and exact initial
  `kind=bug` state.
- Prove exact CLI output contains a safe generated ID and activates that Session.
- Prove replacement and append forms of `current_session` preserve all unrelated
  project metadata.
- Prove blank descriptions and unsafe explicit IDs create no Session.
- Prove an existing Session collision leaves project metadata and existing
  content byte-identical.
- Prove requirement analysis accepts the active bug Session, advances it to
  REQUIREMENT_REVIEW, and retains `kind=bug`.
- Re-run all existing feature Session tests to prove compatibility.
