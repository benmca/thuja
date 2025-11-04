from thuja.itemstream import notetypes, Itemstream, streammodes
from thuja.streamkeys import keys
from thuja.notegenerator import Line
from thuja import csound_utils

rhythms = Itemstream("q s s s s h".split(),
                     tempo=120,
                     notetype=notetypes.rhythm)

pitches = Itemstream("a4".split(),
                     notetype=notetypes.pitch)


g = (
    Line().with_instr(1)
    .with_rhythm(rhythms)
    .with_duration(.1)
    .with_amps(1)
    .with_freqs(pitches)
)

g.note_limit = len(rhythms.values) * 4
g.gen_lines = ['f 1 0 16384 10 1']

# The rhythms play in expected sequence.
g.generate_notes()
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac0'])
g.clear_notes()

# The rhythms play in a randomish sequence, but no not is repeated until the others play
g.streams[keys.rhythm].streammode = streammodes.heap
g.generate_notes()
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac0'])
g.clear_notes()

# The rhythms play in a completely random sequence, and rhythms may repeat.
g.streams[keys.rhythm].streammode = streammodes.random
g.generate_notes()
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac0'])
