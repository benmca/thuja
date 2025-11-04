from thuja.itemstream import streammodes, notetypes, Itemstream
from thuja.notegenerator import Line
from thuja import csound_utils

rhythms = Itemstream('s s e q'.split(),
                     streammode=streammodes.sequence,
                     notetype=notetypes.rhythm)
amps = Itemstream(1)

pitches = Itemstream('a2 a e3 a2 g'.split(),
    streammode=streammodes.sequence,
    notetype=notetypes.pitch
)

g = (
    Line().with_instr(1)
    .with_rhythm(rhythms)
    .with_duration(.1)
    .with_amps(1)
    .with_freqs(pitches)
)

g.note_limit = len(pitches.values) * 4
g.gen_lines = [';sine\n',
             'f 1 0 16384 10 1\n',
             ';saw',
             'f 2 0 256 7 0 128 1 0 -1 128 0\n',
             ';pulse\n',
             'f 3 0 256 7 1 128 1 0 -1 128 -1\n']

g.generate_notes()
print(g.generate_score_string())
csound_utils.play_csound("sine+moog.orc", g, silent=True, args_list=['-odac', '-W'])
