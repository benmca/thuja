from thuja.itemstream import notetypes, Itemstream
from thuja.notegenerator import Line
from thuja import csound_utils

rhythms = Itemstream("e. e. e".split(),
                     tempo=120,
                     notetype=notetypes.rhythm)

pitches = Itemstream("c5 ef f g as c6".split(),
                     notetype=notetypes.pitch)
g = (
    Line().with_instr(1).with_rhythm(rhythms).with_duration(.1).with_amps(1).with_freqs(pitches)
)
g.note_limit = len(pitches.values) * 4
g.gen_lines = ['f 1 0 16384 10 1']

g.generate_notes()
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac0'])
