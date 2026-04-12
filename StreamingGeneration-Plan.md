# Streaming Note Generation Plan

## Problem

`generate_notes()` is a batch operation: it pre-computes all note start times at a fixed tempo and stores them as a flat list of strings. When tempo changes, every pre-baked start time is wrong — the only fix is to regenerate the entire batch. This makes real-time tempo following impractical.

## Goal

Produce one note at a time, on demand, so each note is timed at the moment it is needed. Tempo changes take effect on the next note drawn — within one lookahead window.

---

## Key Insight

The inner loop body of `generate_notes()` is already stateful and self-contained. Itemstreams advance their indices, `cur_time` accumulates, octave state persists. Nothing in the loop body requires the full batch to exist before emitting a note. It is already a generator — we just need to expose it as one.

---

## Architecture

### 1. `generate_next_note()` on `NoteGenerator`

Extract the loop body into a method that:
- Draws the next note from streams (advancing all internal state)
- Runs post-processes and callables
- Returns one note string, or a list of note strings for a chord group
- Returns `None` when `time_limit` or `note_limit` is exhausted

`generate_notes()` is kept working exactly as before — it just calls `generate_next_note()` in a loop. No existing behavior changes.

### 2. `reset_cursor()` on `NoteGenerator`

Rewinds `cur_time` to `start_time` and resets `note_count` to 0, without touching stream state (indices, octave, heap, etc.). An optional `reset_streams=True` parameter resets stream state too (for a full restart).

### 3. Lookahead buffer in `NoteGeneratorThread`

The thread maintains a deque of pre-generated notes covering the next `lookahead_secs` seconds (default: 2.0). Each tick:

1. `_fill_buffer()` — calls `generate_next_note()` until the buffer covers `score_time + lookahead_secs`
2. Dispatch due notes from the front of the buffer (same window logic as current)

Buffer entries are `(start_time_float, note_string)` tuples kept in start-time order.

### 4. Tempo change handling

When `_poll_link()` detects a new BPM:
- Update stream tempos (as now)
- Flush all buffered notes with `start_time > current_score_time` (they were timed at the old BPM)
- Buffer refills automatically from current position at new tempo on the next tick

Worst-case lag = `lookahead_secs`. At the default of 2s, the adjustment is heard within 2 seconds of the tempo change.

### 5. `gen(quantize=...)` in streaming mode

Instead of atomically swapping a pre-baked notes list:
- At the target beat, call `reset_cursor()` on the generator (rewinding `cur_time`)
- Flush the lookahead buffer
- Buffer refills with freshly generated notes from the reset position

No notes-list swap needed. The `_pending_swap` mechanism becomes a pending `reset_cursor()` call.

---

## The Hard Part: Child Generators

Currently child generators run as a separate pass *after* the main loop. In streaming mode their notes must be interleaved into the same buffer in start-time order.

**Phase 1** *(complete)*: streaming mode only for generators with no children (covers all live-coding use cases in csound-pieces). Generators with children fall back to the batch path automatically.

**Phase 2** *(complete — 2026-04-11)*: `_fill_buffer()` uses a min-heap of cursors (parent + all children at any depth). `_init_cursors()` does a recursive tree walk applying limit inheritance and start_time offsets. See `StreamingChildren-Plan.md` for the full design.

---

## Implementation Steps

1. **Extract `generate_next_note()`** from the loop body of `generate_notes()` on `NoteGenerator`. All complexity (chording, post-processes, lambdas) moves into this method. `generate_notes()` becomes a thin wrapper that calls it in a loop.

2. **Add `reset_cursor(reset_streams=False)`** to `NoteGenerator`. Rewinds `cur_time` and `note_count`. When `reset_streams=True`, also resets Itemstream indices and heap state.

3. **Add `_lookahead_secs`, `_buffer`, `_fill_buffer()`** to `NoteGeneratorThread`. `_fill_buffer()` calls `generate_next_note()` until buffer covers `score_time + _lookahead_secs`.

4. **Replace dispatch source** in the run loop: dispatch from `_buffer` instead of `g.notes`.

5. **Update `_poll_link()`**: after updating tempos, flush stale buffer entries (`start_time > score_time`).

6. **Update `gen(quantize=...)`**: pending swap becomes a pending `reset_cursor()` + buffer flush at the target beat. Remove the deep-copy-and-swap mechanism for the streaming path.

7. **Tests**: new test suite `tests/test_streaming.py` covering `generate_next_note()` equivalence with `generate_notes()`, `reset_cursor()` behavior, buffer fill/flush logic, and tempo-change responsiveness.

---

## Backward Compatibility

- `generate_notes()` and the existing notes-list dispatch path are untouched.
- Streaming mode activates when `NoteGeneratorThread` is constructed with `streaming=True` (default: `False` for now; can flip default once validated).
- All existing tests continue to pass.

---

## What This Gives You

| | Batch (current) | Streaming (new) |
|---|---|---|
| Tempo change lag | Full batch duration | ≤ `lookahead_secs` (default 2s) |
| Memory | All notes pre-allocated | Buffer only (small) |
| `gen()` cost | Full `generate_notes()` | Cursor reset + buffer flush |
| Child generators | Full support | Phase 1: fall back to batch |
