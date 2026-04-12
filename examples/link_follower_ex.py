"""
link_follower_ex.py — Ableton Link tempo following with a NoteGeneratorThread.

Requires:
  - Csound installed
  - carabiner running on localhost:17000
  - Ableton Live (or any Link-enabled app) open with Link enabled

See doc/LinkFollower-GettingStarted.md for full setup instructions.
"""

import sys
import time
import traceback

def log(msg):
    print("[link_follower_ex] " + msg, flush=True)

log("Script starting.")
log("Python: " + sys.version)

# ---------------------------------------------------------------------------
# Imports — log each so we can catch any import failure
# ---------------------------------------------------------------------------

log("Importing thuja modules...")
try:
    from thuja.itemstream import streammodes, notetypes, Itemstream
    from thuja.notegenerator import Line, kickoff
    from thuja.link_follower import LinkFollower
    log("Imports OK.")
except Exception as e:
    log("IMPORT ERROR: " + str(e))
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

log("Building generator...")

pitches = Itemstream('a2 b c3 e a2 r e2 f r b'.split() + [['e', 'b']] + [['e', 'b']]
                     + 'a2 c3 c c d d d e r e'.split() + [['e', 'b']] + [['e', 'b']],
    streammode=streammodes.sequence,
    notetype=notetypes.pitch
)

rhythms = Itemstream('s s s s e e'.split(),
                     streammode=streammodes.sequence,
                     tempo=120,
                     notetype=notetypes.rhythm)

g = (
    Line().with_instr(1)
    .with_rhythm(rhythms)
    .with_duration(.1)
    .with_amps(1)
    .with_freqs(pitches)
)

log("Generator ready.")
# ---------------------------------------------------------------------------
# Connect to Ableton Link via carabiner
# ---------------------------------------------------------------------------

log("Connecting to carabiner on localhost:17000...")
try:
    # latency_offset_secs: positive value shifts notes earlier in wall time.
    # Tune by ear. Adjust live via `lf.latency_offset_secs = N`.
    lf = LinkFollower(host='localhost', port=17000, quantum=4,
                      latency_offset_secs=0.15)
    lf.connect()
    log("Connected. BPM=" + str(lf.bpm) + "  last_beat=" + str(lf._last_beat))
except Exception as e:
    log("CARABINER CONNECTION ERROR: " + str(e))
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------------------------------
# Start Csound and the generator thread
# ---------------------------------------------------------------------------

log("Starting Csound...")
try:
# sine.orc uses only instr 1 (p3=dur, p4=amp, p5=freq) and f1 (sine wave).
# A long silent i1 event keeps Csound alive so the thread can send notes.
    t = kickoff(g, 'sine.orc',
            scorestring='f1 0 16384 10 1\ni1 0 7200 0 440\n',
            device_string='dac0',
            link_follower=lf,
            streaming=True)
    log("Csound started. Thread running.")
except Exception as e:
    log("CSOUND START ERROR: " + str(e))
    traceback.print_exc()
    sys.exit(1)

log("Playing. Tempo follows Link automatically.")
log("Change Ableton's tempo to hear Thuja adapt.")

# ---------------------------------------------------------------------------
# Demo: quantized note swap after 8 seconds
# ---------------------------------------------------------------------------

time.sleep(8)

log("Queuing note swap at next bar boundary (quantize=4)...")
try:
    t.gen(quantize=4)
except Exception as e:
    log("GEN ERROR: " + str(e))
    traceback.print_exc()

# ---------------------------------------------------------------------------
# Run until interrupted
# ---------------------------------------------------------------------------

log("Running. Press Ctrl-C to stop.")
try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    log("Stopping.")
