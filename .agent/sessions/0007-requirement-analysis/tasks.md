# Tasks

## Task 1: Typed analysis request and Prompt

Status: complete

1. [x] Add one pytest test for exact raw request, project context, Prompt version,
   and Prompt content.
2. [x] Implement immutable types, analyzer Protocol, Prompt loading, and request
   loading.
3. [x] Make the suite GREEN.

## Task 2: Structured requirement rendering

Status: complete

1. [x] Add one failing test for deterministic Markdown sections and values.
2. [x] Implement rendering without filesystem or model coupling.
3. [x] Make the suite GREEN.

## Task 3: Analysis workflow and state transition

Status: complete

1. [x] Add one failing test with a fake injected analyzer.
2. [x] Validate output, atomically update files, and enter REQUIREMENT_REVIEW.
3. [x] Prove invalid output/state causes no mutation.

## Task 4: Packaging and ignore policy

Status: complete

- [x] Verify the versioned Prompt exists in the built wheel.
- [x] Verify Prompt and Session files are tracked while temp/cache/log files remain
  ignored.
