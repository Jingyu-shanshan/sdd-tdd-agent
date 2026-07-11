# Architecture

## Context

The product is a CLI platform that coordinates a single code agent through
multiple isolated contexts. Python implements the platform; Java is the first
target project language supported by the MVP.

## Initial architecture

The platform starts as a single Python package with a thin CLI boundary. The
`project_init` module owns workspace filesystem changes independently of CLI
dispatch. The side-effect-free `project_detection` module maps root-level
project markers to a project profile. New workflow behavior will be introduced
behind application-layer interfaces only when a failing acceptance test
requires it.

## Decisions

- Use the Python standard library for the bootstrap increment.
- Expose the executable as `agent` and the module as `sdd_tdd_agent`.
- Keep CLI parsing separate from command behavior so output can be unit tested.
- Create bootstrap metadata with exclusive first-write semantics so repeated
  initialization preserves project knowledge.
- Keep project detection read-only and separate from metadata persistence.
- Do not add Typer, Pydantic, SQLite, LangGraph, or other dependencies before a
  concrete behavior needs them and a human approves the dependency.
