 Thuja
=============

Python Module for algorithmic composition. The module specifically targets Csound, and generates Csound score (.sco) files for use in Csound pieces. Itemstreams were inspired by Rick Taube's Common Music 1.x.

The `requirements.txt` file includes the additional python libraries that need to be installed. You can install them with `pip install -r requirements.txt` prior to installing thuja.

You will also need to install Csound: https://csound.com/download.html

# Overview

Thuja is built on a two simple classes that deliver a ton of flexibility in composing Csound score files.

- **Itemstreams** define values for any pfield in a Csound score event.
- **Generators** are collections of Itemstreams and configuration info driving Csound score creation.


# A simple example

In Csound, notes have at a minimum an instrument, start time, and duration as their first 3 p-fields, but can have any number of additional parameters as required by an instrument. Here, we have p4 describing amplitude, and p5 describing frequency. 

	instr    start    dur    amp    freq
	p1       p2       p3     p4     p5
	i3       0.0      0.1    1      440

In Thuja, **Itemstreams** define sequences of p-field values as notes are generated. They can be configured to model certain compositional thinking, such as repeating, varying a sequence of values, reordering them, etc. 

from thuja
	from thuja.itemstream import notetypes
	from thuja.itemstream import streammodes
	from thuja.itemstream import Itemstream
	from thuja.generator import Generator
	from thuja.generator import keys
	from collections import OrderedDict
	from thuja import utils
	import copy
	import csnd6

Declare an Itemstream playing a sequence of rhythms. While float values are valid, Thuja defines a simple shorthand for rhythmic values: w, h, e, q and s are whole-, half-, quarter-, eighth- and sixteenth notes. 

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


This example is found in the pieces folder, called thuja_example.py. 


# Thuja.itemstream

### desc

Itemstreams are the basic compositional building blocks in Thuja, and are just what the name implies: streams of items. They are used to convey a stream of pitches, rhythms, numbers or strings. Used in groups with a Generator (see below) they describe musical ideas.  

Initialize an Itemstream with a list of values (the *initstream* parameter in init, which sets the *values* member of Initstream) and you're ready to roll.

Itemstreams have several configuration options apart from the values it contains, including:

*Notetype*

- **rhythm**: stream uses rhythm-string notation and stream tempo to generate numeric rhythm values.
- **pitch**: stream uses pitch-class notation (ie: c4, cs, cf) to generate numeric frequency values.
- **number**: stream uses numbers to generate numeric rhythm values.

*Streammode*

- **sequence**: stream will generate values in sequence.
- **random**: for each call to get_next_value(), stream will return a random item from values.
- **heap**: for each call to get_next_value(), stream will return a random item from values. No value is repeated until all others have been returned.

The default configuration for an Itemstream is streammode=streammodes.sequence, notetype=notetypes.number

### init with list

To construct an Itemstream, decide which pfield in a score you want to generate values for, and initialize the Itemstream. 

	amplitudes = Itemstream([1,2,3,4,5])

When a Generator leverages this Itemstream (or get_next_value() is called), the Itemstream will return 1 through 5 in sequence, wrapping back to the beginning on the 6th note generated.

### ctor with function

todo 

### notetype: pitch example

Itemstreams support generation of frequencies from pitch class notation. Pitch classes or notated as [pitch] + [accidental] + octave. a4 is the A below middle c, cs4 is c# above middle c, bf4 is the b-flat below middle c. If the octave is left off of the pitch class, the last known octave value is used, hence the example below generates c1 c1 c1 c1 d1 c1 c1 c1 d1:

	>>> pitches = Itemstream('c1 c c d c c c d'.split())
	>>> pitches.notetype = 'pitch'
	>>> for i in range(2*len(pitches.values)): 
			print (pitches.get_next_value())
	... 
	65.4063913251
	65.4063913251
	73.4161919794
	65.4063913251
	65.4063913251
	65.4063913251
	73.4161919794
	65.4063913251
	65.4063913251
	65.4063913251
	73.4161919794
	65.4063913251
	65.4063913251
	65.4063913251
	73.4161919794
	65.4063913251

### notetype: rhythm example

Rhythms can be generated by the Itemstream class by levaraging the rhythm notetype. Rhythms can be noted either as number representing fractional note values (i.e. 4 == quarter note, 8 == eighth note) or using the following nomenclature:

	w: whole note
	h: half note
	q: quarter note
	e: eighth note
	s: sixteenth note

Dots can be used as in regular rhythmic notation, where a dot adds half the value of the rhythm it proceeds. Hence, e. is equal to an eighth note PLUS a sixteenth note.

Rhythms can be added, making w+w+w, w+q, 12+12 all valid rhythm values.  In the example below, the a few rhymic values are supplied to an Itemstream.

	>>> rhythm = Itemstream('w h q e s e. w+q'.split())
	>>> rhythm.notetype = 'rhythm'
	>>> for i in range(len(rhythm.values)): print(rhythm.get_next_value())
	... 
	2.0
	1.0
	0.5
	0.25
	0.125
	0.125
	2.5
	
Itemstreams have a tempo value, which defaults to 120, as indicated by the durations returned in the above example. 

### streammode: sequence, heap, random

todo 

# Thuja.generator

### desc 

The generator class is a container holding a list of Itemstreams mapped to pfields, a starttime and optionally a nested list of Generators. Generators generate csound scores, or notelists for use in csounds scores.

### initializing a generator

todo 

### nested generators

todo 


### post-processes

todo
 
