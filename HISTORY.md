# Thuja Change History

This file tracks significant changes, decisions, and context behind work done on this codebase — more than commit messages can hold.

---

## 2026-03-14 — Language/Architecture Session (thuja-language)

### Context
Deep dive on separation of concerns between `Line` and `NoteGenerator`, informed by analysis of real composition patterns across ~60 files in sibling repo `csound-pieces`.

### Issues Filed and Fixed

**#12 — NameError in `Line.pitches()`**
`Notetypes()` (capitalized, not imported) was used instead of `notetypes` (module-level instance). Broke the most common pitch-setting path silently. Fixed + regression tests added.

**#13 — Mutable default args in `NoteGenerator.__init__`**
`post_processes=[]` and `gen_lines=[]` caused all instances without explicit args to share the same list. Fixed to `None` with `[]` in body. Regression test added.

**#15 — `NoteGenerator.with_streams()` broken**
Second `if` should have been `elif`; method also didn't return `self`. Fixed both. Tests added.

**#14 — `tempo()` name collision**
`NoteGenerator.tempo()` was a no-arg getter; `Line.tempo(x)` was a fluent setter. Same name, opposite semantics. Renamed base class to `get_tempo()`. Updated two live call sites in csound-pieces (`chapel_october_1.py:157`, `index_study_1_respiration.py:149`).

**#16 — Move `g()` and `randomize()` to `NoteGenerator`**
Both had no `Line`-specific logic. Moved to base class; removed from `Line`. Tests added.

**#17 — Move `set_stream()` to `NoteGenerator`**
Type coercion (str/list/callable → Itemstream) had no `Line`-specific dependency. Moved to base class. Tests covering all coercion paths added.

**#18 — Extract `setup_index_params_with_file()` from `Line`**
Domain-specific boilerplate for index-based sample playback. Extracted to `utils.setup_index_params(generator, filename)`. Updated one call site in csound-pieces (`thuja-ep/1min-cs/153.py`). Test added.

### Issues Filed, Not Yet Fixed

**#27 — Parent/child `time_limit` and `note_limit` semantics**
Parent limits are currently defaults, not constraints. Child notes exceeding parent's `time_limit` are included in output unconditionally. `score_dur` can exceed parent's `time_limit`. Needs a design decision: defaults vs. hard constraints.

### Test Coverage Added (PR #28)

14 new tests covering the highest-priority gaps from `tests/todos.md`:

- **time_limit**: stops at boundary, zero means no limit, all notes within boundary
- **deepcopy**: streams independent, children cleared, original unaffected, context independent
- **deepcopy_tree**: children included
- **chording**: nested pitch lists produce simultaneous notes; time advances once per chord
- **child generator inheritance**: inherits parent time_limit/note_limit when unset, start_time offset, notes sorted

### Proposals Written

- **LinkFollowerProposal.md** — Architecture for syncing `NoteGeneratorThread` to Ableton Link. Thuja follows Link tempo. Phase 1: tempo following. Phase 2: quantized regeneration at beat/bar boundaries. Recommended library: carabiner.

### Tooling

- Installed and configured `gh` CLI for GitHub issue/PR workflow
- Added `REVIEW_PROMPT.md` — structured interactive code review protocol
- Added `CLAUDE.md` "Experimental / Proposals" section

### Test Count

Started: 23 tests. End of session: 53 tests.
