"""
link_follower_ex.py — Ableton Link tempo following with a NoteGeneratorThread.

Requires:
  - Csound installed
  - carabiner running on localhost:17000  (brew install carabiner, then: carabiner)
  - Ableton Live (or any Link-enabled app) open with Link enabled

See examples/LinkFollower-GettingStarted.md for full setup instructions.
"""

import time
from thuja.itemstream import streammodes, notetypes, Itemstream
from thuja.notegenerator import Line, kickoff
from thuja.link_follower import LinkFollower

# ---------------------------------------------------------------------------
# Generator — based on examples/thuja_ex.py
# ---------------------------------------------------------------------------

pitches = Itemstream('a2 b c3 e a2 r e2 f r b'.split() + [['e', 'b']] + [['e', 'b']]
                     + 'a2 c3 c c d d d e r e'.split() + [['e', 'b']] + [['e', 'b']],
    streammode=streammodes.sequence,
    notetype=notetypes.pitch
)

rhythms = Itemstream('s s s s e e'.split(),
                     streammode=streammodes.sequence,
                     tempo=120,          # overridden at runtime by LinkFollower
                     notetype=notetypes.rhythm)

g = (
    Line().with_instr(2)
    .with_rhythm(rhythms)
    .with_duration(.1)
    .with_amps(1)
    .with_freqs(pitches)
    .with_pan(45)
    .with_dist(10)
    .with_percent(.1)
)

g.note_limit = len(pitches.values) * 4

g.gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']

g.generate_notes()

# ---------------------------------------------------------------------------
# Connect to Ableton Link via carabiner
# ---------------------------------------------------------------------------

lf = LinkFollower(host='localhost', port=17000, quantum=4)
lf.connect()
print("Connected to Link session. BPM: " + str(lf.bpm))

# ---------------------------------------------------------------------------
# Start Csound and the generator thread
#
# kickoff() starts Csound, establishes the Link sync point, creates a
# NoteGeneratorThread with the follower attached, and starts it.
# ---------------------------------------------------------------------------

t = kickoff(g, 'sine+moog.orc', device_string='dac0', link_follower=lf)

print("Playing. Tempo follows Link automatically.")
print("Change Ableton's tempo to hear Thuja adapt.")

# ---------------------------------------------------------------------------
# Demo: quantized note swap after 8 seconds
# ---------------------------------------------------------------------------

time.sleep(8)

print("Queuing a note swap at the next bar boundary (quantize=4)...")
t.gen(quantize=4)   # new notes swap in at the next 4-beat (1-bar) boundary

# ---------------------------------------------------------------------------
# Run until interrupted
# ---------------------------------------------------------------------------

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Stopping.")
