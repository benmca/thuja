from thuja.itemstream import notetypes, Itemstream
from thuja.notegenerator import NoteGenerator
from thuja.streamkeys import keys
from collections import OrderedDict
from thuja import csound_utils

rhythms = Itemstream("s e s q".split(),
                     tempo=60,
                     notetype=notetypes.rhythm)

pitches = Itemstream("a3 b c4 d e".split(),
                     notetype=notetypes.pitch)


g = NoteGenerator(
    streams=OrderedDict([
        (keys.instrument, 1),
        (keys.rhythm, rhythms),
        (keys.duration, .1),
        (keys.amplitude, Itemstream([1,.5], notetype=notetypes.number)),
        (keys.frequency, pitches),
    ]),
    note_limit=5,
    gen_lines=['f 1 0 16384 10 1']
)

g.generate_notes()
# score_string = g.generate_score_string()
# print(score_string)

csound_utils.play_csound("sine.orc", g, args_list=['-odac0', 'W'])