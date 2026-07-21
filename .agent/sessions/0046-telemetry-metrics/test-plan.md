# Test Plan

- Model success records Prompt identity but no payload, output, or arguments.
- Model/test failures record bounded metadata and re-raise original errors.
- Deterministic clocks prove duration; usage remains explicitly unavailable.
- Multiple events aggregate counts, success rates, and total duration.
- Malformed/oversized/tampered files fail safely.
- Workflow CLI writes telemetry; `agent metrics` renders it deterministically.
- Existing runner call/output behavior remains unchanged under full regression.
