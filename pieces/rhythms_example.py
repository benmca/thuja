from thuja.itemstream import notetypes
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
from collections import OrderedDict
from thuja import csound_utils

rhythms = Itemstream("q q. e. s. h e+q 32",
                     tempo=120,
                     notetype=notetypes.rhythm)

pitches = Itemstream("c5 d e f g a b",
                     notetype=notetypes.pitch)

g = Generator(
    streams=OrderedDict([
        (keys.instrument, 1),
        (keys.rhythm, rhythms),
        (keys.duration, .1),
        (keys.amplitude, 1),
        (keys.frequency, pitches),
    ]),
    note_limit=(len(pitches.values)*4),
    gen_lines=[';sine', 'f 1 0 16384 10 1']
)

g.generate_notes()
score_string = g.generate_score_string()
print(score_string)
csound_utils.play_csound("sine.orc", g, silent=True)
