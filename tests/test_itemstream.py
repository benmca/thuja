import unittest
from context import composition
from composition.itemstream import Itemstream
from composition.generator import keys
import numpy as np

class TestItemstreams(unittest.TestCase):
    def test_mappings(self):
        rhythms = 'h h w h h h'.split()
        indexes = [.769, 1.95, 3.175, 5.54, 6.67, 8.0]
        stream = Itemstream(mapping_keys=[keys.rhythm, keys.index], mapping_lists=[rhythms, indexes])
        self.assertTrue(stream.values == [
                            {keys.rhythm: "h", keys.index: .769},
                            {keys.rhythm: "h", keys.index: 1.95},
                            {keys.rhythm: "w", keys.index: 3.175},
                            {keys.rhythm: "h", keys.index: 5.54},
                            {keys.rhythm: "h", keys.index: 6.67},
                            {keys.rhythm: "h", keys.index: 8.0}])

        rhythms = 'h h w h h w q'.split()
        indexes = [.769, 1.95, 3.175, 5.54, 6.67, 8.0]
        stream = Itemstream(mapping_keys=[keys.rhythm, keys.index], mapping_lists=[rhythms, indexes])
        self.assertTrue(stream.values == [
            {keys.rhythm: "h", keys.index: .769},
            {keys.rhythm: "h", keys.index: 1.95},
            {keys.rhythm: "w", keys.index: 3.175},
            {keys.rhythm: "h", keys.index: 5.54},
            {keys.rhythm: "h", keys.index: 6.67},
            {keys.rhythm: "w", keys.index: 8.0},
            {keys.rhythm: "q", keys.index: .769}
        ])

        rhythms = 'h h w h h w q'.split()
        indexes = [.769, 1.95, 3.175, 5.54, 6.67, 8.0]
        amps = [1, 0]
        stream = Itemstream(mapping_keys=[keys.rhythm, keys.index, keys.amplitude], mapping_lists=[rhythms, indexes, amps])
        self.assertTrue(stream.values == [
            {keys.rhythm: "h", keys.index: .769, keys.amplitude: 1},
            {keys.rhythm: "h", keys.index: 1.95, keys.amplitude: 0},
            {keys.rhythm: "w", keys.index: 3.175, keys.amplitude: 1},
            {keys.rhythm: "h", keys.index: 5.54, keys.amplitude: 0},
            {keys.rhythm: "h", keys.index: 6.67, keys.amplitude: 1},
            {keys.rhythm: "w", keys.index: 8.0, keys.amplitude: 0},
            {keys.rhythm: "q", keys.index: .769, keys.amplitude: 1}
        ])

    # TODO  fix these?  
    #
    # def test_basiccase(self):
    #     rhythms = Itemstream(['q'], 'sequence', tempo=[120, 60, 30])
    #     rhythms.notetype = 'rhythm'
    #     amps = Itemstream([1])
    #
    #     pitches = Itemstream(sum([
    #         ['c4', 'c', 'c', 'd', 'c5', 'c', 'c', 'd'],
    #     ], []))
    #     pitches.notetype = 'pitch'
    #     global_score.reinit(rhythms, [amps, pitches], note_limit=(len(pitches.values) * 2))
    #     global_score.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
    #                    'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
    #     global_score.durstream = Itemstream([.1])
    #     global_score.instr = 3
    #     global_score.generate_notes()
    #
    #     output = ""
    #     for x in range(len(s.gen_lines)):
    #         output += global_score.gen_lines[x]
    #     for x in range(len(s.notes)):
    #         output += global_score.notes[x]
    #
    #     rhythms = Itemstream(['e'] * 12, 'sequence', tempo=[120, 60, 30])
    #     rhythms.notetype = 'rhythm'
    #     global_score.rhythmstream = rhythms
    #     pitches = Itemstream(sum([
    #         ['fs6'],
    #     ], []))
    #     pitches.notetype = 'pitch'
    #     global_score.streams[1] = pitches
    #     global_score.note_limit = 32
    #     # reset time
    #     global_score.starttime = 0.0
    #     global_score.curtime = s.starttime
    #     global_score.instr = 3
    #     global_score.generate_notes()
    #     for x in range(len(global_score.notes)):
    #         output += global_score.notes[x]
    #     score  = global_score.generate_score_string()
    #     self.assertTrue(score is not None)
    #     self.assertTrue(len(score.split('\n')) == 54)
    #
    # def test_tempo(self):
    #     rhythms = Itemstream(['e'] * 60, 'sequence',
    #                          tempo=np.linspace(120, 480, 32).tolist() + np.linspace(480, 120, 32).tolist())
    #     rhythms.notetype = 'rhythm'
    #     amps = Itemstream([3])
    #     pitches = Itemstream(sum([
    #         ['c4', 'd', 'e', 'f', 'g'],
    #     ], []))
    #     # pitches.streammode = 'heap'
    #     pitches.notetype = 'pitch'
    #     pan = Itemstream([0])
    #     dist = Itemstream([10])
    #     pct = Itemstream([.1])
    #
    #     global_score.reinit(rhythms, [amps, pitches, pan, dist, pct], note_limit=240)
    #     global_score.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
    #                    'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
    #     global_score.durstream = Itemstream([.1])
    #     global_score.instr = 3
    #     global_score.generate_notes()
    #
    #     global_score.rhythmstream.tempo = np.linspace(480, 30, 32).tolist() + np.linspace(30, 480, 32).tolist()
    #     global_score.streams[2] = Itemstream([90])
    #     global_score.generate_notes()
    #
    #     output = ""
    #     for x in range(len(global_score.gen_lines)):
    #         output += global_score.gen_lines[x]
    #     for x in range(len(global_score.notes)):
    #         output += global_score.notes[x]
    #     global_score.end_lines = ['i99 0 ' + str(global_score.score_dur) + '\n']
    #     score = global_score.generate_score_string()
    #     self.assertTrue(score is not None)
    #     self.assertTrue(len(score.split('\n')) == 487)
    #
    # def test_basiccase(self):
    #     rhythms = Itemstream(['q'], 'sequence', tempo=[120, 60, 30])
    #     rhythms.notetype = 'rhythm'
    #     amps = Itemstream([1])
    #
    #     pitches = Itemstream(sum([
    #         ['c4', 'c', 'c', 'd', 'c5', 'c', 'c', 'd'],
    #     ], []))
    #     pitches.notetype = 'pitch'
    #     global_score.reinit(rhythms, [amps, pitches], note_limit=(len(pitches.values) * 2))
    #     global_score.gen_lines = [';sine\n', 'f 1 0 16384 10 1\n', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0\n', ';pulse\n',
    #                    'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
    #     global_score.durstream = Itemstream([.1])
    #     global_score.instr = 3
    #     global_score.generate_notes()
    #
    #     output = ""
    #     for x in range(len(global_score.gen_lines)):
    #         output += global_score.gen_lines[x]
    #     for x in range(len(global_score.notes)):
    #         output += global_score.notes[x]
    #
    #     rhythms = Itemstream(['e'] * 12, 'sequence', tempo=[120, 60, 30])
    #     rhythms.notetype = 'rhythm'
    #     global_score.rhythmstream = rhythms
    #     pitches = Itemstream(sum([
    #         ['fs6'],
    #     ], []))
    #     pitches.notetype = 'pitch'
    #     global_score.streams[1] = pitches
    #     global_score.note_limit = 32
    #     # reset time
    #     global_score.starttime = 0.0
    #     global_score.curtime = global_score.starttime
    #     global_score.instr = 3
    #     global_score.generate_notes()
    #     for x in range(len(global_score.notes)):
    #         output += global_score.notes[x]
    #     score = global_score.generate_score_string()
    #     self.assertTrue(score is not None)
    #     self.assertTrue(len(score.split('\n')) == 54)


if __name__ == '__main__':
    unittest.main()
