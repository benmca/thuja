# Test Coverage Gaps - Thuja

This document tracks outstanding test coverage gaps. Items are removed as tests are written.

**NOTE:** Priorities reflect real-world usage frequency across ~62 files in `../csound-pieces/thuja-ep/`.

Last updated: 2026-03-14

---

## Already Covered

The following were gaps at the start of the `thuja-language` session and are now tested:

- `time_limit` — stops generation, zero means no limit, all notes within boundary
- `deepcopy()` — streams independent, children cleared, original unaffected, context independent
- `deepcopy_tree()` — children included
- Chording — simultaneous notes at same start_time, time advances once per chord
- Child generator inheritance — inherits time_limit, note_limit, start_time offset, notes sorted
- `set_stream()` — Itemstream, string, list, callable coercion
- `with_streams()` — OrderedDict, plain dict, returns self
- Mutable default args (#13)
- `get_tempo()` / `Line.tempo()` setter (#14)
- `g()` and `randomize()` on NoteGenerator (#16)
- `Line.pitches()` string/list/Itemstream (#12)
- `setup_index_params()` utility (#18)
- Tuple streams — dict-of-dicts form (`test_callables`)
- `gen_lines` and `end_lines` — implicit in `test_tempo`, `test_literals`
- Tempo as list — `np.linspace(...)` in `test_tempo`
- Heap streammode — basic usage in `test_literals`
- Lambda on duration — `test_callables_lambda`, `test_child_generators`
- Multiple `generate_notes()` calls — `test_tempo` and `test_literals` both call it twice

---

## Outstanding Gaps

### Extremely Critical (55+ files in csound-pieces)

**1. Explicit 2-param `(note, context)` post_process signature**
`test_callables_postprocesses` uses a 1-param closure that accesses `g.context` directly via closure — it does NOT exercise the `def pp(note, context):` injection path that `funcsigs` signature detection handles. This is the dominant pattern across 55 files.
- Need: post_process defined as `def pp(note, context):`, verify context is injected and mutations persist across notes.

**2. Context dict persistence and mutation across notes**
No test verifies that `context["counter"] += 1` in a post_process accumulates correctly across N notes — i.e., the same dict is threaded through every call.
- Need: post_process increments a counter, assert final value equals note count.

---

### Very Common (20–42 files)

**3. `streammode=random`**
33 files use it. Only `sequence` and `heap` are isolation-tested. Random mode allows repetition; distinct from heap.
- Need: verify values come from the defined set; verify repetition is allowed (unlike heap); verify behavior differs from heap with a seed.

**4. Itemstream seed constructor param**
20 files use `Itemstream([...], seed=42)`. No test that seeding produces reproducible output.
- Need: same seed + heap/random → identical sequence on repeated `generate_notes()` calls; different seed → different sequence.

**5. `set_streams_to_seed()`**
4 files use this for reproducible generation. Completely untested.
- Need: after `set_streams_to_seed(n)`, two `generate_notes()` runs produce identical note lists.

**6. Lambda on non-duration fields**
42 files use lambdas for pan, percent, amplitude. Only duration lambdas tested.
- Need: lambda passed to `with_pan()`, `with_amps()`, `with_percent()` is called per note and result appears in generated score.

**7. Rests (`'r'`) in pitch streams**
10 files. No test. Behavior: 'r' sets frequency to 0 (and amplitude to 0?).
- Need: verify 'r' produces a note with frequency=0; verify behavior when 'r' appears alongside normal pitches.

**8. Octave persistence**
38 files implicitly depend on it. `test_basiccase` uses `['c4','c','c','d']` but never asserts the bare `'c'` resolves to c4.
- Need: explicit assertion that omitting octave inherits from previous pitch in the stream.

**9. Path notetype**
19 files. Completely untested.
- Need: `Itemstream(['/path/to/file.wav'], notetype=notetypes.path)` returns the string as-is (no pitch/rhythm conversion applied).

---

### Common (6–23 files)

**10. Tuple streams via `mapping_keys` / `mapping_lists` constructor form**
23 files use this form. `test_callables_postprocesses` uses it but only checks score line count, not correctness of `get_next_value()` output.
- Need: verify `get_next_value()` returns a dict with the correct keys; values from both lists advance in sync.

**11. Chords mixed with rests**
3 files use `[['c4','e4'], 'r', 'd4']` patterns. Chord tests don't include rests in the same stream.
- Need: stream with nested chord list alongside `'r'` values — verify rest produces silence and chord notes generate normally.

**12. `with_instr()` / `with_index()`**
19 and 12 files respectively. `test_child_generators` uses them but makes no assertions.
- Need: verify the set instrument/index value appears at the correct pfield position in the generated score line.

**13. pfields list appending**
23 files use `generator.pfields += [custom_key, ...]` to add output columns. No test.
- Need: verify custom pfield names added to `pfields` appear as additional tab-delimited columns in generated score lines.

**14. `score_dur` with child generators** (issue #30)
56 files use `score_dur` for `end_lines`. Tests confirm it's set, but not its correctness when children extend past the parent.
- See GitHub issue #30.

**15. `generator_dur` relative limits**
2 files (generative/457.py, gesture_draft.py) set `generator_dur` on spawned child generators. Untested.
- Need: child with `generator_dur` set stops generating after that duration relative to its start; verify against a child with `time_limit` for comparison.

---

### Lower Priority (0–4 files in wild)

**16. String args to Itemstream constructor**
4 files use shorthand string streammode/notetype args: `Itemstream(['q'], 'sequence', notetype='rhythm')`. Tests the Itemstream constructor string coercion, distinct from `with_pitches('c4 d e')`.

**17. Heap exhaustion/refill cycle**
26 files depend on heap refilling after all values used. No test that the pool resets correctly and no value repeats within a cycle.

**18. `generate_score()` with filename argument**
1 file. Very rare. Verify score is written to disk correctly.

**19. `add_bars_to_starttime()`**
0 files in wild. Low value until it sees real usage.

**20. `clear_notes()`**
0 files in wild. Low value.

---

## Not Worth Testing Now

- **NoteGeneratorThread** — requires live Csound; unit-test coverage impractical without mocking ctcsound
- **Tempo as callable** — 0 files in wild
- **UDP send methods** — 0 files in wild
- **csound_utils** — integration-only; requires Csound installed
