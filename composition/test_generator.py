import unittest
from itemstream import Itemstream
from score import global_score
from generator import Generator
from generator import keys
from collections import OrderedDict
import numpy as np

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
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, f),
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
        rhythms = Itemstream(['q'], 'sequence', tempo=[120, 60, 30])
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
        print len(score.split('\n'))
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

        output = ""
        for x in range(len(global_score.gen_lines)):
            output += g.gen_lines[x]
        for x in range(len(global_score.notes)):
            output += g.notes[x]

        g.end_lines = ['i99 0 ' + str(global_score.score_dur) + '\n']

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

        output = ""
        for x in range(len(global_score.gen_lines)):
            output += g.gen_lines[x]
        for x in range(len(global_score.notes)):
            output += g.notes[x]

        g.end_lines = ['i99 0 ' + str(global_score.score_dur) + '\n']

        score = g.generate_score_string()
        self.assertTrue(score is not None)
        self.assertTrue(len(score.split('\n')) == 487)

if __name__ == '__main__':
    unittest.main()
