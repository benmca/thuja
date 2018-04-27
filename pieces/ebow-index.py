from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
from thuja.itemstream import streammodes
import thuja.utils as utils
import thuja.csound_utils as cs_utils
from collections import OrderedDict
import numpy as np
import csnd6
import copy

def post_process(note, context):
    item = context['tuplestream'].get_next_value()
    indx = context['indexes'].index(item[keys.index])
    orig_rhythm = context['orig_rhythms'][indx]
    note.rhythm = utils.rhythm_to_duration(item[keys.rhythm], context['tuplestream'].tempo)
    note.pfields[keys.index] = item[keys.index]
    note.pfields['orig_rhythm'] = utils.rhythm_to_duration(orig_rhythm, context['tuplestream'].tempo)
    note.pfields[keys.frequency] = context['tuplestream'].tempo / utils.quarter_duration_to_tempo(.697-.018)
    pass


g = Generator(
    streams=OrderedDict([
        (keys.instrument, Itemstream([1])),
        (keys.duration, lambda note:note.pfields['orig_rhythm']),
        (keys.amplitude, Itemstream([3])),
        (keys.frequency, Itemstream([1], notetype='number')),
        (keys.pan, Itemstream([45])),
        (keys.distance, Itemstream([10])),
        (keys.percent, Itemstream([.01]))
    ]),
    pfields=[
        keys.instrument,
        keys.start_time,
        keys.duration,
        keys.amplitude,
        keys.frequency,
        keys.pan,
        keys.distance,
        keys.percent,
        keys.index,
        'orig_rhythm'
    ],
    note_limit=300,
    post_processes=[post_process]
)
g.context['rhythms'] = ['q', 'q', 's', 'e', 's', 's', 'e', 's', 'q', 'e.', 'e', 'q', 'e', 's']
g.context['indexes'] = [.018, .697, 1.376, 1.538, 1.869, 2.032, 2.2, 2.543, 2.705, 3.373, 3.895, 4.232, 4.894, 5.236]

for x in range(len(g.context['indexes'])):
    g.context['indexes'][x] = g.context['indexes'][x] + 10

g.context['orig_rhythms'] = ['q', 'q', 's', 'e', 's', 's', 'e', 's', 'q', 'e.', 'e', 'q', 'e', 's']
g.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
                                      mapping_lists=[g.context['rhythms'],
                                                     g.context['indexes']],
                                      tempo=80,
                                      streammode=streammodes.random)
#
# g2 = copy.deepcopy(g)
# g2.context['indexes'] = [.018]
# g2.context['rhythms'] = ['q']
# g2.streams[keys.pan] = Itemstream([0])
# g2.streams[keys.amplitude] = Itemstream([1])
# g2.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
#                                       mapping_lists=[g2.context['rhythms'],
#                                                      g2.context['indexes']],
#                                       tempo=80)
#
# g3 = copy.deepcopy(g2)
# g3.context['indexes'] = [.018]
# g3.context['rhythms'] = ['s']
# g3.streams[keys.pan] = Itemstream([90])
# g3.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
#                                       mapping_lists=[g3.context['rhythms'],
#                                                      g3.context['indexes']],
#                                       tempo=80)

g.gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']

g.generate_notes()



g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']

cs_utils.play_csound("indexebow.orc", g)
