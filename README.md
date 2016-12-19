pyComposition
=============

Python Module for algorithmic composition. The module specifically targets Csound, and generates Csound score (.sco) files for use in Csound pieces. Itemstreams were inspired by Rick Taube's Common Music 1.x.

#Overview

pyComposition is built on a two simple classes that deliver a ton of flexibility in composing Csound score files.

- **Generators** are collections of Itemstreams and configuration info driving Csound score creation.
- **Itemstreams** define values for any pfield in a Csound score event.

These docs are a work-in-progress.

#A simple example

In Csound, notes have at a minimum an instrument, start time, and duration as their first 3 p-fields, but can have any number of additional parameters as required by an instrument. Here, we have p4 describing amplitude, and p5 describing frequency. 

```
#instr	start	dur		amp		freq
#p1		p2		p3		p4		p5
i3      0.0 	0.1		1 		440
```
In pyComposition, **Itemstreams** define sequences of p-field values as notes are generated. They can be configured to model certain compositional thinking, such as repeating, varying a sequence of values, reordering them, etc. 


	from composition.itemstream import notetypes
	from composition.itemstream import streammodes
	from composition.itemstream import Itemstream
	from composition.generator import Generator
	from composition.generator import keys
	from collections import OrderedDict
	from composition import utils
	import copy
	import csnd6

Declare an Itemstream playing a sequence of rhythms. While float values are valid, pyComposition defines a simple shorthand for rhythmic values: w, h, e, q and s are whole-, half-, quarter-, eighth- and sixteenth notes. 

	rhythms = Itemstream(['e.','e.','e','q.','e','q.','e','h']),
	    streammode=streammodes.sequence,
	    tempo=120,
	    notetype=notetypes.rhythm)

Amplitude will always be 1.

	amps = Itemstream([1])

Define a string of pitches using pitch-class notation. Chords are nested lists. This stream is in heap mode, meaning no value will repeat until all others have been used.

	pitches = Itemstream(sum([
	    ['c4','c','c','d','c5','c','c','d'],
	    ['c3','e',['c','e','g'],'c4','e',['c','e','g']],
	    [['c','e','g'],['c','e','g'],['c','d','e'],['e','f','g']],
	    ],[]),
	    streammode=streammodes.heap,
	    notetype=notetypes.pitch
	)

Define a Generator which will generate notes like so: 

```
#instr	start	dur		amp		freq	pan		distance	percent
#p1		p2		p3		p4		p5		p6		p7			p8	
i1      0.0 	0.1		1 		440		45		10			.1
```

```
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
    note_limit=(len(pitches.values)*4),
    gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
)

g.generate_notes()
```

Add a note for reverb:

	g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']


This example is found in the pieces folder, called doodle.py. 