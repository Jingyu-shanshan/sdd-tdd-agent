# Requirement

## User request

Continue the roadmap by adding the missing bug Session entry point.

## Requirements

- Add exact `agent bug <description>` CLI behavior.
- Create the same eight standard SDD artifacts as feature Sessions.
- Store `kind=bug`, initial `ANALYSIS` state, no current task, and cycle zero.
- Normalize descriptions, generate safe unique IDs, and support safe explicit
  IDs through the Python service.
- Reject blank descriptions, unsafe IDs, and existing Session collisions before
  activating or overwriting project metadata.
- Activate a successful bug Session without changing unrelated project fields.
- Preserve compatibility with the existing requirement-analysis workflow.
- Share creation mechanics with feature Sessions without changing their public
  behavior.
- Keep the real active user Session and unrelated files unchanged.

## Out of scope

- Bug-specific analysis prompts or state-machine branches.
- Issue-tracker integration, reproduction automation, or severity triage.
- Automatic provider execution during Session creation.
