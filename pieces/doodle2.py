#use variable blueDuration for duration from blue
#use variable userConfigDir for user's .blue dir
#use variable blueLibDir for blue's lib directory
#use variable blueProjectDir for this project's directory
#use variable score at end of script to bring score back into blue
from composition.itemstream import Itemstream
from composition.score import Score



#IdMusic1.wav 
# ['h',.769], ['h',1.95], ['w'], 3.175], ['h',5.54], ['h'], 6.67], ['w'], 8.0]

rhythms = Itemstream(sum([
    ['e.','e.','e','q.','e','q.','e','h'],
    ['s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s','s'],
    ],[]
    ),'sequence', tempo=120)
rhythms.notetype = 'rhythm'
amps = Itemstream([.1])

#pitches = Itemstream(['c3','e',['c','e','g'],'c4','e',['c','e','g']])
pitches = Itemstream(sum([
    ['c4','c','c','d','c5','c','c','d'],
    ['c3','e',['c','e','g'],'c4','e',['c','e','g']],
    [['c2','e','g'],['c4','e','g'],['c','d','e'],['e','f','g']],
    ],[]))
pitches.streammode = 'heap'
pitches.notetype = 'pitch'

pan = Itemstream([45])
dist= Itemstream([10])
pct = Itemstream([.1])

s = Score(rhythms,[amps,pitches,pan,dist,pct], note_limit=(len(pitches.values)*10))

s.gen_lines = [';sine\n','f 1 0 16384 10 1\n',';saw','f 2 0 256 7 0 128 1 0 -1 128 0\n',';pulse\n','f 3 0 256 7 1 128 1 0 -1 128 -1\n']
s.durstream = Itemstream([.1])
s.instr = 1

s.generate_notes()

s.starttime = 0
s.curtime = 0;
s.streams[2] = Itemstream([0])
s.generate_notes()

s.starttime = 0
s.curtime = 0;
s.streams[2] = Itemstream([90])
s.generate_notes()


rhythms = Itemstream(['q'],'sequence', tempo=60)
rhythms.notetype = 'rhythm'
amps = Itemstream([.1])

#pitches = Itemstream(['c3','e',['c','e','g'],'c4','e',['c','e','g']])
pitches = Itemstream(
    ['c6', 'c0'])
pitches.streammode = 'sequence'
pitches.notetype = 'pitch'

s.rhythmstream = rhythms
s.streams[1] = pitches
s.starttime = 0
s.curtime = 0;
s.streams[2] = Itemstream([10])
s.generate_notes()



rhythms = Itemstream(
    ['q']
    ,'sequence', tempo=120)
rhythms.notetype = 'rhythm'
amps = Itemstream([.1])

#pitches = Itemstream(['c3','e',['c','e','g'],'c4','e',['c','e','g']])
pitches = Itemstream(
    ['c0', 'c6'])
pitches.streammode = 'sequence'
pitches.notetype = 'pitch'

s.rhythmstream = rhythms
s.streams[1] = pitches
s.starttime = 0
s.curtime = 0;
s.streams[2] = Itemstream([80])
s.generate_notes()



output = ""
for x in range(len(s.gen_lines)):
    output += s.gen_lines[x]
for x in range(len(s.notes)):
    output += s.notes[x]
    
s.end_lines = ['i99 0 ' + str(s.score_dur) + '\n']
    
s.generate_score("test.sco")
#score  = s.generate_score_string()
