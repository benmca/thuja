
import composition
import composition.itemstream as ci
import composition.score as cs
import numpy as np

rhythms = ci.itemstream(['e']*60,'sequence', tempo=np.linspace(120,480,32).tolist()+np.linspace(480,120,32).tolist())
rhythms.notetype = 'rhythm'
amps = ci.itemstream([3])
pitches = ci.itemstream(sum([
    ['c4','d','e','f','g'],
    ],[]))
#pitches.streammode = 'heap'
pitches.notetype = 'pitch'
pan = ci.itemstream([0])
dist= ci.itemstream([10])
pct = ci.itemstream([.1])

s = cs.score(rhythms,[amps,pitches,pan,dist,pct], note_limit=240)
s.gen_lines = [';sine\n','f 1 0 16384 10 1\n',';saw','f 2 0 256 7 0 128 1 0 -1 128 0\n',';pulse\n','f 3 0 256 7 1 128 1 0 -1 128 -1\n']
s.durstream = ci.itemstream([.1])
s.instr = 3
s.generate_notes()

s.rhythmstream.tempo = np.linspace(480,30,32).tolist()+np.linspace(30,480,32).tolist()
s.streams[2] = ci.itemstream([90])
s.generate_notes()

output = ""
for x in range(len(s.gen_lines)):
    output += s.gen_lines[x]
for x in range(len(s.notes)):
    output += s.notes[x]

s.end_lines = ['i99 0 ' + str(s.score_dur) + '\n']

s.generate_score("test_tempo.sco")
#score  = s.generate_score_string()
