import hashlib
import json
from pathlib import Path

from tests.production_source_support import GENERATED_CONTENT, create_red_workspace


def create_implement_workspace(root: Path) -> Path:
    session = create_red_workspace(root)
    target = root / "src" / "export.ts"
    target.write_text(GENERATED_CONTENT, encoding="utf-8")
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["tdd_cycle"]["phase"] = "IMPLEMENT"
    state["production_source"] = {
        "test_id": "TC1",
        "file_path": "src/export.ts",
        "sha256": hashlib.sha256(GENERATED_CONTENT.encode()).hexdigest(),
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return session
