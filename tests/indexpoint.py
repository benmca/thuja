#use variable blueDuration for duration from blue
#use variable userConfigDir for user's .blue dir
#use variable blueLibDir for blue's lib directory
#use variable blueProjectDir for this project's directory
#use variable score at end of script to bring score back into blue
from composition.itemstream import itemstream
from composition.score import score


#IdMusic1.wav 
tuplestream = itemstream(
[ {"rhy":"h","indx":.769}, {"rhy":"h","indx":1.95}, {"rhy":"w","indx":3.175}, {"rhy":"h","indx":5.54}, {"rhy":"h","indx":6.67}, {"rhy":"h","indx": 8.0}]
)

#rhythms = itemstream(['e.','e.','e','q.','e','q.','e','h'],'sequence', tempo=120)
#rhythms.notetype = 'rhythm'
amps = itemstream([1])

#pitches = composition.itemstream.itemstream(['c3','e',['c','e','g'],'c4','e',['c','e','g']])
pitches = itemstream(sum([
    ['c1','c','c','d','c1','c','c','d'],
    ],[]))
#pitches.streammode = 'heap'
pitches.notetype = 'pitch'
s = score(None,[amps,pitches,tuplestream], note_limit=(len(pitches.values)*2))
s.gen_lines = [';sine\n','f 1 0 16384 10 1\n',';saw','f 2 0 256 7 0 128 1 0 -1 128 0\n',';pulse\n','f 3 0 256 7 1 128 1 0 -1 128 -1\n']
s.durstream = itemstream([.1])
#s.generate_score("/Users/benmca/Documents/src/sandbox/python/test.sco")
#s.generate_score()
s.generate_notes()

#rhythms = itemstream(['e'],'sequence', tempo=120)
##rhythms = composition.itemstream.itemstream(['e.','e.','e'],'heap', tempo=240)
#rhythms.notetype = 'rhythm'
#s.rhythmstream = rhythms
#pitches = itemstream(sum([
    #['fs1'],
    #],[]))
#pitches.notetype = 'pitch'
#s.streams[1] = pitches
#s.note_limit = 32
##reset time
#s.starttime = 0.0
#s.curtime = s.starttime
#s.generate_notes()
#for x in s.notes:
    #print(x)
    
s.generate_score("./test.sco")
#score  = s.generate_score_string()
