# Design

## Existing boundaries

Add one `quality_tools` tuple to the existing immutable project profiles and
Node metadata. Reuse the strict root marker, XML, JSON, dependency, script, and
package-manager parsing already used by `agent init`.

## Java evidence

Parse Maven XML once and match exact plugin group/artifact pairs. Read the one
selected Gradle root build file once and match only standard Groovy/Kotlin plugin
declarations. Return tools in fixed platform order, independent of source order.

## TypeScript evidence

Reuse validated package scripts and dependency names. A dependency alone or a
similarly named command is insufficient; both dependency and exact invoked token
must exist.

## Persistence

The existing project metadata renderer writes `quality_tools` only when the
tuple is non-empty. Existing `.agent/project.yml` remains write-once and is not
silently changed during reinitialization.
