# Offline RPG Memory Distillation Skill (Flexible Schema, No API)

## Purpose
Turn long AI-RPG raw chat logs into **representative memory cards** without calling paid APIs.
This workflow uses:
- Python: parsing + chunking + memory skeleton generation
- Codex (VS Code plugin): semantic summarization into memory cards

## Single Source of Truth
All memory card fields and validation rules are defined in:

- `schema.yaml`

To add/remove/change fields:
1) edit `schema.yaml`
2) run `python split.py` (to generate missing skeletons for new chunks)
3) use Codex/Gemini to fill YAMLs
4) run `python verify.py`


## Workflow
1) `python split.py`
2) Codex/Gemini fills `output/chapters/ch_XXXX.yaml` using `MemoryTemplate.txt`
3) `python verify.py`

## Guardrails
- Do not hallucinate
- Do not change schema keys beyond `schema.yaml`
- Keep memory concise and actionable
- During task execution, DO NOT modify any of the following files:`schema.yaml`,`MemoryTemplate.txt`,`split.py`,`verify.py`