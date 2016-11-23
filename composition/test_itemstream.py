import unittest
from itemstream import Itemstream
from score import global_score

import numpy as np

class TestItemstreams(unittest.TestCase):
    def test_indexpoints(self):
        tuplestream = Itemstream(
            [{"rhy": "h", "indx": .769}, {"rhy": "h", "indx": 1.95}, {"rhy": "w", "indx": 3.175},
             {"rhy": "h", "indx": 5.54}, {"rhy": "h", "indx": 6.67}, {"rhy": "h", "indx": 8.0}]
        )
        amps = Itemstream([1])
        pitches = Itemstream(sum([
            ['c1', 'c', 'c', 'd', 'c1', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'
        global_score.reinit(None, [amps, pitches, tuplestream], note_limit=(len(pitches.values) * 2))
        global_score.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        global_score.durstream = Itemstream([.1])
        global_score.generate_notes()
        score_string = global_score.generate_score_string()
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
        global_score.reinit(rhythms, [amps, pitches], note_limit=(len(pitches.values) * 2))
        global_score.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        global_score.durstream = Itemstream([.1])
        global_score.instr = 3
        global_score.generate_notes()

        output = ""
        for x in range(len(s.gen_lines)):
            output += global_score.gen_lines[x]
        for x in range(len(s.notes)):
            output += global_score.notes[x]

        rhythms = Itemstream(['e'] * 12, 'sequence', tempo=[120, 60, 30])
        rhythms.notetype = 'rhythm'
        global_score.rhythmstream = rhythms
        pitches = Itemstream(sum([
            ['fs6'],
        ], []))
        pitches.notetype = 'pitch'
        global_score.streams[1] = pitches
        global_score.note_limit = 32
        # reset time
        global_score.starttime = 0.0
        global_score.curtime = s.starttime
        global_score.instr = 3
        global_score.generate_notes()
        for x in range(len(global_score.notes)):
            output += global_score.notes[x]
        score  = global_score.generate_score_string()
        self.assertTrue(score is not None)
        self.assertTrue(len(score.split('\n')) == 54)

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

        global_score.reinit(rhythms, [amps, pitches, pan, dist, pct], note_limit=240)
        global_score.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        global_score.durstream = Itemstream([.1])
        global_score.instr = 3
        global_score.generate_notes()

        global_score.rhythmstream.tempo = np.linspace(480, 30, 32).tolist() + np.linspace(30, 480, 32).tolist()
        global_score.streams[2] = Itemstream([90])
        global_score.generate_notes()

        output = ""
        for x in range(len(global_score.gen_lines)):
            output += global_score.gen_lines[x]
        for x in range(len(global_score.notes)):
            output += global_score.notes[x]
        global_score.end_lines = ['i99 0 ' + str(global_score.score_dur) + '\n']
        score = global_score.generate_score_string()
        self.assertTrue(score is not None)
        self.assertTrue(len(score.split('\n')) == 487)

    def test_basiccase(self):
        rhythms = Itemstream(['q'], 'sequence', tempo=[120, 60, 30])
        rhythms.notetype = 'rhythm'
        amps = Itemstream([1])

        pitches = Itemstream(sum([
            ['c4', 'c', 'c', 'd', 'c5', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'
        global_score.reinit(rhythms, [amps, pitches], note_limit=(len(pitches.values) * 2))
        global_score.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        global_score.durstream = Itemstream([.1])
        global_score.instr = 3
        global_score.generate_notes()

        output = ""
        for x in range(len(global_score.gen_lines)):
            output += global_score.gen_lines[x]
        for x in range(len(global_score.notes)):
            output += global_score.notes[x]

        rhythms = Itemstream(['e'] * 12, 'sequence', tempo=[120, 60, 30])
        rhythms.notetype = 'rhythm'
        global_score.rhythmstream = rhythms
        pitches = Itemstream(sum([
            ['fs6'],
        ], []))
        pitches.notetype = 'pitch'
        global_score.streams[1] = pitches
        global_score.note_limit = 32
        # reset time
        global_score.starttime = 0.0
        global_score.curtime = global_score.starttime
        global_score.instr = 3
        global_score.generate_notes()
        for x in range(len(global_score.notes)):
            output += global_score.notes[x]
        score = global_score.generate_score_string()
        self.assertTrue(score is not None)
        self.assertTrue(len(score.split('\n')) == 54)


if __name__ == '__main__':
    unittest.main()
