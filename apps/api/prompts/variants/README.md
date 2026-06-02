# Prompt variants (A/B)

The active prompts are `prompts/classify.md`, `prompts/curate_daily.md`,
`prompts/curate_weekly.md` (loaded by `engine/llm.py` and version-controlled).

To trial a candidate set without touching the active files, drop a full copy here
(or in any dir) and point the engine at it:

```sh
# dry-run a candidate prompt set
NINTEL_LLM_ENABLED=true NINTEL_PROMPT_DIR=src/nintel/prompts/variants \
    .venv/bin/python -m nintel.pipeline build --type daily

# evaluate structural quality (cite integrity, sections, subject/impact, schema)
NINTEL_LLM_ENABLED=true NINTEL_PROMPT_DIR=src/nintel/prompts/variants \
    .venv/bin/python -m pytest -m eval -q
```

`NINTEL_PROMPT_DIR` overrides `settings.prompts_dir`. A variant dir must contain
all three files the active set has (the loader reads by filename). Git history is
the version log; add a `<!-- version: N; updated: YYYY-MM-DD -->` comment at the
top of each prompt for human traceability (it's a comment, ignored by the model).

Keep per-run/retrieved text OUT of the prompt files — it goes in the user turn
(see `llm.py`) so the cached system prefix stays stable.
