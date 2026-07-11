# AGENTS.md

## Purpose

This document defines the mandatory development rules for AI coding agents and human developers working on this repository.

The goals are:

* Maintain production-grade code quality.
* Prevent unsafe modifications.
* Ensure testability and maintainability.
* Minimize hallucinated implementations.
* Ensure all changes are validated by tests.

---

# Core Principles

1. Correctness over speed.
2. Readability over cleverness.
3. Explicit over implicit.
4. Small changes over large rewrites.
5. Tests are part of the implementation.
6. Existing architecture must be respected.

---

# Forbidden Behaviors

## Never modify tests to make code pass

The AI agent MUST NOT:

* Modify existing tests.
* Remove tests.
* Weaken assertions.
* Skip tests.
* Change coverage thresholds.

If a test is incorrect:

1. Stop.
2. Explain why the test appears incorrect.
3. Ask for human review.

---

## Never bypass failing tests

Forbidden:

```python
try:
    ...
except:
    pass
```

```python
return True
```

```python
return None
```

just to satisfy tests.

---

## Never delete production code without justification

Large deletions require:

* explanation,
* impact analysis,
* approval.

---

## Never introduce hidden behavior

Forbidden:

* monkey patching
* runtime mutation of global state
* modifying environment variables silently
* patching imported modules

---

# Scope of Changes

The agent should only modify files that are necessary.

Avoid:

* repository-wide refactoring
* renaming unrelated files
* formatting the entire project

Prefer:

* minimal diffs
* localized changes

---

# Development Workflow

## Step 1

Understand:

* requirements
* existing architecture
* existing tests

## Step 2

Identify:

* affected modules
* dependencies
* edge cases

## Step 3

Implement.

## Step 4

Add tests.

## Step 5

Run:

```bash
ruff check .
ruff format .
pyright
pytest
```

---

# Python Style Guide

## Python Version

Target:

```text
Python >= 3.9
```

---

## Formatting

Use:

```bash
ruff format
```

Maximum line length:

```text
88 characters
```

Indentation:

```text
4 spaces
```

---

# Naming Conventions

## Variables

```python
user_name
order_count
is_deleted
```

## Functions

```python
create_user()
load_configuration()
```

## Classes

```python
UserService
OrderRepository
```

## Constants

```python
MAX_RETRY_COUNT
DEFAULT_TIMEOUT
```

---

# Type Hints

Every public function MUST have type hints.

Good:

```python
def get_user(user_id: int) -> User:
    ...
```

Good:

```python
def find_user(user_id: int) -> User | None:
    ...
```

Bad:

```python
def get_user(user_id):
    ...
```

---

# Function Rules

## Single responsibility

One function should do one thing.

---

## Maximum size

Preferred:

```text
<= 50 lines
```

---

## Parameters

Preferred:

```text
<= 5 parameters
```

If more:

Use:

```python
@dataclass
class Request:
    ...
```

---

## Nesting

Avoid nesting deeper than:

```text
3 levels
```

Prefer early return.

---

# Class Rules

## Single responsibility

A class should have one reason to change.

---

## Maximum size

Preferred:

```text
<= 300 lines
```

---

# Error Handling

Never:

```python
except:
    pass
```

Always:

```python
except ValueError as e:
    raise DomainError() from e
```

---

# Logging

Never:

```python
print()
```

Use:

```python
logger.info()
logger.warning()
logger.error()
```

Never log:

* passwords
* tokens
* secrets
* personal data

---

# Configuration

Never hardcode:

* API keys
* database URLs
* credentials

Use:

```python
pydantic-settings
```

or environment variables.

---

# Dependency Injection

Prefer:

```python
class UserService:
    def __init__(
        self,
        repository: UserRepository,
    ):
        ...
```

Avoid:

```python
global repository
```

---

# Project Structure

Preferred:

```text
src/
    user/
        api.py
        service.py
        repository.py
        schema.py

    order/
        api.py
        service.py
        repository.py
        schema.py
```

---

# Testing Rules

## Framework

```text
pytest
```

---

## Naming

```python
def test_should_create_user():
```

---

## Pattern

```text
Arrange
Act
Assert
```

---

## Coverage

Minimum:

```text
80%
```

Critical modules:

```text
90%
```

---

# AI Agent Rules

## Never assume requirements

If requirements are ambiguous:

STOP.

Ask for clarification.

---

## Never hallucinate APIs

Before using:

* functions
* classes
* methods

Verify they exist.

---

## Never invent configuration values

Verify from:

* code
* documentation
* environment

---

## Never introduce new dependencies unnecessarily

Before adding a package:

1. Search existing dependencies.
2. Explain why it is required.

---

# Refactoring Rules

Allowed:

* extract methods
* simplify conditions
* remove duplication

Not allowed:

* architecture rewrites
* framework migration
* changing public APIs

unless explicitly requested.

---

# LLM / Agent System Rules

All LLM interactions MUST:

* be mockable;
* be testable;
* have typed input/output;
* support dependency injection.

---

## Prompt Management

Prompts must:

* have versions;
* be stored in files;
* not be embedded in business logic.

---

## Tool Calling

Tool interfaces must:

* be typed;
* be unit tested;
* support mocking.

---

# Security Rules

Never:

* commit secrets;
* disable authentication;
* disable authorization;
* ignore validation.

Always:

* validate inputs;
* sanitize outputs;
* fail safely.

---

# Pull Request Checklist

Before completion, verify:

* [ ] Tests pass
* [ ] Ruff passes
* [ ] Pyright passes
* [ ] New functionality is tested
* [ ] No unrelated files changed
* [ ] No secrets introduced
* [ ] Public APIs unchanged
* [ ] Documentation updated if necessary

---

# Final Rule

The AI agent should behave like a cautious senior engineer:

* make the smallest safe change;
* preserve existing behavior;
* prefer correctness over speed;
* never cheat to satisfy tests.
