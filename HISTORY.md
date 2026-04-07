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

---

## 2026-04-07 — Test Coverage and Bug Fix Session

### Context

Continuation of `thuja-language` session. Goal: comprehensive test coverage across all features used in real compositions in `csound-pieces`, using tests as living documentation. Each issue got its own branch and PR. A real bug was discovered in the process.

### Bug Fixed

**Heap/random first-draw always returned `values[0]` (PR #38, issue #31)**
`Itemstream` initialized `self.index = 0` and the random-selection logic ran *after* returning the current value, not before. Result: the first `get_next_value()` call on any fresh `heap` or `random` stream always returned `values[0]` regardless of seed. For heap mode, this also meant one value could appear twice (and another not at all) within a single N-draw cycle.

Fix: at the end of `Itemstream.__init__`, for `heap` and `random` streammodes, initialize `self.index` to a random position. For heap mode, also seed `heapdict` with that index so it is treated as already drawn.

### Bugs Filed

**#40 — `'r'` (rest) does not zero amplitude**
`pc_to_freq('r')` returns frequency 0 but leaves the amplitude stream untouched. A rest note is emitted with full amplitude. Documented in test `test_rest_does_not_zero_amplitude`. Design decision needed (see issue #40).

### Issues Filed and Fixed (PRs #37–#44)

**#29, #30 — PR #37**
- `post_process(note, context)` 2-param signature via `funcsigs` signature detection
- Context dict persists and mutates across all notes in a `generate_notes()` call
- `score_dur` correctness with child generators (extends to cover deepest child)
- Also carries forward uncommitted `notegenerator.py` changes: import cleanup, `kickoff()`/`ko()` live-coding helpers, lambda evaluation order fix

**#31 — PR #38** (includes bug fix above)
- `streammode=random` behavior isolated and tested
- Heap exhaustion/refill cycle verified
- Itemstream `seed` constructor param: reproducibility confirmed
- `set_streams_to_seed()`: two generators with same seed produce identical output

**#32 — PR #39**
- Lambda streams on non-duration fields (pan, amplitude, percent)
- Lambda receives note with rhythm already set

**#33 — PR #41**
- Rests in pitch streams: frequency → 0
- Octave persistence: bare note inherits previous octave; per-stream state
- Chords and rests coexisting in same stream

**#34 — PR #42**
- `with_instr()`, `with_index()` verified in score output
- `notetypes.path` returns quoted string unchanged
- `pfields.append()` and `pfields +=` patterns verified

**#35 — PR #43**
- Tuple stream `get_next_value()` returns correct dict
- Values from both mapping lists advance in sync
- Wrapping and shorter-list-padding behavior

**#36 — PR #44**
- `generator_dur` relative time limit: child stops at `start_time + generator_dur`
- `generator_dur > 0` makes `start_time` absolute (not offset by parent)
- Documented distinction from `time_limit` (absolute vs relative)

### todos.md Refresh

Full pass over `tests/todos.md`: all newly covered items moved to "Already Covered" section; outstanding gaps updated with accurate priority based on `csound-pieces` usage analysis. Five low-priority items remain, plus two open bugs (#27, #40).

### Test Count

53 tests at start of session. End of session: 86 tests (across master after all PRs merged).
