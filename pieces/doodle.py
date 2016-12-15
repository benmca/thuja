from composition.itemstream import Itemstream
from composition.generator import Generator
from composition.generator import keys
from collections import OrderedDict
from composition import utils
import copy

rhythms = Itemstream(sum([
    ['e.','e.','e','q.','e','q.','e','h'],
    ['s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s'],
    ],[]
    ),'sequence', tempo=120)
rhythms.notetype = 'rhythm'
amps = Itemstream([1])

pitches = Itemstream(sum([
    ['c4','c','c','d','c5','c','c','d'],
    ['c3','e',['c','e','g'],'c4','e',['c','e','g']],
    [['c','e','g'],['c','e','g'],['c','d','e'],['e','f','g']],
    ],[]))
pitches.streammode = 'heap'
pitches.notetype = 'pitch'

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
#
# output = ""
# for x in range(len(s.gen_lines)):
#     output += s.gen_lines[x]
# for x in range(len(s.notes)):
#     output += s.notes[x]

g2 = copy.deepcopy(g)
g2.streams[keys.rhythm] = Itemstream(['e'],'sequence', tempo=120)
g2.streams[keys.rhythm].notetype = 'rhythm'
g2.streams[keys.frequency] = Itemstream(sum([
    ['fs6'],
    ],[]))
g2.streams[keys.frequency].notetype = 'pitch'
g2.note_limit = 64
g.add_generator(g2)
g.generate_notes()

g.end_lines = ['i99 0 ' + str(g.score_dur) + '\n']
g.generate_score("../../csound/2015/test.sco")



# score = s.generate_score_string()
# orc = open('../../csound/2015/midiout.orc', 'r').read()

# c = csnd6.Csound()
# c.SetOption("-odac")  # Using SetOption() to configure Csound
                      # Note: use only one commandline flag at a time
# c.SetOption("-M0")
# c.SetOption("-Q0")
# c.SetOption("-B512")
# c.SetOption("-b64")
# c.SetOption("-d")

# c.CompileOrc(orc)     # Compile the Csound Orchestra string
# c.ReadScore(score)      # Compile the Csound SCO String
# c.Start()  # When compiling from strings, this call is necessary before doing any performing
# c.Perform()  # Run Csound to completion
# c.Stop()

# os.execvp('csound','-odac -Q0 -B512 -b64 -d ../../csound/2015/midiout.orc test.sco'.split())