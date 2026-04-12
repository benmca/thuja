# Streaming Child Generators + Outstanding Cleanup

Plan for the next batch of work on `feature/link-follower` (or successor branch).

---

## Scope

Three work items, in order:

1. **Sync accuracy tests** — unit tests for the new `LinkFollower` features from the 2026-04-11 session. Warmup; no design questions.
2. **Streaming child generators** — Phase 2 of `StreamingGeneration-Plan.md`. The main event.
3. **Issue #27: parent/child limit semantics** — design decision that intersects with (2). Can be resolved as part of (2) or separately.

---

## 1. Sync accuracy tests

Cover the three gaps listed in `tests/todos.md`:

### `latency_offset_secs`

- `current_beat(t)` with offset=0 equals `current_beat(t)` without offset (identity)
- `current_beat(t)` with offset=X returns `current_beat(t + X)` (beat shifted forward)
- `csound_time_for_beat(b)` with offset=X returns `csound_time_for_beat(b) - X` (time shifted earlier)
- Round-trip: `csound_time_for_beat(current_beat(t))` == `t` regardless of offset
- Live-mutable: change offset mid-run, subsequent calls reflect new value immediately

### `establish_sync_via_probe`

Uses the existing mock-socket test infrastructure from `test_link_follower.py`:

- Sends `status\n`, parses reply, anchors `(csound_time, _last_beat, bpm)`
- Drains stale lines in the buffer before sending (inject a pre-queued line, verify it's discarded)
- Prefers latest post-recv line if multiple arrive (inject two lines, verify anchor uses the second)
- Returns RTT in seconds (mock timing)

### `probe_sync`

- Returns 6-tuple: `(model_beat, probe_beat, delta, drained_before, drained_after, rtt)`
- `delta = model_beat - probe_beat`
- Drain counts are correct (inject stale lines, verify counts)
- Fresh status request is sent (verify socket saw `status\n`)

**Estimated effort:** small. All tests use the existing mock-socket pattern.

---

## 2. Streaming child generators

### Current state

- `generate_next_note()` exists on `NoteGenerator` — single cursor, parent only.
- `_fill_buffer()` in `NoteGeneratorThread` calls `generate_next_note()` on the top-level generator only.
- `generate_notes()` (batch) handles children in a *post-loop*: runs each child's `generate_notes()` after the parent finishes, extends the parent's notes list, sorts by start time.
- No code in the streaming path touches `self.g.generators` at all.
- In `csound-pieces`, hierarchies are flat: parent + 2-3 children, never children of children.

### Goal

In streaming mode, parent and all children produce notes into the same lookahead buffer, interleaved by start time. Tempo changes and `gen()` resets apply to all cursors.

### Design

#### Cursor initialization

When `NoteGeneratorThread` starts (or after `gen()` resets), initialize a cursor list:

```
cursors = [parent] + [child for child in parent.generators]
```

Before first use, apply the same limit-inheritance logic that `generate_notes()` does today (lines 305-325 of `notegenerator.py`):
- If `child.generator_dur > 0`: set `child.time_limit = child.start_time + child.generator_dur`
- Else: offset `child.start_time += parent.start_time`
- Inherit parent's `time_limit` / `note_limit` if child's are unset

This happens once at initialization, not per-note.

#### Buffer fill: multi-cursor merge

`_fill_buffer(target_time)` changes from:

```python
while self.g.cur_time < target_time:
    note_str = self.g.generate_next_note()
    ...
```

To a min-heap merge across all active cursors:

```python
import heapq

# heap entries: (cursor.cur_time, cursor_index, cursor)
# cursor_index breaks ties deterministically

while heap:
    next_time, idx, cursor = heapq.heappop(heap)
    if next_time >= target_time:
        heapq.heappush(heap, (next_time, idx, cursor))
        break
    note_str = cursor.generate_next_note()
    if note_str is None:
        continue  # this cursor is exhausted
    start = float(note_str.split()[1])
    self._buffer.append((start, note_str))
    heapq.heappush(heap, (cursor.cur_time, idx, cursor))
```

Notes land in the buffer approximately sorted (each cursor is internally monotonic). A final sort isn't needed because dispatch already scans from the front and only dispatches notes within the dispatch window.

**Edge case: cursor start time in the future.** A child with `start_time=5.0` shouldn't emit notes until `score_time >= 5.0`. The heap naturally handles this: the child's initial `cur_time` is 5.0, so it won't be popped until the fill target reaches 5.0.

**Edge case: chording.** `generate_next_note()` returns one note string per call, even for chords (the chord expands into multiple Event strings in `__str__`). Actually — need to verify this. If chording produces multiple note strings in a single `generate_next_note()` call, we need to handle that. If it returns one call per chord member, the heap works as-is.

#### Maintaining the heap across `_fill_buffer()` calls

The heap must persist between ticks. Store as `self._cursor_heap` on `NoteGeneratorThread`. Initialize it in `_init_cursors()` (new method), called from `run()` startup and from `gen()` reset.

#### Tempo change

`_poll_link()` already calls `_set_generator_tempos()` recursively. After that:
- `_flush_stale_buffer()` (existing) clears notes past `score_time`
- Rebuild the heap from current cursor positions (each cursor retains its `cur_time`)

No cursor reset needed — cursors continue from where they are at the new tempo.

#### `gen()` reset

In streaming mode, `gen()` currently resets the parent cursor and flushes the buffer. With children:
- Reset parent cursor via `reset_cursor()`
- Reset each child cursor via `reset_cursor()`
- Re-apply limit inheritance (child start_time offsets, etc.)
- Rebuild the heap
- Flush the buffer

#### Arbitrary nesting depth

`_init_cursors()` is a recursive tree walk that flattens the entire generator hierarchy into a single cursor list. The heap merge is N-cursor agnostic — it doesn't care about tree structure.

The logic in `generate_notes()` (lines 305-325 of `notegenerator.py`) already handles limit inheritance and start-time offsetting for one level. The recursive version applies the same rules at each level:

- `start_time` offsets accumulate: grandchild's absolute start = grandchild.start_time + child.absolute_start_time
- `time_limit` / `note_limit` inherit from the nearest ancestor that sets them
- `generator_dur` sets `time_limit` relative to the generator's own `start_time` (already absolute by the time it's applied)

```python
def _init_cursors(self):
    """Recursively collect all generators into a flat cursor list."""
    cursors = []
    self._collect_cursors(self.g, cursors)
    # Build heap: (cur_time, index, cursor)
    self._cursor_heap = [(c.cur_time, i, c) for i, c in enumerate(cursors)]
    heapq.heapify(self._cursor_heap)

def _collect_cursors(self, generator, cursors, parent=None):
    """Walk the tree, applying limit inheritance and start_time offsets."""
    if parent is not None:
        if generator.generator_dur > 0:
            generator.time_limit = generator.start_time + generator.generator_dur
        else:
            generator.start_time += parent.start_time
        if parent.time_limit > 0 and generator.time_limit == 0:
            generator.time_limit = parent.time_limit
        if parent.note_limit > 0 and generator.note_limit == 0:
            generator.note_limit = parent.note_limit
    cursors.append(generator)
    for child in generator.generators:
        self._collect_cursors(child, cursors, parent=generator)
```

This gives arbitrary depth for free. `csound-pieces` currently uses at most 2 levels, but there's no reason to cap it. Test suite includes a 3-level case to verify offset chaining and limit inheritance cascade.

The main risk area is `generator_dur` interacting with `start_time` offsets at depth > 1 — the absolute-vs-relative semantics are already tricky at one level (see the comment block at line 306 of `notegenerator.py`). The recursive walk must apply offsets parent-first, top-down, so each child sees its parent's already-resolved absolute `start_time`. The code above does this naturally via depth-first traversal with `parent` passed down.

---

## 3. Issue #27: parent/child limit semantics

### Current behavior

Parent `time_limit` and `note_limit` are *defaults* inherited by children when children's own limits are unset. But parent limits don't *constrain* children — a child can generate notes past the parent's `time_limit`, and `score_dur` reflects the child's actual duration.

### The question

Should parent limits be **hard constraints** (child notes past the parent limit are discarded) or **defaults** (current behavior)?

### Recommendation: keep defaults, add optional hard constraint

Current behavior matches every real composition in `csound-pieces` — no one is relying on parent limits to truncate children. Changing to hard constraints risks breaking existing work.

However, for streaming child generators, the question becomes practical: when should a child cursor stop? If the parent has `time_limit=10` and the child inherits it, the child's cursor stops at 10 — that's the current default-inheritance behavior, and it works fine for streaming.

The only gap is if a child has its *own* `time_limit` that exceeds the parent's. In batch mode, those notes are included. In streaming mode, they'd also be included (the child cursor runs until its own limit). This is consistent.

**Proposed resolution:** document the current semantics explicitly. No code change for now. If a "hard constraint" mode is wanted later, add a `constrain_children=False` flag on `NoteGenerator` rather than changing default behavior.

This unblocks streaming child generators without a breaking change.

---

## Implementation order

### Step 1: Sync accuracy tests
- Branch: `test/sync-accuracy` (or work on master if preferred)
- Add tests to `tests/test_link_follower.py`
- Update `tests/todos.md`: move items to "Already Covered"
- Small PR

### Step 2: Streaming child generators
- Branch: new feature branch off master
- New method: `NoteGeneratorThread._init_cursors()` — builds cursor list + heap
- Modify: `_fill_buffer()` — multi-cursor heap merge
- Modify: `gen()` streaming path — reset all cursors, rebuild heap
- Modify: `_poll_link()` — rebuild heap after tempo change
- New tests in `test_streaming.py`: child generators in streaming mode
  - Parent + 1 child: interleaved notes in start-time order
  - Parent + child with offset start_time: child notes don't appear before offset
  - 3-level nesting: parent → child → grandchild, start_time offsets chain correctly
  - 3-level limit inheritance: grandchild inherits from child, which inherits from parent
  - Tempo change with children: all rhythm streams updated, buffer flushed, regeneration correct
  - `gen()` reset with children: all cursors reset (full tree)
  - Child with `generator_dur`: respects relative duration
  - Child with own `time_limit`: not truncated by parent (documenting current semantics)
  - Equivalence: streaming output matches batch `generate_notes()` output for same generator tree
- Update `StreamingGeneration-Plan.md`: mark Phase 2 complete, document design decisions
- Update `HISTORY.md`, `tests/todos.md`

### Step 3: Issue #27 documentation
- Add docstring/comment in `generate_notes()` and `_init_cursors()` explicitly stating: "parent limits are defaults, not constraints"
- Close or update issue #27 on GitHub with the decision rationale
- No code change beyond documentation

---

## Out of scope (this batch)

- Link start/stop sync (Phase 2 of LinkFollower-Plan.md)
- Bug #40 (rest amplitude)
- Compiled Link binding
- Lower-priority test gaps (string args, heap edge case, generate_score, etc.)
