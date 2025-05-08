from thuja.itemstream import notetypes
from thuja.itemstream import streammodes
from thuja.itemstream import Itemstream
from thuja.notegenerator import NoteGenerator
from thuja.streamkeys import keys
from thuja import csound_utils
import copy

rhythms = Itemstream(
    # '12 12 12 12 12 12 e. e. e q. e q. e q q'.split()+['s']*16,
    ['12']*4+['6']*4,
    streammode=streammodes.sequence,
    tempo=120,
    notetype=notetypes.rhythm)

amps = Itemstream([1])

pitches = Itemstream(sum([
    ['c4','c','c','d','c5','c','c','d'],
    ['c3','e',['c','e','g'],'c4','e',['c','e','g']],
    [['c','e','g'],['c','e','g'],['c','d','e'],['e','f','g']],
    ],[]),
    streammode=streammodes.heap,
    notetype=notetypes.pitch
)

g = NoteGenerator(
    streams=[
        (keys.instrument, 1),
        (keys.rhythm, rhythms),
        (keys.duration, Itemstream([.1])),
        (keys.amplitude, .25),
        (keys.frequency, pitches)
    ],
    pfields=None,
    gen_lines=[';sine',
               'f 1 0 16384 10 1']
)
g.time_limit=60

g2 = copy.deepcopy(g)
g2.streams[keys.rhythm] = Itemstream(['e'],'sequence', tempo=120, notetype=notetypes.rhythm)
g2.streams[keys.frequency] = Itemstream([['c5','d','e'],'g3']*4+['f5','c3']*4+[['c5','d','e'],'g3']*4+['g5','d3']*4,notetype=notetypes.pitch)
# g2.streams[keys.amplitude] = Itemstream([.33])
g.add_generator(g2)

g3 = copy.deepcopy(g2)
g.add_generator(g3)
g.generate_notes()


csound_utils.play_csound("sine.orc", g, args_list=['-odac0', 'W'])