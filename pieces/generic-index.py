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

# random.seed(12)
random.seed(11)

filelen = 35
tempo = 120

pitches_to_files = {
    'a':'a.wav',
    'a': 'a.wav',
    'a': 'a.wav',
    'a': 'a.wav',
    'a': 'a.wav',
    'a': 'a.wav',
    'a': 'a.wav',
    'a': 'a.wav',
    'a': 'a.wav'
}

# filelen = 162
def post_process(note, context):
    item = context['tuplestream'].get_next_value()
    indx = context['indexes'].index(item[keys.index])
    orig_rhythm = context['orig_rhythms'][indx]
    note.rhythm = utils.rhythm_to_duration(item[keys.rhythm], context['tuplestream'].tempo)
    note.pfields[keys.index] = item[keys.index]
    note.pfields['orig_rhythm'] = utils.rhythm_to_duration(orig_rhythm, context['tuplestream'].tempo)
    # note.pfields[keys.frequency] = context['tuplestream'].tempo / utils.quarter_duration_to_tempo(.697-.018)
    note.pfields[keys.frequency] = 1
    pass


g = Generator(
    streams=OrderedDict([
        (keys.instrument, Itemstream([1])),
        (keys.duration, lambda note:note.pfields['orig_rhythm']),
        (keys.amplitude, Itemstream([3])),
        (keys.frequency, Itemstream([1], notetype=notetypes.number)),
        (keys.pan, Itemstream([45])),
        (keys.distance, Itemstream([10])),
        (keys.percent, Itemstream([.01])),
        ('inst_file', Itemstream(["/Users/ben/Music/_toSort/2017.06.04.SlidesIdea.wav",
                                  "/Users/ben/Music/_toSort/Ebow Tone Row.1_00.wav"], notetype=notetypes.path))
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


def gen_rhythms(gen, l, opt=1):
    if opt == 1:
        rhystrings = sum([['q'], ['s'] * 5, ['e'], ['e.'], ['h']], [])
    else:
        rhystrings = sum([['32'], ['s'] * 4, ['e'] * 4, ['e.'], ['h']], [])
    gen.context['rhythms'] = []
    gen.context['indexes'] = []
    for x in range(l):
        gen.context['rhythms'].append(rhystrings[random.randint(0, len(rhystrings)-1)])
        gen.context['indexes'].append(random.random()*filelen)
        gen.context['orig_rhythms'] = gen.context['rhythms']


gen_rhythms(g, 30)
g.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
                                      mapping_lists=[g.context['rhythms'],
                                                     g.context['indexes']],
                                      tempo=tempo,
                                      streammode=streammodes.random)
#
g2 = copy.deepcopy(g)
gen_rhythms(g2, 2)
g2.streams[keys.pan] = Itemstream([0])
g2.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
                                      mapping_lists=[g2.context['rhythms'],
                                                     g2.context['indexes']],
                                      tempo=tempo*.5,
                                      streammode=streammodes.random)
#
g3 = copy.deepcopy(g2)
gen_rhythms(g3, 2)
g3.streams[keys.pan] = Itemstream([90])
g3.context['tuplestream'] = Itemstream(mapping_keys=[keys.rhythm, keys.index],
                                      mapping_lists=[g3.context['rhythms'],
                                                     g3.context['indexes']],
                                      tempo=tempo*.5)

g.add_generator(g2)
g.add_generator(g3)
g.gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
g.streams[keys.amplitude] = Itemstream([.5])
g.generate_notes()

g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']

# print(g.generate_score_string())
cs_utils.play_csound("generic-index.orc", g)
