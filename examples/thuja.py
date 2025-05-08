from thuja.itemstream import notetypes
from thuja.itemstream import streammodes
from thuja.itemstream import Itemstream
from thuja.notegenerator import NoteGenerator
from thuja.streamkeys import keys
from thuja import csound_utils
from collections import OrderedDict

rhythms = Itemstream(['e.', 'e.', 'e', 'q.', 'e', 'q.', 'e', 'h'],
                     streammode=streammodes.sequence,
                     tempo=120,
                     notetype=notetypes.rhythm)
amps = Itemstream([1])

pitches = Itemstream(sum([
    ['c4', 'r', 'r', 'd', 'c5', 'c', 'c', 'd'],
    ['c3', 'e', ['c', 'e', 'g'], 'c4', 'r', ['c', 'e', 'g']],
    [['c', 'e', 'g'], ['c', 'e', 'g'], ['c', 'd', 'e'], ['e', 'f', 'g']],
], []),
    streammode=streammodes.heap,
    notetype=notetypes.pitch
)

g = NoteGenerator(
    streams=OrderedDict([
        (keys.instrument, 1),
        (keys.rhythm, rhythms),
        (keys.duration, .1),
        (keys.amplitude, amps),
        (keys.frequency, pitches),
        (keys.pan, 45),
        (keys.distance, 10),
        (keys.percent, .1)
    ]),
    note_limit=(len(pitches.values)*4),
    gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
)

g.generate_notes()
g.end_lines = ['i99 0 ' + str(g.score_dur + 10) + '\n']

score_string = g.generate_score_string()
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac1', '-W'])
