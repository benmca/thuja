from composition.itemstream import Itemstream
from composition.score import Score
import numpy as np

rhythms = Itemstream(['e']*60,'sequence', tempo=np.linspace(120,480,32).tolist()+np.linspace(480,120,32).tolist())
rhythms.notetype = 'rhythm'
amps = Itemstream([3])
pitches = Itemstream(sum([
    ['c4','d','e','f','g'],
    ],[]))
#pitches.streammode = 'heap'
pitches.notetype = 'pitch'
pan = Itemstream([0])
dist= Itemstream([10])
pct = Itemstream([.1])

s = Score(rhythms,[amps,pitches,pan,dist,pct], note_limit=240)
s.gen_lines = [';sine\n','f 1 0 16384 10 1\n',';saw','f 2 0 256 7 0 128 1 0 -1 128 0\n',';pulse\n','f 3 0 256 7 1 128 1 0 -1 128 -1\n']
s.durstream = Itemstream([.1])
s.instr = 3
s.generate_notes()

s.rhythmstream.tempo = np.linspace(480,30,32).tolist()+np.linspace(30,480,32).tolist()
s.streams[2] = Itemstream([90])
s.generate_notes()

output = ""
for x in range(len(s.gen_lines)):
    output += s.gen_lines[x]
for x in range(len(s.notes)):
    output += s.notes[x]

s.end_lines = ['i99 0 ' + str(s.score_dur) + '\n']

s.generate_score("test_tempo.sco")
#score  = s.generate_score_string()
