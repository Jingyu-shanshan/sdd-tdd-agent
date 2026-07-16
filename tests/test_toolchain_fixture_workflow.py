import re
from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "toolchain-fixtures.yml"
)


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_should_define_secure_real_toolchain_matrices() -> None:
    workflow = _workflow()
    actions = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.MULTILINE)

    assert "push:" in workflow
    assert "pull_request:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "pull_request_target:" not in workflow
    assert "permissions:\n  contents: read" in workflow
    assert workflow.count("runs-on: ubuntu-24.04") == 2
    assert 'build-tool: ["maven", "gradle"]' in workflow
    assert "package-manager: npm" in workflow
    assert "package-manager: pnpm" in workflow
    assert "package-manager: yarn" in workflow
    assert actions
    assert all(re.search(r"@[0-9a-f]{40}$", action) for action in actions)


def test_should_pin_java_and_execute_both_java_fixtures() -> None:
    workflow = _workflow()

    assert "actions/setup-java@0f481fcb613427c0f801b606911222b5b6f3083a" in workflow
    assert (
        "gradle/actions/setup-gradle@3f131e8634966bd73d06cc69884922b02e6faf92"
        in workflow
    )
    assert "distribution: temurin" in workflow
    assert 'java-version: "21"' in workflow
    assert 'gradle-version: "9.6.1"' in workflow
    assert "working-directory: tests/fixtures/toolchains/maven" in workflow
    assert "working-directory: tests/fixtures/toolchains/gradle" in workflow
    assert "run: mvn test" in workflow
    assert "run: gradle test" in workflow


def test_should_pin_node_managers_and_execute_locked_fixtures() -> None:
    workflow = _workflow()

    assert "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020" in workflow
    assert 'node-version: "22"' in workflow
    assert "package-manager-version: 11.0.0" in workflow
    assert "package-manager-version: 10.2.0" in workflow
    assert "package-manager-version: 4.6.0" in workflow
    assert "run: npm ci" in workflow
    assert "run: pnpm install --frozen-lockfile" in workflow
    assert "run: yarn install --immutable" in workflow
    assert "run: npm test -- --run" in workflow
    assert "run: pnpm test -- --run" in workflow
    assert "run: yarn run test --run" in workflow
