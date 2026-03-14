# LinkFollower: Ableton Link Sync for NoteGeneratorThread

## Goal

Thuja follows Ableton Link — Link sets tempo, thuja adjusts. Eventually: quantized regeneration aligned to beat/bar/multi-bar boundaries.

---

## The Core Timing Problem

Link operates on its own beat clock (microseconds since session start, mapped to beats). Csound operates on score time (seconds since `t.start()`). To make these work together you need a **sync point**: the Csound score time and Link beat position at the moment you establish the connection. Everything else is derived from that offset + current BPM.

```
csound_time_for_beat(b) = sync_csound_time + (b - sync_link_beat) * (60 / bpm)
```

---

## Two Phases

**Phase 1: Tempo following**
- Poll Link for current BPM
- On change: update `Itemstream.tempo` on all active streams, call `t.gen()` to rebake note times
- Simple, useful immediately

**Phase 2: Quantized regeneration**
- Instead of `t.gen()` swapping notes immediately, it waits until the next bar/multi-bar boundary (expressed in Csound score time) before the swap
- The lock in `gen()` already handles the atomic swap — you'd just delay *when* you acquire it

---

## Library Options

Three realistic paths:

| Option | How it works | Pros | Cons |
|---|---|---|---|
| **carabiner** | Separate bridge process; talk to it over TCP | No compilation, battle-tested in live coding community (Overtone, etc.) | Requires running a second process |
| **pylinkwrap** | Python bindings wrapping the Link C++ SDK | Single process, direct | Requires compiling native extension |
| **python-ableton-link** | Another binding approach | Similar to above | Less maintained |

**Recommendation**: Start with carabiner — stable, no compilation, and easy to prototype against. Switch to a compiled binding later if the extra process is a problem.

---

## Proposed Architecture

```
LinkFollower (new class)
├── Connects to carabiner (or Link SDK)
├── Polls/subscribes to BPM changes
├── Maintains sync_point (csound_time, link_beat, bpm) at connection time
├── on_tempo_change(new_bpm):
│     update all generator stream tempos
│     schedule gen() at next quantum boundary
└── beat_to_csound_time(beat) → float
```

`NoteGeneratorThread.gen()` gets a `quantize=None` parameter:
- `quantize=None` → immediate (current behavior)
- `quantize='beat'` → wait for next beat boundary
- `quantize='bar'` → wait for next 4-beat boundary
- `quantize=8` → wait for next 8-beat boundary

---

## Implementation Plan

1. Get carabiner running and verify BPM can be read from Python via TCP socket
2. Build `LinkFollower` as a standalone class (no thuja dependency) exposing `current_bpm` and `beat_to_csound_time()`
3. Wire into `NoteGeneratorThread` minimally — tempo following only, no quantization yet
4. Add quantized `gen()` as Phase 2
