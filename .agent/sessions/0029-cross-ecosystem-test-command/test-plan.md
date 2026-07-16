# Test Plan

- Prove Maven and Gradle commands select one standard fully qualified test
  method and choose executable wrapper, `sh` wrapper, or system launcher.
- Prove Java traversal, non-standard source roots, invalid names, and missing
  build markers fail without execution.
- Prove `packageManager` and lockfile detection for npm/pnpm/yarn, including
  consistent dual evidence, conflicts, multiple locks, and absent evidence.
- Prove strict package JSON rejects syntax errors, duplicate keys, invalid field
  types, missing/invalid test scripts, and unsupported managers/frameworks.
- Prove Jest commands use exact-path/name/serial filters for all three package
  managers.
- Prove Vitest commands disable watch and filter one file/name.
- Prove Angular commands use non-watch include/name filters and require Angular
  workspace/dependency/script evidence.
- Prove mixed Java/Node roots select by test extension and unsupported file
  extensions fail.
- Prove general project detection reports TypeScript/Angular metadata without
  changing existing Java behavior.
