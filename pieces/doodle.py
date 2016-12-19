from composition.itemstream import notetypes
from composition.itemstream import streammodes
from composition.itemstream import Itemstream
from composition.generator import Generator
from composition.generator import keys
from collections import OrderedDict
from composition import utils
import copy
import csnd6

rhythms = Itemstream(sum([
    ['e.','e.','e','q.','e','q.','e','h'],
    ['s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s'],
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
g2.streams[keys.frequency] = Itemstream(['c5','g3']*4+['f5','c3']*4+['c5','g3']*4+['g5','d3']*4,notetype=notetypes.pitch)
g2.note_limit = 64
g.add_generator(g2)
g.generate_notes()

g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']

with open ("/Users/benmca/src/csound/2015/sine.orc", "r") as f:
    orc_string=f.read()
score_string = g.generate_score_string()
cs = csnd6.Csound()
cs.CompileOrc(orc_string)
cs.ReadScore(score_string)
cs.SetOption('-odac')
cs.Start()
cs.Perform()
cs.Stop()
