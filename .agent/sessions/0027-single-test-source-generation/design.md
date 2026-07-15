# Design

`test_source_generation.py` owns the provider-independent contract:

- `TestSourceGenerationRequest` contains the versioned Prompt, approved
  requirement/design, exactly one `TestCasePlan`, and explicit `SourceSnapshot`
  values.
- `GeneratedTestSource` contains only `test_id`, `file_path`, and complete file
  `content`.
- `load_test_source_generation_request` validates the active cycle and builds
  the isolated Test Context without mutation.
- `validate_generated_test_source` binds model output to the current test and
  planned safe path.

`test_source_adapter.py` owns the two provider exchanges. Both serialize the
same nested request and decode the same exact three-field response. The Codex
adapter uses an ephemeral read-only run and an operating-system temporary
directory, so it cannot directly edit the project.

The test author may see requirement/design because it defines tests; this is
separate from `BlindDevelopmentContext`, which will later expose only the
current failing test and execution evidence to the production-code developer.
