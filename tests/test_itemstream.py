import unittest
from thuja.notegenerator import *
from thuja.itemstream import streammodes, notetypes
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
        g = NoteGenerator(
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
        g = NoteGenerator(
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


    # ------------------------------------------------------------------ #
    # Tuple streams: mapping_keys/mapping_lists get_next_value  (#35)
    # ------------------------------------------------------------------ #

    def test_mapping_stream_get_next_value_returns_correct_dict(self):
        # get_next_value() on a mapping stream returns a dict whose keys
        # match mapping_keys and whose values come from the corresponding list.
        rhythms = ['h', 'q', 'e']
        indexes = [1.0, 2.0, 3.0]
        stream = Itemstream(
            mapping_keys=[keys.rhythm, keys.index],
            mapping_lists=[rhythms, indexes]
        )
        first = stream.get_next_value()
        self.assertEqual(first[keys.rhythm], 'h')
        self.assertAlmostEqual(first[keys.index], 1.0)

    def test_mapping_stream_values_advance_in_sync(self):
        # Each call to get_next_value() advances both lists together —
        # the nth call always returns the nth pair, never mixing pairs.
        rhythms = ['h', 'q', 'e']
        indexes = [1.0, 2.0, 3.0]
        stream = Itemstream(
            mapping_keys=[keys.rhythm, keys.index],
            mapping_lists=[rhythms, indexes]
        )
        results = [stream.get_next_value() for _ in range(3)]
        self.assertEqual(results[0][keys.rhythm], 'h')
        self.assertAlmostEqual(results[0][keys.index], 1.0)
        self.assertEqual(results[1][keys.rhythm], 'q')
        self.assertAlmostEqual(results[1][keys.index], 2.0)
        self.assertEqual(results[2][keys.rhythm], 'e')
        self.assertAlmostEqual(results[2][keys.index], 3.0)

    def test_mapping_stream_wraps_in_sequence_mode(self):
        # After the last pair, the stream wraps back to the first pair.
        rhythms = ['h', 'q']
        indexes = [1.0, 2.0]
        stream = Itemstream(
            mapping_keys=[keys.rhythm, keys.index],
            mapping_lists=[rhythms, indexes],
            streammode=streammodes.sequence
        )
        # Exhaust + one more
        stream.get_next_value()
        stream.get_next_value()
        wrapped = stream.get_next_value()
        self.assertEqual(wrapped[keys.rhythm], 'h')
        self.assertAlmostEqual(wrapped[keys.index], 1.0)

    def test_mapping_stream_shorter_list_wraps_independently(self):
        # When lists have different lengths, the shorter one wraps to fill
        # the longer one's length (Itemstream constructor pads with wrap).
        rhythms = ['h', 'q', 'e', 'w']   # length 4
        indexes = [1.0, 2.0]              # length 2 — wraps: 1.0, 2.0, 1.0, 2.0
        stream = Itemstream(
            mapping_keys=[keys.rhythm, keys.index],
            mapping_lists=[rhythms, indexes]
        )
        results = [stream.get_next_value() for _ in range(4)]
        self.assertEqual([r[keys.rhythm] for r in results], ['h', 'q', 'e', 'w'])
        self.assertEqual([r[keys.index] for r in results], [1.0, 2.0, 1.0, 2.0])

    def test_mapping_stream_in_post_process_sets_pfields(self):
        # The dominant real-world pattern: a tuple stream lives in context
        # and a post_process reads from it to set note.rhythm and a custom pfield.
        # This is the core of every index-based granular synthesis piece.
        rhythms = ['h', 'q', 'e']
        indexes = [0.5, 1.5, 2.5]
        tempo = 120

        def parse_tuple(note, context):
            item = context['tuplestream'].get_next_value()
            note.rhythm = utils.rhythm_to_duration(item[keys.rhythm], tempo)
            note.pfields[keys.index] = item[keys.index]

        gen = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([0.5])),
            ]),
            pfields=[keys.instrument, keys.start_time, keys.duration, keys.index],
            note_limit=3,
            post_processes=[parse_tuple],
            init_context={
                'tuplestream': Itemstream(
                    mapping_keys=[keys.rhythm, keys.index],
                    mapping_lists=[rhythms, indexes],
                    tempo=tempo
                )
            }
        )
        gen.generate_notes()

        # Each note should have the index from the corresponding tuple
        index_values = [float(note.split()[3]) for note in gen.notes]
        self.assertAlmostEqual(index_values[0], 0.5)
        self.assertAlmostEqual(index_values[1], 1.5)
        self.assertAlmostEqual(index_values[2], 2.5)

    # ------------------------------------------------------------------ #
    # streammode=random  (#31)
    # ------------------------------------------------------------------ #

    def test_random_streammode_values_come_from_defined_set(self):
        # random mode returns values drawn from the stream's value list.
        allowed = {'a', 'b', 'c', 'd'}
        stream = Itemstream(list(allowed), streammode=streammodes.random)
        for _ in range(40):
            self.assertIn(stream.get_next_value(), allowed)

    def test_random_streammode_allows_value_repetition(self):
        # Unlike heap, random mode can return the same value on consecutive calls.
        # With a 2-item list and 20 draws, repetition is statistically certain.
        stream = Itemstream(['x', 'y'], streammode=streammodes.random, seed=42)
        draws = [stream.get_next_value() for _ in range(20)]
        # If every adjacent pair were different, the list would perfectly alternate.
        # With random mode, at least one repeat must appear.
        has_repeat = any(draws[i] == draws[i + 1] for i in range(len(draws) - 1))
        self.assertTrue(has_repeat, "random mode should allow consecutive repeats")

    # ------------------------------------------------------------------ #
    # heap exhaustion and refill  (#31)
    # ------------------------------------------------------------------ #

    def test_heap_streammode_no_repeat_within_one_cycle(self):
        # heap mode exhausts all values before repeating any.
        # Over exactly N draws from an N-item stream, each value appears exactly once.
        values = ['a', 'b', 'c', 'd', 'e']
        stream = Itemstream(values, streammode=streammodes.heap, seed=42)
        draws = [stream.get_next_value() for _ in range(len(values))]
        self.assertEqual(sorted(draws), sorted(values))

    def test_heap_streammode_refills_after_exhaustion(self):
        # After all N values are drawn, the heap refills and a second cycle begins.
        # Both cycles contain all N values in (potentially different) random order.
        values = ['a', 'b', 'c']
        stream = Itemstream(values, streammode=streammodes.heap, seed=42)
        first_cycle = [stream.get_next_value() for _ in range(len(values))]
        second_cycle = [stream.get_next_value() for _ in range(len(values))]
        self.assertEqual(sorted(first_cycle), sorted(values))
        self.assertEqual(sorted(second_cycle), sorted(values))

    # ------------------------------------------------------------------ #
    # seed constructor param  (#31)
    # ------------------------------------------------------------------ #

    def test_seed_param_produces_same_heap_sequence(self):
        # Two Itemstreams with the same seed and same values produce identical sequences.
        values = ['a', 'b', 'c', 'd', 'e', 'f']
        s1 = Itemstream(values, streammode=streammodes.heap, seed=42)
        s2 = Itemstream(values, streammode=streammodes.heap, seed=42)
        draws_1 = [s1.get_next_value() for _ in range(len(values) * 3)]
        draws_2 = [s2.get_next_value() for _ in range(len(values) * 3)]
        self.assertEqual(draws_1, draws_2)

    def test_seed_param_produces_same_random_sequence(self):
        # Same guarantee applies to random mode: same seed → same sequence.
        values = ['a', 'b', 'c', 'd']
        s1 = Itemstream(values, streammode=streammodes.random, seed=99)
        s2 = Itemstream(values, streammode=streammodes.random, seed=99)
        draws_1 = [s1.get_next_value() for _ in range(20)]
        draws_2 = [s2.get_next_value() for _ in range(20)]
        self.assertEqual(draws_1, draws_2)

    def test_different_seeds_produce_different_sequences(self):
        # Two streams with different seeds should (with high probability) produce
        # different orderings over 3 heap cycles.
        values = ['a', 'b', 'c', 'd', 'e', 'f']
        s1 = Itemstream(values, streammode=streammodes.heap, seed=1)
        s2 = Itemstream(values, streammode=streammodes.heap, seed=9999)
        draws_1 = [s1.get_next_value() for _ in range(len(values) * 3)]
        draws_2 = [s2.get_next_value() for _ in range(len(values) * 3)]
        self.assertNotEqual(draws_1, draws_2)


if __name__ == '__main__':
    unittest.main()
