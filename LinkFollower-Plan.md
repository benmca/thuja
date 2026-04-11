# LinkFollower: Ableton Link Sync for NoteGeneratorThread

## Goal

Thuja follows Ableton Link — Link sets tempo, thuja adjusts. Phase 2 adds quantized note regeneration that snaps to beat/bar/multi-bar boundaries in Link beat time.

---

## Terminology

| Term | Definition |
|---|---|
| **Link session** | A group of peers sharing a timeline. There is no single authoritative peer — all are equal. |
| **Beat time** | Monotonic, continuous clock in beats. Keeps running across tempo changes. Never resets. |
| **Tempo** | Beats per minute. Any peer can propose a new tempo; Link propagates it to all peers. |
| **Quantum** | The number of beats in one "bar" for phase alignment. Typically 4. |
| **Phase** | Beat time modulo quantum. Used for quantized alignment. |

In Thuja's typical use: Ableton Live is one peer; Thuja is another. Thuja never proposes tempo — it follows whatever the session BPM is.

---

## The Core Timing Problem

Link operates on its own beat clock. Csound operates on score time (seconds since `NoteGeneratorThread.start()`). To bridge them, you need a **sync point** recorded at the moment the connection is established:

```
sync_point = (sync_csound_time, sync_link_beat, sync_bpm)
```

All conversions derive from that offset:

```
current_beat()  = sync_link_beat + (csound_now - sync_csound_time) * (sync_bpm / 60)
csound_time_for_beat(b) = sync_csound_time + (b - sync_link_beat) * (60 / sync_bpm)
```

**Critical**: on every tempo change, `establish_sync()` must be called to record a new sync point before the old BPM is overwritten. The new sync point captures the current Csound time and current Link beat at the exact moment the BPM changes. This keeps beat-to-csound-time conversions consistent.

---

## The Quantized Swap: `target_beat`, not `target_csound_time`

When `gen(quantize='bar')` is called, the thread must wait until the next bar boundary before swapping in new notes. The naive implementation stores the target as a Csound time:

```python
# WRONG: target_csound_time breaks on tempo change
target_csound_time = csound_time_for_beat(next_bar_beat)
```

This breaks because if tempo changes before the swap fires, the pre-computed Csound time no longer corresponds to the bar boundary.

**Correct implementation**: store `target_beat` (the Link beat number of the next boundary). Each tick, recompute `current_beat()` live from the sync point and compare:

```python
# CORRECT
target_beat = next_bar_beat(quantum=4)   # Link beat number

# in run loop, each tick:
if self._pending_swap and current_beat() >= self._pending_swap.target_beat:
    self._do_swap()
```

Because `current_beat()` is always derived from the *current* sync point and *current* BPM, it stays accurate across tempo changes. `target_beat` is a position on the Link timeline — it never needs to be recomputed.

---

## Library: carabiner

Talk to Ableton Link via the **carabiner** bridge process over TCP on port 17000. Protocol is s-expressions.

**Pros**: no compilation, battle-tested in live coding community (Overtone, Sonic Pi, etc.)  
**Cons**: requires running `carabiner` as a separate process before Thuja starts

Example session:
```
→ connect
← (status bpm 120.000 beat 0.000 phase 0.000 metro (0.000 0.000))
→ (bpm 140.0)
← (status bpm 140.000 ...)
```

Switch to a compiled binding (`pylinkwrap`) later if the extra process becomes a problem.

---

## `LinkFollower` Class (new file: `thuja/link_follower.py`)

```python
class LinkFollower:
    def __init__(self, host='localhost', port=17000, quantum=4):
        ...

    def connect(self):
        """Open TCP socket to carabiner, receive status, establish sync point."""

    def disconnect(self):
        """Close socket cleanly."""

    def establish_sync(self, csound_time):
        """Record (csound_time, current_link_beat, current_bpm) as sync point.
        Must be called after connect() and after every tempo change."""

    def current_beat(self, csound_time):
        """Live calculation: sync_link_beat + (csound_time - sync_csound_time) * bpm/60"""

    def csound_time_for_beat(self, beat):
        """sync_csound_time + (beat - sync_link_beat) * 60/bpm"""

    def next_boundary(self, csound_time, quantum=None):
        """Next beat boundary at or after current_beat(csound_time).
        quantum=1 → next beat; quantum=4 → next bar; quantum=8 → next 2 bars."""

    def poll(self):
        """Check carabiner for a new BPM. Returns new BPM if changed, else None.
        Non-blocking: reads pending data if available, returns immediately."""

    @property
    def bpm(self):
        """Current BPM as last reported by carabiner."""

    @property
    def connected(self):
        """True if socket is open."""
```

---

## `NoteGeneratorThread` Modifications (in `thuja/notegenerator.py`)

### Constructor

```python
def __init__(self, generator, orc_file, link_follower=None, ...):
    self.link_follower = link_follower
    self._pending_swap = None   # namedtuple(notes, target_beat)
```

### `gen(quantize=None)`

```python
def gen(self, quantize=None):
    """Regenerate notes.
    quantize=None  → immediate (current behavior)
    quantize=1     → next beat
    quantize=4     → next bar (4 beats)
    quantize=8     → next 8-beat boundary
    'beat'/'bar'   → aliases for 1/4
    """
    new_notes = self.generator.generate_notes()
    if quantize is None or self.link_follower is None:
        with self._lock:
            self._notes = new_notes
    else:
        q = {'beat': 1, 'bar': 4}.get(quantize, quantize)
        target = self.link_follower.next_boundary(self._csound_time(), quantum=q)
        self._pending_swap = _PendingSwap(notes=new_notes, target_beat=target)
```

### Run loop additions

```python
# tempo following
if self.link_follower and self.link_follower.connected:
    new_bpm = self.link_follower.poll()
    if new_bpm is not None:
        self.link_follower.establish_sync(self._csound_time())
        self._update_tempos(new_bpm)

# quantized swap
if self._pending_swap:
    if self.link_follower.current_beat(self._csound_time()) >= self._pending_swap.target_beat:
        with self._lock:
            self._notes = self._pending_swap.notes
            self._pending_swap = None
```

### `_update_tempos(bpm)`

Walk all Itemstreams in `self.generator` (recursively through child generators) and set `.tempo = bpm` on each rhythm-notetype stream.

---

## Test Plan

All tests mock the carabiner socket — no live Link session required.

| # | Test name | What it verifies |
|---|---|---|
| 1 | `test_connect_parses_status` | `connect()` sends "connect", parses BPM/beat from status response |
| 2 | `test_establish_sync` | `establish_sync(t)` stores `(t, beat, bpm)` correctly |
| 3 | `test_current_beat_math` | `current_beat(t)` = sync_beat + (t - sync_t) * bpm/60 |
| 4 | `test_csound_time_for_beat_math` | Inverse of current_beat |
| 5 | `test_current_beat_survives_tempo_change` | After tempo change + re-sync, current_beat() is still correct |
| 6 | `test_next_boundary_beat` | quantum=1 → next whole beat |
| 7 | `test_next_boundary_bar` | quantum=4 → next multiple of 4 |
| 8 | `test_poll_returns_none_when_no_change` | poll() returns None when BPM unchanged |
| 9 | `test_poll_returns_bpm_on_change` | poll() returns new BPM when carabiner sends updated status |
| 10 | `test_thread_updates_tempo_on_poll` | NoteGeneratorThread run loop calls _update_tempos when poll returns new BPM |
| 11 | `test_gen_quantize_fires_at_target_beat` | _pending_swap fires when current_beat >= target_beat |
| 12 | `test_gen_quantize_target_beat_survives_tempo_change` | target_beat unchanged after tempo change; swap still fires at correct musical moment |

---

## Backward Compatibility

All changes to `NoteGeneratorThread` are additive with `None` defaults. When `link_follower` is not provided, every new code path is unreachable — existing behavior is identical to today. No existing call sites require changes.

---

## Implementation Order

1. **`thuja/link_follower.py`** — standalone, no thuja dependency. Implement `connect`, `establish_sync`, `current_beat`, `csound_time_for_beat`, `next_boundary`, `poll`. Write tests 1–9 against a mock socket.

2. **`tests/test_link_follower.py`** — all 12 tests, initially skipped for NoteGeneratorThread tests (10–12).

3. **`NoteGeneratorThread.__init__`** — add `link_follower` param, `_pending_swap` attr.

4. **`NoteGeneratorThread.gen()`** — add `quantize` param; write `_pending_swap` when quantize is set.

5. **Run loop** — add tempo-following poll + quantized swap check. Enable tests 10–12.

---

## Out of Scope

- Thuja proposing tempo changes to the Link session (Thuja is follower-only)
- Phase alignment across multiple Thuja generators (one follower per session is enough)
- **Start/stop sync** — responding to Link transport start/stop signals (Phase 2)
- **Carabiner process management** — starting/stopping carabiner from Python; user must launch the bridge before Thuja
- **Compiled Link binding** — switching from carabiner to `pylinkwrap` or similar; architecture makes this a one-file swap in `link_follower.py` when needed
- NoteGeneratorThread without ctcsound — integration tests still require live Csound
