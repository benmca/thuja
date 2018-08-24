from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
from thuja.itemstream import streammodes
from thuja.itemstream import notetypes
import thuja.utils as utils
import thuja.csound_utils as cs_utils
from collections import OrderedDict
import numpy as np
import csnd6
import copy
import random
import dill
import pickle
import time


# random.seed(12)
# random.seed(11)
seed = 1528952907
random.seed(seed)
filelen = 60
tempo = 240

pitches_to_files = {
    'a': 'a.wav',
    'as': 'as.wav',
    'b': 'b.wav',
    'c': 'c.wav',
    'cs': 'cs.wav',
    'd': 'd.wav',
    'ds': 'ds.wav',
    'e': 'e.wav',
    'f': 'f.wav',
    'fs': 'fs.wav',
    'g': 'g.wav',
    'gs': 'gs.wav'
}

# for some reason, indx always ends up being the first item here...
def post_process(note, context):
    item = context['tuplestream'].get_next_value()
    indx = context['indexes'].index(item[keys.index])
    orig_rhythm = context['orig_rhythms'][indx]
    note.rhythm = utils.rhythm_to_duration(item[keys.rhythm], context['tuplestream'].tempo)
    note.pfields[keys.index] = item[keys.index]
    note.pfields['orig_rhythm'] = utils.rhythm_to_duration(orig_rhythm, context['tuplestream'].tempo)
    # note.pfields[keys.frequency] = context['tuplestream'].tempo / utils.quarter_duration_to_tempo(.697-.018)
    note.pfields['inst_file'] = '"' + '/Users/ben/Music/Portfolio/_gtrs/' + note.pfields[keys.frequency] + '.wav' + '"'
    note.pfields[keys.frequency] = 1
    pass


g = Generator(
    streams=OrderedDict([
        (keys.instrument, Itemstream([1])),
        (keys.duration, lambda note:note.pfields['orig_rhythm']),
        (keys.amplitude, Itemstream([3])),
        (keys.frequency, Itemstream(['a', 'a',  'c', 'c', 'd', 'd', 'd'])),
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
        'orig_rhythm',
        'inst_file'
    ],
    note_limit=300,
    post_processes=[post_process]
)

# g.context['rhythms'] = ['q', 's']
# g.context['indexes'] = [53.080063070509745, 4.424683781699188]
g.context['rhythms'] = ['s', 'e.']
g.context['indexes'] = [31.786509144647518, 59.72425937269479]
g.context['orig_rhythms'] = g.context['rhythms']
g.streams[keys.pan] = Itemstream([0])
g.streams[keys.amplitude] = Itemstream([1])
g.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
                                      mapping_lists=[g.context['rhythms'],
                                                     g.context['indexes']],
                                      tempo=tempo*.5,
                                      streammode=streammodes.random,
                                      seed=seed)
#
# g2 = copy.deepcopy(g)
#
#
# g2.context['rhythms'] = ['s', 's']
# g2.context['indexes'] = [23.301317351754314, 24.822384009095295]
# g2.context['orig_rhythms'] = g.context['rhythms']
# g2.streams[keys.pan] = Itemstream([90])
# g2.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
#                                       mapping_lists=[g2.context['rhythms'],
#                                                      g2.context['indexes']],
#                                       tempo=tempo*.5,
#                                       streammode=streammodes.random,
#                                       seed=seed)
# g.add_generator(g2)

g.gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
g.generate_notes()

g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']


print(g.generate_score_string())

# for x in [g, g2, g3]:
#     print(x.streams[keys.frequency].values)
#     print(x.context['rhythms'])
#     print(x.context['indexes'])

cs_utils.play_csound("generic-index.orc", g, silent=True)
