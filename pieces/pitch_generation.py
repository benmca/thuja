from thuja.itemstream import notetypes
from thuja.itemstream import streammodes
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
from collections import OrderedDict
from thuja import utils
import copy
import csnd6

import random


rhythms = Itemstream(['e.','e.','e','q.','e','q.','e','s'],
    streammode=streammodes.sequence,
    tempo=120,
    notetype=notetypes.rhythm)
amps = Itemstream([1])

pitches = Itemstream(sum([
    ['c7','d','e','f','g','a','b','c8'],
    ],[]),
    streammode=streammodes.sequence,
    notetype=notetypes.pitch
)

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
    pfields=None,
    note_limit=(len(pitches.values)*16),
    gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
)


def post_processs(note):
    if random.random() > .5:
        i = random.randint(0, len(g.streams[keys.frequency].values)-1)
        val = g.streams[keys.frequency].values[i]
        freq = utils.pc_to_freq(val, g.streams[keys.frequency].current_octave)['value']
        midinote = utils.freq_to_midi_note(freq)
        if random.random() > .6:
            if random.random() > .5:
                if random.random() > .5:
                    midinote += 2
                else:
                    midinote += 1
            else:
                if random.random() > .5:
                    midinote -= 2
                else:
                    midinote -= 1
        newfreq = utils.midinote_to_freq(midinote)
        newpc = utils.freq_to_pc(newfreq, True)
        g.streams[keys.frequency].values[i] = newpc


g.post_processes = [post_processs]

g.generate_notes()

g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']

with open ("sine.orc", "r") as f:
    orc_string=f.read()
score_string = g.generate_score_string()
cs = csnd6.Csound()
cs.CompileOrc(orc_string)
cs.ReadScore(score_string)
cs.SetOption('-odac')
cs.Start()
cs.Perform()
cs.Stop()
