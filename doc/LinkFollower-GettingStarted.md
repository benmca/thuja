# LinkFollower Getting Started Guide

Play a Thuja generator in sync with an Ableton Link session. Ableton (or any other Link-enabled app) drives tempo; Thuja follows automatically.

---

## Prerequisites

- **Csound** installed — https://csound.com/download.html
- **Python dependencies** installed — `pip install -r requirements.txt`
- **Ableton Live** (or any Link-enabled app) open with a session running
- **Link enabled** in Ableton: *Preferences → Link/Tempo/MIDI → Link: ON*
- **carabiner** installed (see below)

---

## Install and Start carabiner (macOS)

carabiner is a small bridge process that exposes your Mac's Ableton Link session over a local TCP socket. Thuja connects to it on port 17000.

### Install via Homebrew

```bash
brew install carabiner
```

If Homebrew doesn't have it, build from source - but double-check this from in the [carabiner repo readme](https://github.com/Deep-Symmetry/carabiner):

```bash
git clone https://github.com/Deep-Symmetry/carabiner.git
cd carabiner
mkdir build
cd build
cmake ..
cmake --build .
```

### Start carabiner

Open a terminal and run:

```bash
Carabiner
```

You should see output like:

```
Carabiner version 1.1.2
Listening on port 17000
```

Leave this terminal open while you work. Thuja will connect to it automatically when you run the example.

---

## Verify Link is Active

With carabiner running and Ableton Link enabled, open a second terminal and run:

```bash
nc localhost 17000
```

Type `status` and press Enter. You should receive a status line like:

```
status { :peers 1 :bpm 120.000000 :start 285332905719 :beat 4.000000 }
```

The `bpm` value should match what Ableton shows. Press `Ctrl-C` to exit.

---

## Run the Example

The example file is `examples/link_follower_ex.py`. It uses `sine.orc` (a simple sine-wave instrument) and starts a `NoteGeneratorThread` linked to the current Ableton session tempo, then demonstrates a quantized note swap.

```bash
cd examples
python link_follower_ex.py
```

### What to expect

1. Thuja connects to carabiner and prints the current BPM
2. The generator starts playing at that tempo
3. After 8 seconds, `gen(quantize=4)` is called — a new set of notes is queued to swap in at the next 4-beat (1-bar) boundary
4. You'll see `Swap queued at beat X` in the terminal when the swap is scheduled
5. Change Ableton's tempo mid-performance — Thuja's rhythm streams update automatically within `lookahead_secs` (default 2s)

---

## Key Concepts

**Streaming mode** (`streaming=True` passed to `kickoff`): notes are generated on demand into a short lookahead buffer (default 2s) rather than pre-baked. Tempo changes take effect within `lookahead_secs` because only the buffered notes need to be flushed and regenerated.

**Sync point**: recorded when `link_follower.establish_sync_via_probe(csound_time_fn)` is called. Maps Csound score time to Link beat time. Unlike the passive `establish_sync()`, the "via probe" variant sends a fresh `status\n` request to carabiner and anchors against the reply — this avoids stale-line errors where a pushed status update had been in-flight for an unknown time. Re-anchoring happens automatically in `kickoff` (initial sync) and on every tempo change detected by `_poll_link`.

**`gen(quantize=4)`**: regenerates notes and queues the swap to fire at the next 4-beat boundary. `quantize=1` = next beat, `quantize=8` = next 2-bar phrase.

**Target beat**: stored as a Link beat number, not a Csound time. Survives tempo changes — the swap fires at the right musical moment regardless of what happened to tempo between the call and the boundary.

**Latency offset** (`latency_offset_secs` on `LinkFollower`): a fixed wall-time shift applied to all beat/time conversions. Positive values move notes *earlier* in wall time, compensating for the audio output chain (Csound buffers + driver + DAC). Live-tunable — assign to `lf.latency_offset_secs` mid-performance. See *Notes on calculating latency* below.

---

## Quantum and time signature

`LinkFollower(quantum=4)` tells Thuja how many beats make a bar. This is used by `quantize='bar'` to align generators with Ableton's bar downbeats.

**Important:** the Ableton Link protocol does not transmit time signature. Ableton lets you set the denominator (2, 4, 8, 16) but Link only shares tempo, beat count, and phase. The `quantum` parameter must be set manually to match your Ableton session:

| Ableton time sig | quantum |
|---|---|
| 4/4 | 4 (default) |
| 3/4 | 3 |
| 6/8 | 6 |
| 5/4 | 5 |
| 7/8 | 7 |

If quantum doesn't match Ableton's time signature, `quantize='bar'` will land on the wrong beat. `quantize='beat'` (quantum=1) is unaffected.

You can change quantum at runtime: `lf.quantum = 3`. The next `add_generator(quantize='bar')` or `gen(quantize='bar')` call will use the new value.

---

## Notes on calculating latency

Even with a perfectly accurate sync model, notes sound late because the audio pipeline after Csound's score engine takes time to reach the speakers. The `latency_offset_secs` field on `LinkFollower` is how you compensate.

For the default `link_follower_ex.py` setup (Csound with `-b 1024 -B 4096` at 44100 Hz on macOS built-in output) a value around **`0.15`** feels right by ear. Here's where that number comes from.

### Where the latency comes from

Csound renders audio in three stages:

1. **`ksmps` chunks** — tiny (default 10 samples, ~0.2 ms). Negligible.
2. **Software buffer `-b`** — Csound accumulates ksmps chunks here before flushing to the driver.
3. **Hardware buffer `-B`** — the driver-owned ring buffer the DAC reads from.

A sample that Csound emits has to traverse the software buffer and then wait in the hardware buffer before it becomes audible. Worst-case:

```
csound_latency_secs = (b_samples + B_samples) / sample_rate
```

For the defaults (`-b 1024 -B 4096` at 44100 Hz):

```
(1024 + 4096) / 44100 ≈ 0.116 s
```

That's ~116 ms just from Csound's own buffering.

### Driver / output latency

Beyond Csound's buffers, the rest of the output chain adds more:

- **CoreAudio driver scheduling**: ~10 ms
- **DAC conversion + output path**: a few ms
- **Speaker DSP** (built-in Mac speakers do some light processing): a few more ms
- **Bluetooth output**: *much* worse — often 100–250 ms on top

For built-in speakers or a wired interface, figure **~30–40 ms** of post-Csound latency. Bluetooth requires far more and is not recommended for live-coding.

### Putting it together

```
latency_offset_secs ≈ (b_samples + B_samples) / sample_rate + driver_output_latency
                   ≈ (1024 + 4096) / 44100 + ~0.035
                   ≈ 0.151 s
```

Which matches what sounds right by ear with the example's defaults.

### Tuning for your setup

The buffer term is fully predictable from your Csound command-line flags. The driver term is the unknown — it depends on your output device and OS. The manual tuning approach:

1. Compute the buffer term from your `-b` and `-B` values and sample rate.
2. Start with `latency_offset_secs = buffer_term + 0.03` and play.
3. If notes still sound late, bump up in ~5 ms increments. If they sound rushed (ahead of the Link grid), dial back.
4. Once tuned, the value is stable for that device / sample rate / buffer size combination.

If you change `-b`, `-B`, or the sample rate, recalculate — the buffer term is the dominant component.

### Quick reference

| -b | -B | SR | buffer latency |
|---|---|---|---|
| 256 | 1024 | 44100 | ~29 ms |
| 512 | 2048 | 44100 | ~58 ms |
| 1024 | 4096 | 44100 | ~116 ms |
| 256 | 1024 | 48000 | ~27 ms |
| 1024 | 4096 | 48000 | ~107 ms |

Add ~30–40 ms for the driver term (or more for Bluetooth).

---

## Stopping

Press `Ctrl-C` in the terminal running the example. Csound and the thread will be cleaned up by the interpreter exit.
