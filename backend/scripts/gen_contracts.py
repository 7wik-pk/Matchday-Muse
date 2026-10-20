"""Generates app/contracts/ (Pydantic v2 models) from contracts/.

contracts/ws/ and contracts/pipeline/ are JSON Schema as written. Each file in
contracts/mcp/ is a tool descriptor, so its input and output schemas are first
written out as schemas of their own (FindMatchesInput, FindMatchesOutput...).

    uv run python scripts/gen_contracts.py           # write
    uv run python scripts/gen_contracts.py --check   # fail if stale
"""

import filecmp
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
CONTRACTS = BACKEND.parent / "contracts"
OUT = BACKEND / "app" / "contracts"
# Mock scripts and takes only feed the frontend's mock socket.
SKIP = {"mock-script.json", "mock-takes.json"}

HEADER = "# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.\n"


def camel(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def stage(tmp: Path) -> None:
    for sub in ("ws", "pipeline"):
        (tmp / sub).mkdir()
        for f in sorted((CONTRACTS / sub).glob("*.json")):
            if f.name not in SKIP:
                shutil.copy(f, tmp / sub / f.name)
    (tmp / "mcp").mkdir()
    for f in sorted((CONTRACTS / "mcp").glob("*.json")):
        tool = json.loads(f.read_text())
        for key, suffix in (("inputSchema", "Input"), ("outputSchema", "Output")):
            schema = {"title": camel(tool["name"]) + suffix, **tool[key]}
            (tmp / "mcp" / f"{tool['name']}_{suffix.lower()}.json").write_text(json.dumps(schema, indent=2))


def generate(dest: Path) -> None:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        stage(tmp)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(tmp),
                "--input-file-type",
                "jsonschema",
                "--output",
                str(dest),
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.14",
                "--use-title-as-name",
                "--use-standard-collections",
                "--use-union-operator",
                "--use-type-alias",
                "--enum-field-as-literal",
                "all",
                "--use-double-quotes",
                "--snake-case-field",
                "--allow-population-by-field-name",
                "--field-constraints",
                "--use-annotated",
                "--disable-timestamp",
                "--custom-file-header",
                HEADER,
                "--formatters",
                "ruff-format",
                "ruff-check",
            ],
            check=True,
        )
    # The ruff formatter leaves its cache in the output.
    shutil.rmtree(dest / ".ruff_cache", ignore_errors=True)


def same_tree(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(same_tree(a / d, b / d) for d in cmp.common_dirs if d != "__pycache__")


def main() -> None:
    if "--check" in sys.argv:
        with tempfile.TemporaryDirectory() as t:
            fresh = Path(t) / "contracts"
            generate(fresh)
            if not OUT.exists() or not same_tree(fresh, OUT):
                sys.exit("backend/app/contracts is stale; run make gen")
        print("ok: backend/app/contracts is up to date")
        return
    if OUT.exists():
        shutil.rmtree(OUT)
    generate(OUT)
    print(f"wrote {OUT.relative_to(BACKEND)}")


if __name__ == "__main__":
    main()
