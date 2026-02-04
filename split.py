from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

# ===========================
# Configuration
# ===========================
INPUT_PATH = Path("input/raw_chat.txt")
CHUNKS_DIR = Path("chunks")
OUT_CHAPTERS_DIR = Path("output/chapters")
SCHEMA_PATH = Path("schema.yaml")

TURNS_PER_CHUNK = 10
OVERLAP_TURNS = 0  # set >0 if you want overlap context between chunks

MSG_START_RE = re.compile(
    r"^\[(20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s*(.+?):\s*(.*)$"
)


@dataclass
class Turn:
    idx: int
    timestamp: str  # "YYYY-MM-DD HH:MM:SS"
    speaker: str
    content: str


def parse_turns(text: str) -> List[Turn]:
    lines = text.splitlines()
    turns: List[Turn] = []
    current = None
    idx = 0

    for line in lines:
        m = MSG_START_RE.match(line)
        if m:
            if current is not None:
                idx += 1
                turns.append(
                    Turn(
                        idx=idx,
                        timestamp=current["timestamp"],
                        speaker=current["speaker"],
                        content="\n".join(current["content_lines"]).strip(),
                    )
                )

            timestamp, speaker, first_tail = m.group(1), m.group(2), m.group(3)
            current = {
                "timestamp": timestamp,
                "speaker": speaker.strip(),
                "content_lines": [first_tail] if first_tail else [],
            }
        else:
            if current is None:
                continue
            current["content_lines"].append(line)

    if current is not None:
        idx += 1
        turns.append(
            Turn(
                idx=idx,
                timestamp=current["timestamp"],
                speaker=current["speaker"],
                content="\n".join(current["content_lines"]).strip(),
            )
        )

    return turns


def chunk_indices(total_turns: int, chunk_size: int, overlap: int) -> List[Dict[str, int]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >=0 and < chunk_size")

    ranges = []
    start = 0
    ch_id = 1
    while start < total_turns:
        end = min(start + chunk_size, total_turns)
        ranges.append({"ch_id": ch_id, "start_i": start, "end_i": end})
        ch_id += 1
        if end == total_turns:
            break
        # advance start while keeping the requested overlap (if any)
        start = max(end - overlap, 0)
    return ranges


def write_chunk_file(turns: List[Turn], ch_id: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = out_dir / f"ch_{ch_id:04d}.txt"

    header = [
        f"# chunk_id: ch_{ch_id:04d}",
        f"# turns_range: {turns[0].idx}..{turns[-1].idx}",
        f"# turns_count: {len(turns)}",
        "",
    ]

    body = []
    for t in turns:
        body.append(f"[{t.timestamp}] {t.speaker}:")
        body.append(t.content if t.content else "(empty)")
        body.append("")

    filename.write_text("\n".join(header + body), encoding="utf-8")
    return filename


def load_schema() -> Dict[str, Any]:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Missing schema file: {SCHEMA_PATH}")
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def _date_ymd_slash(timestamp: str) -> str:
    date_part = timestamp.split(" ", 1)[0].strip()
    return date_part.replace("-", "/")


def _time_hms(timestamp: str) -> str:
    parts = timestamp.split(" ", 1)
    return parts[1].strip() if len(parts) == 2 else ""


def derived_value(name: str, first_turn: Turn, last_turn: Turn, derived: Dict[str, str]) -> Optional[str]:
    fn = derived.get(name)
    if not fn:
        return None

    if fn == "from_first_turn_date_ymd_slash":
        return _date_ymd_slash(first_turn.timestamp)

    if fn == "from_first_last_turn_time_range":
        t1 = _time_hms(first_turn.timestamp)
        t2 = _time_hms(last_turn.timestamp)
        return t1 if (not t2 or t1 == t2) else f"{t1}-{t2}"

    raise ValueError(f"Unknown derived function: {fn}")


def default_value_for_field(field: Dict[str, Any]) -> Any:
    t = field.get("type")
    if t == "string":
        return ""
    if t == "list":
        return []
    if t == "dict":
        keys = field.get("dict_keys", [])
        return {k: "" for k in keys}
    return None


def make_skeleton(schema: Dict[str, Any], first_turn: Turn, last_turn: Turn) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    derived = schema.get("derived", {}) or {}

    for field in schema.get("fields", []):
        name = field["name"]
        dv = derived_value(name, first_turn, last_turn, derived)
        if dv is not None:
            out[name] = dv
        else:
            out[name] = default_value_for_field(field)
    return out


def write_memory_yaml(ch_id: int, schema: Dict[str, Any], first_turn: Turn, last_turn: Turn, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"ch_{ch_id:04d}.yaml"
    if not path.exists():
        data = make_skeleton(schema, first_turn, last_turn)
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    schema = load_schema()

    text = INPUT_PATH.read_text(encoding="utf-8", errors="ignore")
    turns = parse_turns(text)
    if not turns:
        raise ValueError("No turns parsed. Check input format or MSG_START_RE.")

    ranges = chunk_indices(len(turns), TURNS_PER_CHUNK, OVERLAP_TURNS)

    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)

    for r in ranges:
        ch_id = r["ch_id"]
        chunk_turns = turns[r["start_i"] : r["end_i"]]
        write_chunk_file(chunk_turns, ch_id, CHUNKS_DIR)
        write_memory_yaml(ch_id, schema, chunk_turns[0], chunk_turns[-1], OUT_CHAPTERS_DIR)

    print(f"Parsed turns: {len(turns)}")
    print(f"Chunks written: {len(ranges)} -> {CHUNKS_DIR.resolve()}")
    print(f"Memory YAML skeletons: {len(ranges)} -> {OUT_CHAPTERS_DIR.resolve()}")
    print("Next: use Codex + MemoryTemplate.txt to fill YAML files, then run: python verify.py")


if __name__ == "__main__":
    main()
