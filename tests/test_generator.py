from __future__ import print_function
import unittest
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
import thuja.utils as utils

from collections import OrderedDict
import numpy as np

rhythm = Itemstream('w h q e s e. w+q'.split())
rhythm.notetype = 'rhythm'

class TestGenerators(unittest.TestCase):

    def test_callables(self):
        tuplestream = Itemstream(
            [{keys.rhythm: "h", "indx": .769}, {keys.rhythm: "h", "indx": 1.95}, {keys.rhythm: "w", "indx": 3.175},
             {keys.rhythm: "h", "indx": 5.54}, {keys.rhythm: "h", "indx": 6.67}, {keys.rhythm: "h", "indx": 8.0}]
        )

        pitches = Itemstream('c1 c c d c c c d'.split())
        pitches.notetype = 'pitch'

        def f(note):
            return note.rhythm * 2

        g = Generator(
            pfields=[
                keys.instrument,
                keys.start_time,
                keys.duration,
                keys.amplitude,
                keys.frequency,
                'indx'
                ],
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, f),
                ('rhy|indx', tuplestream),
                (keys.amplitude, Itemstream([1])),
                (keys.frequency, pitches)
            ]),
            note_limit=(len(pitches.values) * 2)
        )

        g.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        g.generate_notes()
        score_string = g.generate_score_string()
        self.assertTrue(score_string is not None)
        self.assertTrue(len(score_string.split('\n')) == 22)

    def test_callables_lambda(self):
        tuplestream = Itemstream(
            [{keys.rhythm: "h", "indx": .769}, {keys.rhythm: "h", "indx": 1.95}, {keys.rhythm: "w", "indx": 3.175},
             {keys.rhythm: "h", "indx": 5.54}, {keys.rhythm: "h", "indx": 6.67}, {keys.rhythm: "h", "indx": 8.0}]
        )
        pitches = Itemstream(sum([
            ['c1', 'c', 'c', 'd', 'c1', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'

        g = Generator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, lambda note:note.rhythm*2),
                ('rhy|indx', tuplestream),
                (keys.amplitude, Itemstream([1])),
                (keys.frequency, pitches)
            ]),
            pfields=[
                keys.instrument,
                keys.start_time,
                keys.duration,
                keys.amplitude,
                keys.frequency,
                'indx'
            ],
            note_limit=(len(pitches.values) * 2)
        )

        g.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        g.generate_notes()
        score_string = g.generate_score_string()
        self.assertTrue(score_string is not None)
        self.assertTrue(len(score_string.split('\n')) == 22)

    def test_callables_postprocesses(self):
        rhythms = 'h h w h h h'.split()
        indexes = [.769, 1.95, 3.175, 5.54, 6.67, 8.0]
        tuplestream = Itemstream(mapping_keys=[keys.rhythm, keys.index], mapping_lists=[rhythms, indexes])
        pitches = Itemstream(sum([
            ['c1', 'c', 'c', 'd', 'c1', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'

        def post_processs(note):
            indx = g.context['indexstream'].get_next_value()
            item = g.context['tuplestream'].values[indx]
            note.rhythm = utils.rhythm_to_duration(item[keys.rhythm], g.context['tuplestream'].tempo)
            note.pfields[keys.index] = item[keys.index]

        g = Generator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, lambda note:note.rhythm*2),
                (keys.amplitude, Itemstream([1])),
                (keys.frequency, pitches)
            ]),
            pfields=[
                keys.instrument,
                keys.start_time,
                keys.duration,
                keys.amplitude,
                keys.frequency,
                'indx'
            ],
            note_limit=(len(pitches.values) * 2),
            post_processes=[post_processs]
        )

        g.context['indexstream'] = Itemstream([1, 1, 1, 4, 5])
        g.context['tuplestream'] = tuplestream

        g.gen_lines = [';sine\n',
                       'f 1 0 16384 10 1\n',
                       ';saw',
                       'f 2 0 256 7 0 128 1 0 -1 128 0\n',
                       ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        g.generate_notes()
        score_string = g.generate_score_string()
        self.assertTrue(score_string is not None)
        self.assertTrue(len(score_string.split('\n')) == 22)

    def test_indexpoints(self):
        tuplestream = Itemstream(
            [{keys.rhythm: "h", "indx": .769}, {keys.rhythm: "h", "indx": 1.95}, {keys.rhythm: "w", "indx": 3.175},
             {keys.rhythm: "h", "indx": 5.54}, {keys.rhythm: "h", "indx": 6.67}, {keys.rhythm: "h", "indx": 8.0}]
        )
        pitches = Itemstream(sum([
            ['c1', 'c', 'c', 'd', 'c1', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'

        g = Generator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([.1])),
                ('rhy|indx', tuplestream),
                (keys.amplitude, Itemstream([1])),
                (keys.frequency, pitches)
            ]),
            pfields=[
                keys.instrument,
                keys.start_time,
                keys.duration,
                keys.amplitude,
                keys.frequency,
                'indx'
                ],
            note_limit=(len(pitches.values) * 2)
        )

        g.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        g.generate_notes()
        score_string = g.generate_score_string()
        self.assertTrue(score_string is not None)
        self.assertTrue(len(score_string.split('\n')) == 22)

    def test_basiccase(self):
        rhythms = Itemstream(['q','32'], 'sequence', tempo=60)
        rhythms.notetype = 'rhythm'
        amps = Itemstream([1])
        pitches = Itemstream(sum([
            ['c4', 'c', 'c', 'd', 'c5', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'

        g = Generator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([.1])),
                (keys.rhythm, rhythms),
                (keys.amplitude, amps),
                (keys.frequency, pitches)
            ]),
            note_limit=(len(pitches.values) * 2)
        )

        g.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        g.generate_notes()

        output = ""
        for x in range(len(g.gen_lines)):
            output += g.gen_lines[x]
        for x in range(len(g.notes)):
            output += g.notes[x]

        score = g.generate_score_string()
        self.assertTrue(score is not None)
        print(len(score.split('\n')))
        self.assertTrue(len(score.split('\n')) == 22)

    def test_tempo(self):
        rhythms = Itemstream(['e'] * 60, 'sequence',
                             tempo=np.linspace(120, 480, 32).tolist() + np.linspace(480, 120, 32).tolist())
        rhythms.notetype = 'rhythm'
        amps = Itemstream([3])
        pitches = Itemstream(sum([
            ['c4', 'd', 'e', 'f', 'g'],
        ], []))
        # pitches.streammode = 'heap'
        pitches.notetype = 'pitch'
        pan = Itemstream([0])
        dist = Itemstream([10])
        pct = Itemstream([.1])

        # global_score.reinit(rhythms, [amps, pitches, pan, dist, pct], note_limit=240)
        g = Generator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([.1])),
                (keys.rhythm, rhythms),
                (keys.amplitude, amps),
                (keys.frequency, pitches),
                (keys.pan, pan),
                (keys.distance, dist),
                (keys.percent, pct)
            ]),
            note_limit=240
        )
        g.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                                  'f 3 0 256 7 1 128 1 0 -1 128 -1\n']

        g.generate_notes()
        g.streams[keys.rhythm].tempo = np.linspace(480, 30, 32).tolist() + np.linspace(30, 480, 32).tolist()
        g.streams[keys.pan] = Itemstream([90])
        g.generate_notes()

        g.end_lines = ['i99 0 ' + str(g.score_dur) + '\n']

        score = g.generate_score_string()
        self.assertTrue(score is not None)
        self.assertTrue(len(score.split('\n')) == 487)


    def test_literals(self):
        rhythms = Itemstream(['e'] * 60, 'sequence',
                             tempo=np.linspace(120, 480, 32).tolist() + np.linspace(480, 120, 32).tolist())
        rhythms.notetype = 'rhythm'
        amps = Itemstream([3])
        pitches = Itemstream(sum([
            ['c4', 'd', 'e', 'f', 'g'],
        ], []))
        pitches.streammode = 'heap'
        pitches.notetype = 'pitch'
        pan = 0
        dist = 10
        pct = .1

        g = Generator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([.1])),
                (keys.rhythm, rhythms),
                (keys.amplitude, amps),
                (keys.frequency, pitches),
                (keys.pan, pan),
                (keys.distance, dist),
                (keys.percent, pct)
            ]),
            note_limit=240
        )
        g.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']

        g.generate_notes()
        g.streams[keys.rhythm].tempo = np.linspace(480, 30, 32).tolist() + np.linspace(30, 480, 32).tolist()
        g.streams[keys.pan] = 90
        g.generate_notes()


        g.end_lines = ['i99 0 ' + str(g.score_dur) + '\n']

        score = g.generate_score_string()
        self.assertTrue(score is not None)
        self.assertTrue(len(score.split('\n')) == 487)

if __name__ == '__main__':
    unittest.main()
