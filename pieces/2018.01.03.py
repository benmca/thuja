from thuja.itemstream import notetypes
from thuja.itemstream import streammodes
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
from collections import OrderedDict
from thuja import utils
import copy
import csnd6
the_tempo = 120

rhythms = Itemstream(
    'e e q e s s s s s s e e e e q q'.split(),
    streammode=streammodes.sequence,
    tempo=the_tempo,
    notetype=notetypes.rhythm)

amps = Itemstream([1])

pitches = Itemstream('a4 c e r a4 a a c a4 g r a4 a a a r'.split(),
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
        (keys.percent, .1),
        ("channel", 1)
    ]),
    pfields=None,
    gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
)
g.time_limit=120

g2 = copy.deepcopy(g)
g2.streams[keys.rhythm] = Itemstream(['q'],'sequence', tempo=the_tempo, notetype=notetypes.rhythm)
g2.streams[keys.frequency] = Itemstream(['a5'], notetype=notetypes.pitch)
g2.streams[keys.pan] = Itemstream([0,90], 'sequence')
g2.streams[keys.distance] = Itemstream([1], 'sequence')
g2.streams[keys.percent] = Itemstream([0], 'sequence')
g2.streams[keys.amplitude] = Itemstream([.25])
g.add_generator(g2)


g.generate_notes()

g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']

with open ("sine+midiout+channelparam.orc", "r") as f:
    orc_string=f.read()
score_string = g.generate_score_string()
with open ("test.sco", "w") as sco:
    sco.write(score_string)
cs = csnd6.Csound()
cs.CompileOrc(orc_string)
cs.ReadScore(score_string)
cs.SetOption('-odac')
cs.SetOption('-Q0')
cs.SetOption('-b64')
cs.SetOption('-B64')
cs.Start()
cs.Perform()
cs.Stop()
