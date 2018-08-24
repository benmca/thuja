from __future__ import print_function
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


# seed = int(time.time())
seed = 1531254620
random.seed(seed)
filelen = 60
tempo = 60

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

def post_process(note, context):
    item = context['tuplestream'].get_next_value()
    indx = context['indexes'].index(item[keys.index])
    orig_rhythm = context['orig_rhythms'][indx]
    note.rhythm = utils.rhythm_to_duration(item[keys.rhythm], context['tuplestream'].tempo)
    note.pfields[keys.index] = item[keys.index]
    note.pfields['orig_rhythm'] = utils.rhythm_to_duration(orig_rhythm, context['tuplestream'].tempo)
    # note.pfields[keys.frequency] = context['tuplestream'].tempo / utils.quarter_duration_to_tempo(.697-.018)
    note.pfields['inst_file'] = '"' + '/Users/ben/Music/Portfolio/_gtrs/' + note.pfields['filepitch'] + '.wav' + '"'
    # note.pfields[keys.frequency] = 1
    pass


g = Generator(
    streams=OrderedDict([
        (keys.instrument, Itemstream([1])),
        (keys.duration, lambda note:note.pfields['orig_rhythm']),
        (keys.amplitude, Itemstream([3])),
        (keys.frequency, Itemstream([1])),
        (keys.pan, Itemstream([45])),
        (keys.distance, Itemstream([10])),
        (keys.percent, Itemstream([.01])),
        ('output_prefix', Itemstream([1])),
        ('filepitch', Itemstream(['a', 'a', 'c', 'c', 'd', 'd'])),
        ('stretch', Itemstream(['1'])),
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
        'inst_file',
        'output_prefix'
    ],
    note_limit=300,
    post_processes=[post_process]
)


def gen_rhythms(gen, l, opt=1):
    if opt == 1:
        rhystrings = sum([['q'],['s']*5, ['e'], ['e.'], ['h']], [])
    if opt == 2:
        rhystrings = sum(['e q q q q e e e e e e e e e e e'.split()], [])
    else:
        rhystrings = sum([['32'], ['s']*4, ['e']*4, ['e.'], ['h']], [])
    gen.context['rhythms'] = []
    gen.context['indexes'] = []
    for x in range(l):
        gen.context['rhythms'].append(rhystrings[random.randint(0, len(rhystrings)-1)])
        gen.context['indexes'].append(random.random()*filelen)
        gen.context['orig_rhythms'] = gen.context['rhythms']


gen_rhythms(g, 6*4, 2)
g.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
                                      mapping_lists=[g.context['rhythms'],
                                                     g.context['indexes']],
                                      tempo=tempo,
                                      # streammode=streammodes.random,
                                      seed=seed)
g.gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
# g.streams[keys.amplitude] = Itemstream([0])
g.generate_notes()


metronome = copy.deepcopy(g)


metronome.context['rhythms'] = ['q']
metronome.context['indexes'] = [23.301317351754314]
metronome.context['orig_rhythms'] = g.context['rhythms']
metronome.streams[keys.frequency] = Itemstream([6])
metronome.streams[keys.pan] = Itemstream([90])
metronome.streams[keys.amplitude] = Itemstream([5])
metronome.streams[keys.duration] = Itemstream([.01])
metronome.streams['filepitch'] = Itemstream(['a'])
metronome.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
                                      mapping_lists=[metronome.context['rhythms'],
                                                     metronome.context['indexes']],
                                      tempo=tempo,
                                      seed=seed)
g.add_generator(metronome)
g.generate_notes()


g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']
print(g.generate_score_string())

print('seed:', seed)
x=g
# for x in [g, g2, g3]:
print(x.streams[keys.frequency].values)
print("g.context['rhythms'] =", x.context['rhythms'])
print("g.context['indexes'] =", x.context['indexes'])
print(x.context['tuplestream'].seed)

cs_utils.play_csound("generic-index.orc", g, silent=True)
