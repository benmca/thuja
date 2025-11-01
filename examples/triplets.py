from thuja.itemstream import notetypes, Itemstream, streammodes
from thuja.streamkeys import keys
from thuja.notegenerator import Line
from thuja import csound_utils

rhythms = Itemstream(
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

g = (
    Line().with_instr(1)
    .with_rhythm(rhythms)
    .with_duration(.1)
    .with_amps(.25)
    .with_freqs(pitches)
)

g.gen_lines = ['f 1 0 16384 10 1']
g.time_limit=60

g2 = g.deepcopy()
g2.with_rhythm(Itemstream(['e'],'sequence', tempo=120, notetype=notetypes.rhythm))
g2.with_pitches(Itemstream([['c5','d','e'],'g3']*4+['f5','c3']*4+[['c5','d','e'],'g3']*4+['g5','d3']*4,notetype=notetypes.pitch))
g.add_generator(g2)

g3 = g2.deepcopy()
g.add_generator(g3)
g.generate_notes()

print(g.generate_score_string())
csound_utils.play_csound("sine.orc", g, args_list=['-odac0'])