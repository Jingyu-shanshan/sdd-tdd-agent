# Implementation

## RED

Two new test modules failed collection because the provider-independent
generation module and its adapters did not exist. This established the intended
contract before production implementation.

The first GREEN run also exposed an invalid newly added `GREEN` fixture: the
existing cycle contract requires the current test in the completed prefix. The
fixture record was corrected without changing or weakening its assertion.

## GREEN

Added the isolated request/result models, versioned single-test Prompt, current
cycle loader, source and output validation, strict JSON command adapter, and
ephemeral read-only Codex adapter. No file writer, CLI, or test runner was
introduced.

## Verification

Targeted result: 36 tests passed. Full result: 343 tests passed with 94.61%
coverage; the new core has 98%, the adapter 100%, and `tdd_cycle.py` 91%.
Ruff, Pyright, compile, build, Session JSON, active-Session preservation, and
ignore-rule checks passed.
