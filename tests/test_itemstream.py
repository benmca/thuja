import unittest
from thuja.itemstream import *
from thuja.generator import *
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
        stream = Itemstream(mapping_keys=[keys.rhythm, keys.index, keys.amplitude],
                            mapping_lists=[rhythms, indexes, amps])
        self.assertTrue(stream.values == [
            {keys.rhythm: "h", keys.index: .769, keys.amplitude: 1},
            {keys.rhythm: "h", keys.index: 1.95, keys.amplitude: 0},
            {keys.rhythm: "w", keys.index: 3.175, keys.amplitude: 1},
            {keys.rhythm: "h", keys.index: 5.54, keys.amplitude: 0},
            {keys.rhythm: "h", keys.index: 6.67, keys.amplitude: 1},
            {keys.rhythm: "w", keys.index: 8.0, keys.amplitude: 0},
            {keys.rhythm: "q", keys.index: .769, keys.amplitude: 1}
        ])

    def test_basiccase(self):
        pitches = Itemstream(['c4', 'c', 'c', 'd', 'c5', 'c', 'c', 'd'], notetype=notetypes.pitch)
        g = Generator(
            streams=[
                (keys.instrument, 1),
                (keys.rhythm, Itemstream(['q'], 'sequence', tempo=[120, 60, 30], notetype=notetypes.rhythm)),
                (keys.duration, .1),
                (keys.amplitude, 1),
                (keys.frequency, pitches),
            ],
            note_limit=(16),
            gen_lines=[';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']
        )
        g.generate_notes()

        output = ""
        for x in range(len(g.gen_lines)):
            output += (g.gen_lines[x] + '\n')
        for x in range(len(g.notes)):
            output += g.notes[x]

        rhythms = Itemstream(['e'] * 12, 'sequence', tempo=[120, 60, 30], notetype=notetypes.rhythm)
        g.streams[keys.rhythm] = rhythms
        pitches = Itemstream(['fs6'], notetype=notetypes.pitch)
        g.streams[keys.frequency] = pitches
        g.note_limit = 32

        # reset time
        g.starttime = 0.0
        g.curtime = g.starttime
        g.instr = 3
        g.generate_notes()

        for x in range(len(g.notes)):
            output += g.notes[x]

        score = g.generate_score_string()
        # score should generate 54 lines + 1
        self.assertTrue(len(score.split('\n')) == 39)
        self.assertTrue(len(output.split('\n')) == 55)

    def test_tempo(self):
        g = Generator(
            streams=[
                (keys.instrument, 3),
                (keys.rhythm, Itemstream(['e'] * 60, 'sequence',
                                         tempo=np.linspace(120, 480, 32).tolist() + np.linspace(480, 120, 32).tolist(),
                                         notetype=notetypes.rhythm)),
                (keys.duration, .1),
                (keys.amplitude, 3),
                (keys.frequency, Itemstream(['c4', 'd', 'e', 'f', 'g'], notetype=notetypes.pitch)),
                (keys.pan, 0),
                (keys.distance, 10),
                (keys.percent, .1)
            ],
            note_limit=(240),
            gen_lines=[';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']
        )
        g.generate_notes()

        g.streams[keys.rhythm].tempo = np.linspace(480, 30, 32).tolist() + np.linspace(30, 480, 32).tolist()
        g.streams[keys.pan] = Itemstream([90])
        g.generate_notes()

        output = ""
        for x in range(len(g.gen_lines)):
            output += g.gen_lines[x]
        for x in range(len(g.notes)):
            output += g.notes[x]
        g.end_lines = ['i99 0 ' + str(g.score_dur)]

        score = g.generate_score_string()
        self.assertTrue(len(score.split('\n')) == 248)


if __name__ == '__main__':
    unittest.main()
