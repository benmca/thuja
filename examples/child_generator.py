from asyncio import create_subprocess_exec

from thuja.itemstream import Itemstream
from thuja.notegenerator import Line
from thuja.itemstream import streammodes, notetypes
from thuja.streamkeys import keys
import thuja.utils as utils
import thuja.csound_utils as cs_utils
import random

melody_left = (
    Line().with_rhythm(Itemstream(['w'], notetype=notetypes.rhythm, streammode=streammodes.sequence))
    .with_duration(lambda note: note.rhythm * 1)
    .with_amps(1)
    .with_pitches(
        Itemstream(['c3', 'd', 'e', 'f', 'g', 'a', 'b'], notetype=notetypes.pitch,
                   streammode=streammodes.sequence))
    .with_pan(Itemstream(['10'], notetype=notetypes.number, streammode=streammodes.heap))
    .with_dist(5)
    .with_percent(.04)
    .with_instr(2)
)
melody_left.start_time = 4
melody_left.time_limit = 8

# we set melody left's pan to 10, so a whole note c major sequence is heard in on the left. I will start at 4 seconds,
#   and stop at 8 seconds. Let's add a sixteenth pulse panned right:

melody_right = (
    Line().with_rhythm(Itemstream(['s'], notetype=notetypes.rhythm, streammode=streammodes.sequence))
    .with_duration(lambda note: note.rhythm * 1)
    .with_amps(1)
    .with_pitches(
        Itemstream(['c3', 'g'], notetype=notetypes.pitch,
                   streammode=streammodes.sequence))
    .with_pan(Itemstream(['80'], notetype=notetypes.number, streammode=streammodes.heap))
    .with_dist(5)
    .with_percent(.04)
    .with_instr(2)
)

melody_left.add_generator(melody_right)
melody_left.generate_notes()


reverb_time = 10
melody_left.end_lines = ['i99 0 ' + str(melody_left.score_dur+10) + ' ' + str(reverb_time) + '\n']
print(melody_left.generate_score_string())

cs_utils.play_csound("sine+moog.orc", melody_left, silent=True, args_list=['-odac1'])