from thuja.itemstream import streammodes, notetypes, Itemstream
from thuja.notegenerator import Line
from thuja import csound_utils


#
# When constructing a list of values for an itemstream, you can use any method you like.
#  I like to use split and concatenation to keep the ideas readable.  This will yield:
#  ['a2', 'b', 'c3', 'e', 'a2', 'r', 'e2', 'f', 'r', 'b', ['e', 'b'], ['e', 'b'],
#  'a2', 'c3', 'c', 'c', 'd', 'd', 'd', 'e', 'r', 'e', ['e', 'b'], ['e', 'b']]
#
pitches = Itemstream('a2 b c3 e a2 r e2 f r b'.split() + [['e', 'b']] + [['e', 'b']]
                     + 'a2 c3 c c d d d e r e'.split() + [['e', 'b']] + [['e', 'b']],
    streammode=streammodes.sequence,
    notetype=notetypes.pitch
)
# a sequence of four 16ths and two 8ths.
rhythms = Itemstream('s s s s e e'.split(),
                     streammode=streammodes.sequence,
                     tempo=120,
                     notetype=notetypes.rhythm)

# we're using the Line class, which adds many conveniences.  One convenience is we can initialize fields
#   with a single value. The method will take care of Itemstream construction for us. See NoteGenerator.py
#   to get a sense of the default values per field.
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

# we can define the duration of this generator in terms of how many notes (note_limit)
#   or how long in seconds (time_limit).
g.note_limit = len(pitches.values) * 4

# gen_lines are added at the beginning of the score. Handy to prime the score for your orc with
#   f statements, or any other static data before notes are generated.
g.gen_lines = [';sine\n',
             'f 1 0 16384 10 1\n',
             ';saw',
             'f 2 0 256 7 0 128 1 0 -1 128 0\n',
             ';pulse\n',
             'f 3 0 256 7 1 128 1 0 -1 128 -1\n']

g.generate_notes()

# end_lines are added at the the end of the score, after the generated notes.
#   Here, we'll tell instr 99 (our reverb instrument) to sound for 10 seconds more
#   than the calculated duration of the score - of all of the notes generated.
g.end_lines = ['i99 0 ' + str(g.score_dur + 10) + '\n']

csound_utils.play_csound("sine+moog.orc", g, silent=True, args_list=['-odac0', '-W'])
