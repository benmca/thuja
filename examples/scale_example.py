from thuja.itemstream import notetypes
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.streamkeys import keys
from thuja import csound_utils
from collections import OrderedDict

rhythms = Itemstream("s e s q".split(),
                     tempo=60,
                     notetype=notetypes.rhythm)

pitches = Itemstream("c5 d e f g a b".split(),
                     notetype=notetypes.pitch)

g = Generator(
    streams=OrderedDict([
        (keys.instrument, 1),
        (keys.rhythm, rhythms),
        (keys.duration, .1),
        (keys.amplitude, Itemstream(".5 .25".split())),
        (keys.frequency, pitches),
    ]),
    note_limit=(len(pitches.values)*4),
    gen_lines=[';sine', 'f 1 0 16384 10 1']
)

g.generate_notes()
score_string = g.generate_score_string()
print(score_string)
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-ex.wav', '-W'])
