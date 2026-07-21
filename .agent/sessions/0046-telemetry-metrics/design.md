# Design

## Minimal boundary

Use one telemetry module with two decorators around the existing `ProcessRunner`
and `TestCommandRunner`. CLI composition labels operations; workflow modules and
Provider adapters remain unchanged.

## Storage

Append one bounded canonical JSON object per line to
`.agent/metrics/<session-id>.jsonl` using one `O_APPEND` write. Store only
allowlisted metadata. Metrics files are already ignored as runtime data.

## Usage honesty

Current strict Provider protocols expose no verified token or billing fields.
Events therefore store null token/cost values plus `usage_status: unavailable`.
The aggregator reports usage only when every event carries validated values.

## Failure behavior

Delegate exceptions are recorded and re-raised. Invalid operations, malformed
events, unsafe Session IDs, oversized files, and write failures raise a safe
telemetry error; nothing is silently discarded.
