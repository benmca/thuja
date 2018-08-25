from thuja.itemstream import notetypes
from thuja.itemstream import streammodes
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
from collections import OrderedDict
from thuja import utils
import copy
import csnd6

rhythms = Itemstream(sum([
    ['e.','e.','e','q.','e','q.','e','h'],
    ['s']*20,
    ],[]
    ),
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

g = Generator(
    streams=OrderedDict([
        (keys.instrument, 1),
        (keys.rhythm, rhythms),
        (keys.duration, Itemstream([.1])),
        (keys.amplitude, 1),
        (keys.frequency, pitches),
        (keys.pan, 45),
        (keys.distance, 10),
        (keys.percent, .1)
    ]),
    pfields=None,
    note_limit=(len(pitches.values)*4),
    gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
)

g2 = copy.deepcopy(g)
g2.streams[keys.rhythm] = Itemstream(['e'],'sequence', tempo=120, notetype=notetypes.rhythm)
g2.streams[keys.frequency] = Itemstream([['c5','d','e'],'g3']*4+['f5','c3']*4+[['c5','d','e'],'g3']*4+['g5','d3']*4,notetype=notetypes.pitch)
g2.note_limit = 64
g.add_generator(g2)
g.generate_notes()

g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']

with open ("sine.orc", "r") as f:
    orc_string=f.read()
score_string = g.generate_score_string()
print (score_string)
cs = csnd6.Csound()

cs.CompileOrc(orc_string)
cs.ReadScore(score_string)
cs.SetOption('-odac')
cs.Start()
cs.Perform()
cs.Stop()
