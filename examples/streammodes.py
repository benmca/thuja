from thuja.itemstream import notetypes, Itemstream, streammodes
from thuja.streamkeys import keys
from thuja.notegenerator import Line
from thuja import csound_utils

rhythms = Itemstream("q e. s s s s. 32".split(),
                     tempo=80,
                     notetype=notetypes.rhythm)

pitches = Itemstream("c5 d e f g a b".split(),
                     notetype=notetypes.pitch)


g = (
    Line().with_instr(1)
    .with_rhythm(rhythms)
    .with_duration(.1)
    .with_amps(1)
    .with_freqs(pitches)
)

g.note_limit = len(pitches.values) * 4
g.gen_lines = ['f 1 0 16384 10 1']

g.generate_notes()
print('rhythms in sequence')
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac0'])
g.clear_notes()

g.streams[keys.rhythm].streammode = streammodes.heap
g.generate_notes()
print('rhythms in heap')
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac0'])
g.clear_notes()

g.streams[keys.rhythm].streammode = streammodes.random
g.generate_notes()
print('rhythms in random')
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac0'])
