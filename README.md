 Thuja
=============


..is a Python Module for algorithmic composition. It uses Csound for audio generation, and generates Csound score (.sco) files for use in Csound pieces. Itemstreams were inspired by Rick Taube's Common Music 1.x. 

Install with `pip install -r requirements.txt`. Csound is available [here](https://csound.com/download.html). [The excellent FLOSS Manual]((https://flossmanual.csound.com/) is a great help if you're new to Csound. 

# Tests

To run the tests:

	cd tests
	sh runUnitTests.sh

The /examples directory contains the best documentation to date, and there's a verbose walkthrough of the thuja mental model in the doc folder. You might read that after reading this.

# Getting Started

At Thuja's core are two simple classes that deliver a ton of flexibility in composing Csound score files.

- **Itemstreams** define values for any pfield in a Csound score event.
- **NoteGenerators** are collections of Itemstreams and configuration info driving Csound score creation.


# A simple example

In Csound, notes have at a minimum an instrument, start time, and duration as their first 3 p-fields (a csound naming convention: 'parameter fields'), but can have any number of additional parameters as required by an instrument. Here, we have p4 describing amplitude, and p5 describing frequency. 

	instr    start    dur    amp    freq
	p1       p2       p3     p4     p5
	i3       0.0      0.1    1      440

In Thuja, **Itemstreams** define sequences of p-field values, and provide them to a NoteGenerator as notes are generated. They can be configured to model certain compositional thinking, such as repeating, varying a sequence of values, reordering them, etc. 

    from thuja.itemstream import streammodes, notetypes, Itemstream
    from thuja.notegenerator import Line
    from thuja import csound_utils

Declare an Itemstream with a sequence of rhythms. When constructing a list of values for an Itemstream, you can use any method you like. I like to use split() and concatenation to keep the ideas readable.  

    rhythms = Itemstream('s s s s e e'.split(),
                         streammode=streammodes.sequence,
                         tempo=120,
                         notetype=notetypes.rhythm)
    
Side notes on rhythm:

- While float values are valid, Thuja defines a simple shorthand for rhythmic values: w, h, e, q and s are whole-, half-, quarter-, eighth- and sixteenth notes. 
- Dots can be added after as in traditional notation, and add half the value to the note. You can add rhythms as well i.e. q. == q+e 
- Numbers can be used in place of these symbols i.e. 32, 16 and 8 are all viable, and derive timing information from the tempo and the duration of a whole note at that tempo. So, at 60 bpm, a q is 1 second and s or 16 is .25.

We'll set amplitude to 1 for all generated notes. The Csound score will use this as a scalar (between 0 and 1) for loudness. 

	amps = Itemstream(1)

Define a string of pitches using [scientific pitch notation](https://en.wikipedia.org/wiki/Scientific_pitch_notation). **Chords are nested lists.** 'r' denotes a rest in a stream of notes. 
Octaves persist until a new octave number is used.

    pitches = Itemstream('a2 b c3 e a2 r e2 f r b'.split() + [['e', 'b']] + [['e', 'b']]
                         + 'a2 c3 c c d d d e r e'.split() + [['e', 'b']] + [['e', 'b']],
        streammode=streammodes.sequence,
        notetype=notetypes.pitch
    )

The Line class, derived from NoteGenerator, adds some convenience methods, and defaults to these p-fields for generated notes:

    #instr	start	dur		amp		freq	pan		distance	percent
    #p1		p2		p3		p4		p5		p6		p7			p8	
    i1      0.0 	0.1		1 		440		45		10			.1

We set default values in the NoteGenerator constructor for instrument, duration, pan, distance and percent. Under the covers, this creates a single item ItemStream for each of these fields as we did for amps, above.

```
g = (
    Line().with_instr(2)
    .with_rhythm(rhythms)
    .with_duration(.1)
    .with_amps(1)
    .with_freqs(pitches)
    .with_pan(45)
    .with_dist(10)
    .with_percent(.1)
)

g.note_limit = len(pitches.values) * 4
g.gen_lines = [';sine\n',
             'f 1 0 16384 10 1\n',
             ';saw',
             'f 2 0 256 7 0 128 1 0 -1 128 0\n',
             ';pulse\n',
             'f 3 0 256 7 1 128 1 0 -1 128 -1\n']

g.generate_notes()
```

Add a note for reverb:

    g.end_lines = ['i99 0 ' + str(g.score_dur + 10) + '\n']


This example is found in the examples folder, called thuja_ex.py. 

# Thuja.itemstream

### desc

Itemstreams are the basic compositional building blocks in Thuja, and are just what the name implies: streams of items. They are used to convey a stream of pitches, rhythms, numbers or strings. Used in groups with a Generator (see below) they describe musical ideas.  

Initialize an Itemstream with a list of values (the *initstream* parameter in init, which sets the *values* 
member of Initstream) and you're ready to roll.

Itemstreams have several configuration options apart from the values it contains, including:

*Notetype*

- **rhythm**: stream uses rhythm-string notation (i.e. w, h, q, e. etc) and tempo to generate numeric rhythm values.
- **pitch**: stream uses pitch-class notation (i.e. c4, cs, cf) to generate numeric frequency values.
- **number**: stream uses numbers to generate numeric rhythm values.

*Streammode*

- **sequence**: stream will generate values in the order provided.
- **random**: stream will return a random item from values.
- **heap**: stream will return a random item from values. No value is repeated until all others have been returned.

The default configuration for an Itemstream is streammode=streammodes.sequence, notetype=notetypes.number

### init with list

To construct an Itemstream, decide which p-field in a score you want to generate values for, and initialize the 
Itemstream. 

	amplitudes = Itemstream([1,2,3,4,5])

When a NoteGenerator leverages this Itemstream (or get_next_value() is called), the Itemstream will return 1 through 5 in sequence, wrapping back to the beginning on the 6th note generated.

### notetype: pitch example

Itemstreams support generation of frequencies from scientific pitch notation: [pitch] + [accidental] + octave. a3 is the A below middle c, cs4 is c# above middle c, bf3 is the b-flat below middle c, c4 is middle c. If the octave is left off of the pitch class, the last known octave value is used, hence the example below generates c1 c1 c1 c1 d1 c1 c1 c1 d1:

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

Rhythms can be added, making w+w+w, w+q, 12+12 all valid rhythm values.  In the example below, the a few rhythmic values are supplied to an Itemstream.

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

# thuja.notegenerator

### desc 

The class is a container holding a list of Itemstreams mapped to p-fields, a starttime and optionally a nested list of NoteGenerators. NoteGenerators generate csound scores, or notelists for use in csounds scores. 

### nested generators

NoteGenerators can have children, whose start_time, time_limit and note_limit are inherited from the parent. See examples/child_generator.py for an illustration. 

### post-processes and lambdas

For each note generated, callables can be used to set parameters. post_processes added to a NoteGenerator are called after all p-fields are populated, and can be used to add or modify a note. Any lambda functions used to initialize p-fields in place of Itemstreams are called after post_processes.  See test_callables_lambda and 
test_callables_postprocesses in tests/test_generator.py for examples. 

