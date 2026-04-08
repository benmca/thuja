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
5. Change Ableton's tempo mid-performance — Thuja's rhythm streams update automatically within one polling interval (~100ms)

---

## Key Concepts

**Sync point**: recorded when `link_follower.establish_sync(csound_time)` is called. Maps Csound score time to Link beat time. Re-established automatically on every tempo change.

**`gen(quantize=4)`**: regenerates notes and queues the swap to fire at the next 4-beat boundary. `quantize=1` = next beat, `quantize=8` = next 2-bar phrase.

**Target beat**: stored as a Link beat number, not a Csound time. Survives tempo changes — the swap fires at the right musical moment regardless of what happened to tempo between the call and the boundary.

---

## Stopping

Press `Ctrl-C` in the terminal running the example. Csound and the thread will be cleaned up by the interpreter exit.
