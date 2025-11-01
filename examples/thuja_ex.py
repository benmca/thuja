from thuja.itemstream import streammodes, notetypes, Itemstream
from thuja.notegenerator import Line
from thuja import csound_utils

rhythms = Itemstream(['e.', 'e.', 'e', 'q.', 'e', 'q.', 'e', 'h'],
                     streammode=streammodes.sequence,
                     tempo=240,
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

g = (
    Line().with_instr(1)
    .with_rhythm(rhythms)
    .with_duration(.1)
    .with_amps(1)
    .with_freqs(pitches)
    .with_pan(45)
    .with_dist(10)
    .with_percent(.1)
)

g.note_limit = len(pitches.values) * 4
g.gen_lines = ['f 1 0 16384 10 1']

g.generate_notes()
g.end_lines = ['i99 0 ' + str(g.score_dur + 10) + '\n']
score_string = g.generate_score_string()
csound_utils.play_csound("sine.orc", g, silent=True, args_list=['-odac0', '-W'])
