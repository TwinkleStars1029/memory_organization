from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Tuple

import yaml

CHUNKS_DIR = Path("chunks")
OUT_CHAPTERS_DIR = Path("output/chapters")
SCHEMA_PATH = Path("schema.yaml")


def load_schema() -> Dict[str, Any]:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Missing schema file: {SCHEMA_PATH}")
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def list_sorted(dir_path: Path, pattern: str) -> List[Path]:
    return sorted(dir_path.glob(pattern))


def validate_field(value: Any, field: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    name = field.get("name")
    ftype = field.get("type")
    required = bool(field.get("required", False))

    if value is None:
        if required:
            errors.append(f"Missing key: {name}")
        return errors

    if ftype == "string":
        if not isinstance(value, str):
            errors.append(f"{name} must be a string")
        else:
            v = value.strip()
            if field.get("non_empty") and not v:
                errors.append(f"{name} is empty")
            max_chars = field.get("max_chars")
            if isinstance(max_chars, int) and len(v) > max_chars:
                errors.append(f"{name} exceeds max_chars={max_chars} (len={len(v)})")
            pattern = field.get("pattern")
            if pattern and not re.match(pattern, v):
                errors.append(f"{name} does not match pattern: {pattern}")

    elif ftype == "list":
        if not isinstance(value, list):
            errors.append(f"{name} must be a list")
        else:
            min_items = field.get("min_items")
            max_items = field.get("max_items")
            if isinstance(min_items, int) and len(value) < min_items:
                errors.append(f"{name} requires >= {min_items} items")
            if isinstance(max_items, int) and len(value) > max_items:
                errors.append(f"{name} requires <= {max_items} items")

            min_non_empty_items = field.get("min_non_empty_items")
            if isinstance(min_non_empty_items, int):
                non_empty = sum(1 for x in value if isinstance(x, str) and x.strip())
                if non_empty < min_non_empty_items:
                    errors.append(f"{name} requires >= {min_non_empty_items} non-empty items")

    elif ftype == "dict":
        if not isinstance(value, dict):
            errors.append(f"{name} must be an object/dict")
        else:
            keys = field.get("dict_keys", [])
            for k in keys:
                if k not in value and str(k) not in value:
                    errors.append(f"{name} missing key: {k}")

            if field.get("non_empty_any"):
                any_non_empty = False
                for v in value.values():
                    if isinstance(v, str) and v.strip():
                        any_non_empty = True
                        break
                if not any_non_empty:
                    errors.append(f"{name} has no non-empty values")

    else:
        errors.append(f"{name} has unsupported type: {ftype}")

    return errors


def validate_yaml_against_schema(path: Path, schema: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["Root is not a mapping/object"]

    fields = schema.get("fields", [])
    field_names = [f.get("name") for f in fields]

    extra_keys = [k for k in data.keys() if k not in field_names]
    if extra_keys:
        errors.append(f"Extra keys not in schema.yaml: {extra_keys}")

    for f in fields:
        name = f.get("name")
        value = data.get(name)
        errors.extend(validate_field(value, f))

    return errors


def main() -> int:
    if not CHUNKS_DIR.exists():
        print(f"Missing directory: {CHUNKS_DIR.as_posix()}", file=sys.stderr)
        return 2
    if not OUT_CHAPTERS_DIR.exists():
        print(f"Missing directory: {OUT_CHAPTERS_DIR.as_posix()}", file=sys.stderr)
        return 2
    if not SCHEMA_PATH.exists():
        print(f"Missing schema file: {SCHEMA_PATH.as_posix()}", file=sys.stderr)
        return 2

    schema = load_schema()

    chunks = list_sorted(CHUNKS_DIR, "ch_*.txt")
    yamls = list_sorted(OUT_CHAPTERS_DIR, "ch_*.yaml")

    print(f"Chunks: {len(chunks)}")
    print(f"YAMLs : {len(yamls)}")

    chunk_ids = {p.stem for p in chunks}
    yaml_ids = {p.stem for p in yamls}

    missing_yaml = sorted(chunk_ids - yaml_ids)
    extra_yaml = sorted(yaml_ids - chunk_ids)

    if missing_yaml:
        print("\nMissing YAML for chunks:")
        for x in missing_yaml:
            print(f"  - {x}.yaml")

    if extra_yaml:
        print("\nYAML exists without chunk:")
        for x in extra_yaml:
            print(f"  - {x}.yaml")

    bad: List[Tuple[Path, List[str]]] = []
    for y in yamls:
        errs = validate_yaml_against_schema(y, schema)
        if errs:
            bad.append((y, errs))

    if bad:
        print("\nInvalid / incomplete YAML files:")
        for y, errs in bad:
            print(f"\n- {y.as_posix()}")
            for e in errs:
                print(f"    * {e}")
    else:
        print("\nAll YAML files passed validation checks.")

    problems = len(missing_yaml) + len(bad)
    print(f"\nSummary: problems={problems} (missing_yaml={len(missing_yaml)}, bad_yaml={len(bad)})")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
