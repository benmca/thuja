# Thuja Change History

This file tracks significant changes, decisions, and context behind work done on this codebase — more than commit messages can hold.

---

## 2026-04-12 — Bug fix: rest ('r') zeros amplitude (#40)

`generate_next_note()` now sets `amplitude=0` when `frequency==0` (i.e., when a rest is encountered in a pitch stream). Previously, rests only zeroed frequency — amplitude came through unchanged from the amp stream, producing a note that Csound would attempt to play at zero frequency. The fix is applied after all streams and post_processes have run, so user-set amplitude values for non-rest notes are unaffected.

The existing test `test_rest_does_not_zero_amplitude` (which documented the bug) is updated to `test_rest_zeros_amplitude` and now asserts amplitude=0 on rest, with normal amplitude restored on the following non-rest note.

---

## 2026-04-11 — Per-generator tempo ratio (#46) + multi-generator thread (#47)

### Per-generator tempo ratio (#46)

Added `tempo_ratio` attribute to `NoteGenerator` (default `1.0`). When `_set_generator_tempos` updates rhythm streams, it applies `bpm * effective_ratio` where the ratio composes through the hierarchy: if parent has ratio 1.0 and child has ratio 0.5, child gets `bpm * 0.5`. A grandchild with ratio 2.0 gets `bpm * 0.5 * 2.0 = bpm * 1.0`.

### Multiple top-level generators (#47)

`NoteGeneratorThread` now accepts either a single generator or a list. Internally stores `_generators` (list of roots). Each root is an independent tree with independent lifecycle.

New methods:
- `add_generator(g, quantize=None)` — adds a root generator mid-performance. `quantize` controls when it starts: `None` = current score time (immediate), `'beat'` or `1` = next beat, `'bar'` or `4` = next bar, any integer N = next N-beat boundary. Without a LinkFollower, quantize is ignored. Rebuilds cursor heap.
- `remove_generator(g)` — removes a root, buffered notes still dispatch
- `gen(generator=g)` — selective reset: only resets the specified generator's cursor tree

`_init_cursors`, `_update_tempos`, and `_rebuild_cursors` iterate over all roots. `self.g` preserved as reference to the first generator for backward compatibility.

### Test count: 181 (was 167). All passing.

---

## 2026-04-11 — Streaming child generators + sync accuracy tests

### Streaming child generators (Phase 2 of StreamingGeneration-Plan)

`_fill_buffer()` now pulls from a min-heap of cursors — parent plus all children at any nesting depth — interleaving notes by start time. `_init_cursors()` does a recursive depth-first walk of the generator tree, applying the same limit-inheritance and start_time-offset logic as batch `generate_notes()`. `gen()`, `_check_pending_swap()`, and `_poll_link()` all reset/snap the full cursor tree, not just the root generator.

Supports arbitrary nesting depth. `csound-pieces` uses at most 2 levels; a 3-level nesting test verifies start_time chaining and limit inheritance cascade.

### Bug fix: streaming after generate_notes()

`_init_cursors()` now calls `reset_cursor()` on each generator (resetting both `cur_time` and `note_count`) instead of just setting `cur_time = start_time`. Without this, calling `generate_notes()` before `kickoff(streaming=True)` exhausted `note_count`, causing `generate_next_note()` to return `None` immediately — no sound. Found while testing `csound-pieces/thuja-ep/olallan/jams4.py`.

### Issue #27 resolution (parent/child limit semantics)

Documented the existing behavior: parent `time_limit` and `note_limit` are *defaults*, not hard constraints. If a child sets its own limits, the child's values win — even if they exceed the parent's. This is replicated identically in both the batch path (`generate_notes()`) and the streaming path (`_collect_cursors()`). No code change; comment clarified in both locations.

### Sync accuracy tests

19 tests for `latency_offset_secs` (7), `establish_sync_via_probe` (6), and `probe_sync` (6). Moved from Outstanding Gaps to Already Covered in `tests/todos.md`.

### Test count: 167 (was 136). All passing.

---

## 2026-04-11 — Link sync accuracy: active-probe anchor + latency offset

### Context
With streaming generation and Link following already implemented on `feature/link-follower`, the example sounded consistently late by an audible amount across tempo changes. Instrumented the sync path to find out why, and added a configurable compensation knob.

### Diagnosis
Added probe instrumentation (`LinkFollower.probe_sync()`) that sends a fresh `status\n` to carabiner and compares carabiner's reported beat against the sync model's beat. Ran the example at multiple tempos (60/90/120/240 bpm) and measured:

- `delta_send` — model at pre-send time vs probe
- `delta_mid`  — model at send + rtt/2 vs probe
- `delta_recv` — model at post-recv time vs probe

Key findings:

1. **Carabiner RTT is ~20–25 ms on localhost.** Not the sub-ms we'd expect from a local TCP roundtrip — carabiner apparently services status requests on its own ~50 Hz internal loop.
2. **Carabiner does not push unsolicited updates** (beyond tempo-change notifications). `drained_before` / `drained_after` were always 0.
3. **Initial anchor and each tempo-change re-anchor introduced their own systematic offset**, because `establish_sync()` projected `_last_beat` forward from `_last_beat_wall_time` (the parse timestamp, not the send timestamp). The delay between carabiner sending and us reading the status line varied per call.
4. **Carabiner samples its reported beat at the midpoint of the RTT window.** Measuring `delta_mid` at steady state gave values consistently within ±2 ms of zero across 60/120/240 bpm — confirming the sync model itself is accurate.

The residual audible lateness was *not* a sync-model error. It's audio output latency: Csound software buffer + hardware buffer + driver + DAC. With `-b 1024 -B 4096` at 44100 Hz plus CoreAudio + Mac speaker output, that's ~150 ms.

### Changes

**`LinkFollower.establish_sync_via_probe(csound_time_fn)`**
New anchor method. Sends fresh `status\n`, reads the reply, drains any races (prefers latest), and anchors `(csound_time_at_recv, _last_beat)` with no projection correction. Replaces the passive `establish_sync()` call in `kickoff` and `_poll_link`. The old `establish_sync()` is kept (still used by tests, still correct mathematically) but marked as less accurate in its docstring.

**`LinkFollower.latency_offset_secs` (new field)**
Tunable fixed wall-time offset applied in `current_beat()` and `csound_time_for_beat()`. Positive values shift notes earlier in wall time, compensating for audio output latency. Live-adjustable mid-performance (e.g. `lf.latency_offset_secs = 0.15`). The example now defaults to `0.15`, which is the measured sweet spot for Csound default buffers + macOS built-in speakers.

**`LinkFollower._drain_nonblocking()` (new helper)**
Extracted drain-and-discard logic used by both `probe_sync()` and `establish_sync_via_probe()`.

**`LinkFollower.probe_sync()` (revised)**
Now returns `(model_beat, probe_beat, delta, drained_before, drained_after, rtt_secs)`. Drains queued pushes before sending and prefers the latest post-recv line, so the returned beat is guaranteed to reflect a reply to the current request, not a stale push.

**`NoteGeneratorThread._poll_link` and `kickoff`**
Both now call `establish_sync_via_probe()` at anchor time. The startup drain dance in `kickoff` is gone — subsumed by the new method.

**`doc/LinkFollower-GettingStarted.md` (moved from `examples/`)**
Moved the getting-started guide out of `examples/` into `doc/` where narrative documentation lives. Updated content to describe streaming mode, the active-probe anchor, and the new latency offset field. Added a *Notes on calculating latency* section with the formula `(b + B) / sample_rate + driver_latency`, a worked example for the defaults, and a quick-reference table of buffer/sample-rate combinations. Decision: keep latency tuning fully manual rather than auto-computing from Csound options — the driver term is the dominant unknown anyway, so a documented formula is more useful than partial automation.

### Decision rationale

The original diagnostic hypothesis was "add a midpoint correction in `establish_sync_via_probe` to account for carabiner's sample timing." That was tried and made things *worse* — each anchor's RTT was different, so it introduced its own per-anchor bias that persisted until the next re-anchor. Dropping the correction entirely and anchoring at raw `_last_beat` from the fresh probe gave `delta_mid` within ±2 ms across all tempo regimes (except one 240→120 transition, which showed a ~10 ms outlier with no clear cause — left unfixed pending a reproducible case).

A fixed per-anchor bias is acceptable because probe measurements have the same bias and cancel out. The audible offset that remained was audio output latency, which `latency_offset_secs` solves at the compensation layer rather than by fighting the sync model.

### Test Count
Still 136 tests, all passing. No new tests added this session — the changes are observable behavior fixes, and the sync-model math was already well-covered. A dedicated test for `latency_offset_secs` semantics (round-trip identity when offset=0, expected shift when nonzero) should be added.

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

---

## 2026-04-08 — LinkFollower Implementation (feature/link-follower)

### Context

First implementation pass on the Ableton Link sync feature described in `LinkFollower-Plan.md`. Goal: tempo following (Phase 1) and quantized note regeneration (Phase 2) wired into `NoteGeneratorThread`, with all existing behavior unaffected.

### Design Decisions

**`target_beat` not `target_csound_time`**
Quantized swaps store the Link beat number as the target, not the equivalent Csound time. Csound time for a given beat changes when tempo changes; the Link beat number does not. `_check_pending_swap()` recomputes `current_beat()` live each tick using the current sync point, so the check stays accurate across tempo changes without updating the target.

**`establish_sync()` called on every tempo change**
The sync point `(csound_time, link_beat, bpm)` must be re-recorded any time BPM changes. `_poll_link()` calls `establish_sync()` immediately after detecting a change, before `_update_tempos()`, so that all subsequent `current_beat()` calls use the new BPM.

**`next_boundary()` uses strictly-next semantics**
`floor(cb / q) + 1` rather than `ceil(cb / q)`. If `gen(quantize=4)` is called exactly on a bar boundary, the swap waits for the following bar, not the current one. This avoids an immediate swap that defeats the purpose of quantization.

**Mock socket via `_socket_factory` injection**
`LinkFollower.__init__` accepts an optional `_socket_factory` callable. Tests pass a factory that returns a `MagicMock` socket. This keeps the class clean (no test-only hooks) while making all 12 tests runnable without a live carabiner process.

**All `NoteGeneratorThread` changes are additive**
`link_follower=None` default; all new logic gated on non-None. `_poll_link()` and `_check_pending_swap()` are no-ops when `link_follower` is None. Zero impact on existing call sites.

### New Files

- **`thuja/link_follower.py`** — `LinkFollower` class; standalone, no thuja dependency
- **`examples/link_follower_ex.py`** — end-to-end example: connects to carabiner, starts a generator thread, demonstrates quantized swap
- **`examples/LinkFollower-GettingStarted.md`** — setup guide: carabiner install on macOS, verifying Link, running the example

### Modified Files

- **`thuja/notegenerator.py`** — `NoteGeneratorThread`: added `link_follower` param, `_pending_swap`, `gen(quantize=...)`, `_poll_link()`, `_check_pending_swap()`, `_update_tempos()`, `_set_generator_tempos()`; `kickoff()` and `ko()` accept `link_follower=None` and call `establish_sync()` before starting the thread
- **`CLAUDE.md`** — updated `LinkFollowerProposal.md` reference to `LinkFollower-Plan.md`; updated file count to 8
- **`tests/todos.md`** — LinkFollower coverage added to "Already Covered"; NoteGeneratorThread note updated
- **`HISTORY.md`** — this entry

### Test Count

86 tests at start of session. End of session: 113 tests.

---

## 2026-04-08 — Streaming Note Generation (feature/link-follower)

### Context

Batch `generate_notes()` pre-bakes all note start times at a fixed tempo. When Ableton Link changes the BPM, every pre-baked start time is wrong — the only remedy is a full regeneration. This defeats the purpose of real-time tempo following. Streaming generation produces one note at a time on demand, so tempo changes take effect within one lookahead window.

### Design Decisions

**`generate_next_note()` extracts the loop body**
The inner loop of `generate_notes()` is already stateful and self-contained: Itemstreams advance their indices, `cur_time` accumulates, octave state persists. Nothing in it requires the full batch to exist first. Extracting it as `generate_next_note()` required minimal refactoring. `generate_notes()` becomes a thin wrapper that calls it in a loop; all existing behavior is preserved.

**`reset_cursor(reset_streams=False)` rewinds timing only**
Resets `cur_time` to `start_time` and `note_count` to 0 without touching stream state. Used by `gen()` and `_check_pending_swap()` in streaming mode to restart note generation from the current score time. `reset_streams=True` also resets Itemstream indices, heap state, and octave state (full restart).

**Lookahead buffer as a `deque` of `(start_time, note_str)` tuples**
`NoteGeneratorThread` maintains a deque covering the next `lookahead_secs` (default 2.0s). `_fill_buffer(target)` calls `generate_next_note()` until the buffer covers `target`. On tempo change, `_flush_stale_buffer()` removes notes with `start_time > current_score_time`; the buffer refills on the next tick at the new tempo.

**`_fast_forward_to(target)` prevents burst dispatch after cursor reset**
After `reset_cursor()`, `cur_time` is at `start_time`. Without fast-forwarding, the first `_fill_buffer()` call would generate notes starting at 0 — all of which would be instantly dispatched as overdue. `_fast_forward_to(score_time)` generates and discards notes up to the current score time before filling the buffer.

**`_pending_swap.notes = None` signals a streaming reset**
The existing `_PendingSwap` namedtuple is reused for quantized gen() in streaming mode. `notes=None` distinguishes the streaming path (pending cursor reset) from the batch path (pending notes-list swap). No new namedtuple needed.

**Phase 1: children fall back to batch**
Child generators are processed in a separate pass in `generate_notes()`. In streaming mode, only generators with no children use the new path. Generators with children fall back to batch automatically. Phase 2 (per-child cursors with buffer merge-sort) is deferred.

### Modified Files

- **`thuja/notegenerator.py`** — `NoteGenerator`: `generate_next_note()` extracted from loop body; `reset_cursor(reset_streams=False)` added; `generate_notes()` refactored as thin wrapper. `NoteGeneratorThread`: `streaming=False`, `lookahead_secs=2.0`, `_buffer=deque()` added to `__init__`; `_fill_buffer()`, `_flush_stale_buffer()`, `_fast_forward_to()` added; `run()` has streaming branch; `gen()`, `_poll_link()`, `_check_pending_swap()` updated for streaming path; `kickoff()` and `ko()` accept `streaming=` and `lookahead_secs=` params
- **`examples/link_follower_ex.py`** — updated to use `streaming=True`, `time_limit=7200` (no pre-bake), comprehensive diagnostic logging
- **`StreamingGeneration-Plan.md`** — full architecture plan saved before implementation
- **`tests/test_streaming.py`** — new test suite (see below)

### Test Coverage Added

21 new tests in `tests/test_streaming.py`:

- **`TestGenerateNextNote`**: equivalence with batch `generate_notes()`; exhaustion returns None; `cur_time` advances correctly; `time_limit` respected; `score_dur` matches batch
- **`TestResetCursor`**: rewinds `cur_time`; resets `note_count`; preserves stream state by default; `reset_streams=True` resets indices; first note after reset matches original
- **`TestBufferHelpers`**: `_fill_buffer` generates notes up to target; `_fill_buffer` stops at target; `_flush_stale_buffer` removes future notes; `_fast_forward_to` advances `cur_time`; `_fast_forward_to` adds nothing to buffer
- **`TestStreamingTempoChange`**: `_poll_link` flushes buffer on tempo change; `_poll_link` updates rhythm stream tempo; next notes after tempo change use new BPM
- **`TestStreamingGen`**: immediate `gen()` resets cursor and fast-forwards; `gen(quantize=4)` sets `_pending_swap` with correct target beat and `notes=None`; `_check_pending_swap` fires and clears at target beat

### Test Count

113 tests at start of session. End of session: 136 tests.

---

## 2026-04-09 — Branch Status Summary (feature/link-follower)

### Streaming Generation — Complete

Everything in `StreamingGeneration-Plan.md` is implemented and committed:

- `generate_next_note()` — single-note on-demand extraction from loop body
- `reset_cursor(reset_streams=False)` — rewinds timing without touching stream state
- `generate_notes()` — refactored as thin wrapper; all existing behavior intact
- `NoteGeneratorThread` — lookahead deque buffer (`_fill_buffer`, `_flush_stale_buffer`, `_fast_forward_to`); streaming `run()` dispatch; streaming paths in `gen()`, `_poll_link()`, `_check_pending_swap()`
- `kickoff()`/`ko()` — accept `streaming=True` and `lookahead_secs=` params
- `link_follower_ex.py` — updated to use `streaming=True`, `time_limit=7200`, no pre-bake
- 21 new tests in `tests/test_streaming.py`; all 136 tests pass

**Phase 2 deferred:** Child generators fall back to batch in streaming mode. Noted in `StreamingGeneration-Plan.md`.

### LinkFollower — Complete

Everything in `LinkFollower-Plan.md` Phase 1 + Phase 2 is implemented and committed:

- `LinkFollower` class — carabiner connection, BPM/beat parsing (both carabiner 1.x and 1.2+ formats), `establish_sync()`, `current_beat()`, `next_boundary()` (strictly-next semantics), `poll()`
- `NoteGeneratorThread` — `_poll_link()` updates tempos on BPM change, `gen(quantize=N)` queues swap at next beat boundary, `_check_pending_swap()` fires at target beat
- 12 tests in `tests/test_link_follower.py` using mock socket injection

### What Remains Before PR

1. Live end-to-end test: run `link_follower_ex.py` with carabiner + Ableton to confirm streaming tempo following works in practice
2. Minor: update `CLAUDE.md` file count (8 → 9 after adding `link_follower.py`)
3. Open PR: `feature/link-follower` → `master`
