# Test Coverage Gaps - Thuja

This document tracks outstanding test coverage gaps. Items are removed as tests are written.

**NOTE:** Priorities reflect real-world usage frequency across ~62 files in `../csound-pieces/thuja-ep/`.

Last updated: 2026-04-11 (link sync accuracy)

---

## Already Covered

The following were gaps at the start of the `thuja-language` session and are now tested:

**PR #28 (initial coverage push):**
- `time_limit` — stops generation, zero means no limit, all notes within boundary
- `deepcopy()` — streams independent, children cleared, original unaffected, context independent
- `deepcopy_tree()` — children included
- Chording — simultaneous notes at same start_time, time advances once per chord
- Child generator inheritance — inherits time_limit, note_limit, start_time offset, notes sorted

**PR #37 (#29, #30):**
- `post_process(note, context)` 2-param signature — funcsigs detects params, context injected
- Context dict persists and mutates correctly across all notes in a `generate_notes()` call
- Chained post_processes run in order
- `init_context` pre-populates context before generation
- `score_dur` — equals last note start + duration; extends to cover child generators; max across all children

**PR #38 (#31) — includes bug fix:**
- Bug fixed: heap and random Itemstreams always returned `values[0]` as first draw
- `streammode=random` — values come from defined set; allows consecutive repeats
- Heap — no repeat within one cycle; refills correctly after exhaustion
- Itemstream `seed` constructor param — same seed → same sequence; different seeds → different sequences
- `set_streams_to_seed()` — two generators with same seed produce identical output; context streams also reseeded

**PR #39 (#32):**
- Lambda on pan, amplitude, percent — return value appears at correct score position
- Lambda receives note object with rhythm set (can compute tempo-aware values)
- Lambda called fresh per note (distinct values across notes)

**PR #41 (#33):**
- `'r'` in pitch stream → frequency 0
- `'r'` does not zero amplitude (documented as bug #40)
- Octave persistence — bare note name inherits previous octave; resets on new octave
- Octave state is per-stream
- Chord and rest coexist in same pitch stream

**PR #42 (#34):**
- `with_instr(n)` — instrument embedded as `i<n>` in score line
- `with_index(n)` — value appears at correct column when key appended to pfields
- `notetypes.path` — value returned as `"<path>"` (quoted string, no conversion)
- Custom pfield via `set_stream()` + `pfields.append()` appears in score
- Custom stream key NOT in pfields produces no extra column
- `pfields += [...]` pattern — multiple custom columns

**PR #43 (#35):**
- Tuple stream `get_next_value()` returns dict with correct keys
- Values from both mapping lists advance in sync
- Wraps after exhaustion (sequence mode)
- Shorter list wraps independently to fill longer list's length
- End-to-end: tuplestream in context, post_process reads it, correct values in score

**PR #44 (#36):**
- `generator_dur` limits child to relative duration from its own start_time
- `generator_dur > 0` makes start_time absolute (not offset by parent)
- Explicit contrast: `time_limit` (absolute) vs `generator_dur` (relative)

**Other (already covered from before):**
- `set_stream()` — Itemstream, string, list, callable coercion
- `with_streams()` — OrderedDict, plain dict, returns self
- Mutable default args (#13)
- `get_tempo()` / `Line.tempo()` setter (#14)
- `g()` and `randomize()` on NoteGenerator
- `Line.pitches()` string/list/Itemstream (#12)
- `setup_index_params()` utility (#18)
- Tuple streams — dict-of-dicts form
- `gen_lines` and `end_lines`
- Tempo as list
- Heap streammode — basic usage
- Lambda on duration
- Multiple `generate_notes()` calls

---

## Outstanding Gaps

### Lower Priority (0–4 files in wild)

**1. String args to Itemstream constructor**
4 files use shorthand string streammode/notetype args: `Itemstream(['q'], 'sequence', notetype='rhythm')`. Tests the Itemstream constructor string coercion, distinct from `with_pitches('c4 d e')`.

**2. Heap exhaustion/refill cycle edge case**
The heap bug fix (PR #38) ensures correct behavior, but no test verifies the boundary between cycles when the heap's internal `heapdict` clears mid-sequence.

**3. `generate_score()` with filename argument**
1 file. Very rare. Verify score is written to disk correctly.

**4. `add_bars_to_starttime()`**
0 files in wild. Low value until it sees real usage.

**5. `clear_notes()`**
0 files in wild. Low value.

**feature/link-follower (streaming generation):**
- `generate_next_note()` — equivalence with batch `generate_notes()`; exhaustion returns None; `cur_time` advances; `time_limit` respected; `score_dur` matches batch
- `reset_cursor()` — rewinds `cur_time` and `note_count`; preserves stream state by default; `reset_streams=True` resets indices and octave state
- `NoteGeneratorThread._fill_buffer()` — generates notes up to target time; stops at target
- `NoteGeneratorThread._flush_stale_buffer()` — removes notes with start_time > score_time
- `NoteGeneratorThread._fast_forward_to()` — advances cur_time without filling buffer
- Tempo change via `_poll_link()` — flushes buffer; updates rhythm stream tempo; new notes use new BPM
- `gen()` immediate in streaming mode — resets cursor, fast-forwards to score_time
- `gen(quantize=N)` in streaming mode — sets `_pending_swap` with `notes=None` and correct `target_beat`
- `_check_pending_swap()` in streaming mode — fires and clears at `target_beat`

---

**feature/link-follower (LinkFollower + NoteGeneratorThread integration):**
- `LinkFollower.connect()` — parses BPM and beat from carabiner initial status
- `LinkFollower.establish_sync()` — stores (csound_time, link_beat, bpm) sync point
- `LinkFollower.current_beat()` — correct math; survives tempo change + re-sync
- `LinkFollower.csound_time_for_beat()` — inverse of current_beat; round-trip verified
- `LinkFollower.next_boundary()` — strictly-next quantum boundary; beat/bar/exactly-on cases
- `LinkFollower.poll()` — returns None when no change; returns new BPM on change
- `NoteGeneratorThread._update_tempos()` — sets tempo on all rhythm-notetype streams
- `NoteGeneratorThread._poll_link()` — calls _update_tempos when poll returns new BPM
- `NoteGeneratorThread.gen(quantize=...)` — sets _pending_swap with correct target_beat
- `NoteGeneratorThread._check_pending_swap()` — fires swap at target_beat; doesn't fire early
- `target_beat` survives tempo change (stored as Link beat number, not Csound time)

---

## Outstanding Gaps

**feature/link-follower (sync accuracy session 2026-04-11):**
- `LinkFollower.establish_sync_via_probe()` — sends fresh status, anchors to reply; race-hardens against pushed pushes by preferring latest post-recv line
- `LinkFollower.probe_sync()` — round-trip measurement + drain counts; reports (model, probe, delta, drained_before, drained_after, rtt)
- `LinkFollower.latency_offset_secs` — round-trip identity when offset=0; `current_beat(t)` shifted by +offset × bpm/60 beats; `csound_time_for_beat(b)` shifted by -offset seconds; live-mutable mid-run

---

## Not Worth Testing Now

- **NoteGeneratorThread run loop** — requires live Csound; _poll_link/_check_pending_swap are tested directly
- **Tempo as callable** — 0 files in wild
- **UDP send methods** — 0 files in wild
- **csound_utils** — integration-only; requires Csound installed

---

## Open Bugs

- **#40** — `'r'` (rest) in pitch stream does not zero amplitude; only frequency is set to 0
- **#27** — Parent/child `time_limit` and `note_limit` semantics: limits are defaults not constraints; child notes are never filtered; `score_dur` can exceed parent's `time_limit`
