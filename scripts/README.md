# Dataset generator scripts (one-off, not used at runtime)

These four scripts were used during development to generate
`data/default_vocab.json` (the 700-word / 70-unit dataset) and
`data/vocab_template.csv`. **None of them are imported by the running app** —
the app only reads the already-generated JSON/CSV files via
[`utils/data_loader.py`](../utils/data_loader.py).

They're kept here for reference in case the word list needs to be
regenerated or extended, not because they run on a schedule or on deploy.

- `build_dataset.py`, `generator.py`, `build_vocab_data.py` — three
  successive attempts at generating the base 700-word list. They overlap
  significantly; `build_vocab_data.py` is the most complete and is believed
  to be the one that produced the dataset currently shipped in `data/`.
- `build_rich_vocab.py` — a later pass that enriched the dataset with
  derivatives, synonyms and antonyms (the fields you see today in the
  flashcard view).

**Before running any of these**, check the script for hardcoded paths —
`build_vocab_data.py` in particular has an absolute Windows path
(`C:/Users/User/...`) left over from the machine it was written on and
will need that updated to a real path on your machine first.

If you're confident these are fully superseded by `data/default_vocab.json`
and won't be needed again, it's reasonable to delete this folder — they're
kept for now rather than removed outright since it wasn't clear which
version was authoritative.
