from thuja.itemstream import notetypes
from thuja.itemstream import streammodes
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
from collections import OrderedDict
from thuja import csound_utils
import copy

rhythms = Itemstream(sum([
    'e. e. e q. e q. e h'.split(),
    ['s']*20,
    ],[]
    ),
    streammode=streammodes.sequence,
    tempo=120,
    notetype=notetypes.rhythm)

pitches = Itemstream(sum(['c4 c c d c5 c c d'.split(),
    ['c3','e',['c','e','g'],'c4','e',['c','e','g']],
    [['c','e','g'],['c','e','g'],['c','d','e'],['e','f','g']],
    ],[]),
    streammode=streammodes.heap,
    notetype=notetypes.pitch
)

g = Generator(
    streams=OrderedDict([
        (keys.instrument, 1),
        (keys.rhythm, rhythms),
        (keys.duration, Itemstream([.1])),
        (keys.amplitude, 1),
        (keys.frequency, pitches),
    ]),
    pfields=None,
    note_limit=(len(pitches.values)*4),
    gen_lines=[';sine',
               'f 1 0 16384 10 1']
)

g2 = copy.deepcopy(g)
g2.streams[keys.rhythm] = Itemstream('e','sequence', tempo=120, notetype=notetypes.rhythm)
g2.streams[keys.frequency] = Itemstream([['c5','d','e'],'g3']*4+['f5','c3']*4+[['c5','d','e'],'g3']*4+['g5','d3']*4,
                                        notetype=notetypes.pitch)
g2.note_limit = 64
g.add_generator(g2)
g.generate_notes()

score_string = g.generate_score_string()
csound_utils.play_csound("sine.orc", g, silent=True)
