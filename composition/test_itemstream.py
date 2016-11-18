import unittest
from itemstream import Itemstream
from score import Score
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
        s = Score(None, [amps, pitches, tuplestream], note_limit=(len(pitches.values) * 2))
        s.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        s.durstream = Itemstream([.1])
        s.generate_notes()
        score  = s.generate_score_string()
        self.assertTrue(score is not None)
        self.assertTrue(len(score.split('\n')) == 22)

    def test_basiccase(self):
        rhythms = Itemstream(['q'], 'sequence', tempo=[120, 60, 30])
        rhythms.notetype = 'rhythm'
        amps = Itemstream([1])

        pitches = Itemstream(sum([
            ['c4', 'c', 'c', 'd', 'c5', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'
        s = Score(rhythms, [amps, pitches], note_limit=(len(pitches.values) * 2))
        s.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        s.durstream = Itemstream([.1])
        s.instr = 3
        s.generate_notes()

        output = ""
        for x in range(len(s.gen_lines)):
            output += s.gen_lines[x]
        for x in range(len(s.notes)):
            output += s.notes[x]

        rhythms = Itemstream(['e'] * 12, 'sequence', tempo=[120, 60, 30])
        rhythms.notetype = 'rhythm'
        s.rhythmstream = rhythms
        pitches = Itemstream(sum([
            ['fs6'],
        ], []))
        pitches.notetype = 'pitch'
        s.streams[1] = pitches
        s.note_limit = 32
        # reset time
        s.starttime = 0.0
        s.curtime = s.starttime
        s.instr = 3
        s.generate_notes()
        for x in range(len(s.notes)):
            output += s.notes[x]
        score  = s.generate_score_string()
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

        s = Score(rhythms, [amps, pitches, pan, dist, pct], note_limit=240)
        s.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        s.durstream = Itemstream([.1])
        s.instr = 3
        s.generate_notes()

        s.rhythmstream.tempo = np.linspace(480, 30, 32).tolist() + np.linspace(30, 480, 32).tolist()
        s.streams[2] = Itemstream([90])
        s.generate_notes()

        output = ""
        for x in range(len(s.gen_lines)):
            output += s.gen_lines[x]
        for x in range(len(s.notes)):
            output += s.notes[x]
        s.end_lines = ['i99 0 ' + str(s.score_dur) + '\n']
        score  = s.generate_score_string()
        self.assertTrue(score is not None)
        self.assertTrue(len(score.split('\n')) == 487)

if __name__ == '__main__':
    unittest.main()
