pyComposition
=============

Python Module for algorithmic composition, based on concepts from Rick Taube's Common Music 1.x  

This doc is a work in progress. 


The mental model:

1. Generators (currently the score object) generate notes aka events, given a start time and duration. 

2. the notes generated have, at a minimum, a start time, duration as their first 3 pfields i.e:

```
#instr	start	dur	
i3      0.0 	0.1	 	
```  

3. Itemstreams define sequences driving successive values of these pfields as notes are generated.  

```
#instr	start	dur		amp		freq
i3      0.0 	0.1		1 		440
```  
Itemstreams can be configured to model certain compositional thinking, such as repeating, varying a sequence of values, reordering them randomly or 'in-heap'. 

A sample, with notes:


```
import composition
import composition.itemstream as ci
import composition.score as cs

rhythms = ci.itemstream(['e.','e.','e','q.','e','q.','e','h'],'sequence', tempo=120)
rhythms.notetype = 'rhythm'
```
We begin by creating a stream for rhythms. Here, the rhythmic sequence is 2 dotted eighths, an eighth, a dotted quarter, and so on. After constructing, we set the notetype to 'rhythm'.  This provides a hint to the Generator, that these values should be interpreted as rhythms and will govern both start time and duration unless otherwise configured.

```
amps = ci.itemstream([1])
```

For amplitude, we provide a single value, 1, which will be present in every generated note.

```

pitches = ci.itemstream(sum([
    ['c4','c','c','d','c5','c','c','d'],
    ],[]))
pitches.streammode = 'heap'
pitches.notetype = 'pitch'
```
Pitches are created with a special syntax: [note name][s|f|n][octave]. Examples: b4, cs5, af8, an3

Note name is required, but the other 2 are optional as cna be seen above. Octaves apply to all notes afterward, while accidentals only apply to the note they decorate.

The stream mode here is 'heap', which indicates that this stream generates pitches from it's configure list randomly, but without repeating a note, as in much serial music. 


```
s = cs.score(rhythms,[amps,pitches], note_limit=(len(pitches.values)*2))
s.gen_lines = [';sine\n','f 1 0 16384 10 1\n',';saw','f 2 0 256 7 0 128 1 0 -1 128 0\n',';pulse\n','f 3 0 256 7 1 128 1 0 -1 128 -1\n']
s.instr = 3
s.generate_notes()
```
Final steps:
- Create the score object, giving it the itemstreams and note limit.
- The score's gen_lines array is populated with csound-compatible score lines when generate_notes is called. Here, a header is placed at the beginning of the array, which will look familiar to csound users: it provides the f-statements required by test orchestra file.

Now that the gen_lines array is full of musical material, it can be outputted link so, below:


```

output = ""
for x in range(len(s.gen_lines)):
    output += s.gen_lines[x]
for x in range(len(s.notes)):
    output += s.notes[x]

print(output)
    
s.generate_score("test.sco")

```