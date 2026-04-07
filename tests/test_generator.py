from __future__ import print_function
import unittest
from thuja.itemstream import Itemstream, notetypes, streammodes
from thuja.notegenerator import NoteGenerator
from thuja.notegenerator import Line
from thuja.streamkeys import keys
import thuja.utils as utils

from collections import OrderedDict
import numpy as np

# rhythm = Itemstream('w h q e s e. w+q'.split())
# rhythm.notetype = 'rhythm'


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

        g = NoteGenerator(
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

        g.gen_lines = [';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']
        g.generate_notes()
        score_string = g.generate_score_string()
        self.assertTrue(score_string is not None)
        self.assertTrue(len(score_string.split('\n')) == 23)

    def test_callables_lambda(self):
        tuplestream = Itemstream(
            [{keys.rhythm: "h", "indx": .769}, {keys.rhythm: "h", "indx": 1.95}, {keys.rhythm: "w", "indx": 3.175},
             {keys.rhythm: "h", "indx": 5.54}, {keys.rhythm: "h", "indx": 6.67}, {keys.rhythm: "h", "indx": 8.0}]
        )
        pitches = Itemstream(sum([
            ['c1', 'c', 'c', 'd', 'c1', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'

        g = NoteGenerator(
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

        g.gen_lines = [';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']
        g.generate_notes()
        score_string = g.generate_score_string()
        self.assertTrue(score_string is not None)
        self.assertTrue(len(score_string.split('\n')) == 23)

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
            note.duration = note.rhythm*2

        # 2025.05.08 - with recent changes, lambda will be called before post_processes in generate_notes, so lambda
        #               expression here has no rhythm. Docs should guide users to use either post_process or lambdas,
        #               not necessarily both.
        #               TODO: Add a safeguard for this uninitiated rhythm situation once that algo is baked.
        g = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, 1),
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

        g.gen_lines = [';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']
        g.generate_notes()
        score_string = g.generate_score_string()
        self.assertTrue(score_string is not None)
        self.assertTrue(len(score_string.split('\n')) == 23)

    def test_indexpoints(self):
        tuplestream = Itemstream(
            [{keys.rhythm: "h", "indx": .769}, {keys.rhythm: "h", "indx": 1.95}, {keys.rhythm: "w", "indx": 3.175},
             {keys.rhythm: "h", "indx": 5.54}, {keys.rhythm: "h", "indx": 6.67}, {keys.rhythm: "h", "indx": 8.0}]
        )
        pitches = Itemstream(sum([
            ['c1', 'c', 'c', 'd', 'c1', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'

        g = NoteGenerator(
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

        g.gen_lines = [';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']
        g.generate_notes()
        score_string = g.generate_score_string()
        self.assertTrue(score_string is not None)
        self.assertTrue(len(score_string.split('\n')) == 23)

    def test_basiccase(self):
        rhythms = Itemstream(['q','32'], 'sequence', tempo=60)
        rhythms.notetype = 'rhythm'
        amps = Itemstream([1])
        pitches = Itemstream(sum([
            ['c4', 'c', 'c', 'd', 'c5', 'c', 'c', 'd'],
        ], []))
        pitches.notetype = 'pitch'

        g = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([.1])),
                (keys.rhythm, rhythms),
                (keys.amplitude, amps),
                (keys.frequency, pitches)
            ]),
            note_limit=(len(pitches.values) * 2)
        )

        g.gen_lines = [';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']
        g.generate_notes()

        output = ""
        for x in range(len(g.gen_lines)):
            output += g.gen_lines[x]
        for x in range(len(g.notes)):
            output += g.notes[x]

        score = g.generate_score_string()
        self.assertTrue(score is not None)
        print(len(score.split('\n')))
        self.assertTrue(len(score.split('\n')) == 23)

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
        g = NoteGenerator(
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
        g.gen_lines = [';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']

        g.generate_notes()
        g.streams[keys.rhythm].tempo = np.linspace(480, 30, 32).tolist() + np.linspace(30, 480, 32).tolist()
        g.streams[keys.pan] = Itemstream([90])
        g.generate_notes()

        g.end_lines = ['i99 0 ' + str(g.score_dur)]

        score = g.generate_score_string()
        self.assertTrue(len(score.split('\n')) == 248)


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

        g = NoteGenerator(
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
        g.gen_lines = [';sine', 'f 1 0 16384 10 1', ';saw', 'f 2 0 256 7 0 128 1 0 -1 128 0', ';pulse',
                       'f 3 0 256 7 1 128 1 0 -1 128 -1']

        g.generate_notes()
        g.streams[keys.rhythm].tempo = np.linspace(480, 30, 32).tolist() + np.linspace(30, 480, 32).tolist()
        g.streams[keys.pan] = 90
        g.generate_notes()
        g.end_lines = ['i99 0 ' + str(g.score_dur)]

        score = g.generate_score_string()
        self.assertTrue(len(score.split('\n')) == 248)




    def test_child_generators(self):
        melody_left = (
            Line().with_rhythm(Itemstream(['w'], notetype=notetypes.rhythm, streammode=streammodes.sequence))
            .with_duration(lambda note: note.rhythm * 1)
            .with_amps(1)
            .with_pitches(
                Itemstream(['c3', 'd', 'e', 'f', 'g', 'a', 'b'], notetype=notetypes.pitch,
                           streammode=streammodes.sequence))
            .with_pan(Itemstream(['10'], notetype=notetypes.number, streammode=streammodes.heap))
            .with_dist(5)
            .with_percent(.04)
            .with_instr(2)
        )
        melody_left.time_limit = 20


        melody_right = (
            Line().with_rhythm(Itemstream(['s'], notetype=notetypes.rhythm, streammode=streammodes.sequence))
            .with_duration(lambda note: note.rhythm * 1)
            .with_amps(1)
            .with_pitches(
                Itemstream(['c3', 'g'], notetype=notetypes.pitch,
                           streammode=streammodes.sequence))
            .with_pan(Itemstream(['80'], notetype=notetypes.number, streammode=streammodes.heap))
            .with_dist(5)
            .with_percent(.04)
            .with_instr(2)
        )

        melody_left.add_generator(melody_right)

        pass

    # ------------------------------------------------------------------ #
    # time_limit
    # ------------------------------------------------------------------ #

    def test_time_limit_stops_generation(self):
        # At 120bpm, q = 0.5s. time_limit=2.0 should yield exactly 4 notes
        # (start times 0.0, 0.5, 1.0, 1.5 — 5th would start at 2.0, cur_time
        # becomes 2.5 which exceeds limit, so it is excluded).
        g = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]))
        g.time_limit = 2.0
        g.generate_notes()
        self.assertEqual(len(g.notes), 4)

    def test_time_limit_zero_means_no_limit(self):
        # time_limit=0 is "unset" — generation is controlled by note_limit only
        g = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]), note_limit=6)
        g.time_limit = 0
        g.generate_notes()
        self.assertEqual(len(g.notes), 6)

    def test_time_limit_all_notes_within_boundary(self):
        # Every generated note's start_time should be less than time_limit
        g = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]))
        g.time_limit = 3.0
        g.generate_notes()
        for note in g.notes:
            start = float(note.split()[1])
            self.assertLess(start, g.time_limit)

    # ------------------------------------------------------------------ #
    # deepcopy / deepcopy_tree
    # ------------------------------------------------------------------ #

    def test_deepcopy_streams_are_independent(self):
        # Modifying a stream on the copy should not affect the original
        original = Line().with_rhythm('q').with_pitches('c4 d4 e4')
        copied = original.deepcopy()
        copied.streams[keys.frequency] = Itemstream(['g4'])
        self.assertNotEqual(
            original.streams[keys.frequency].values,
            copied.streams[keys.frequency].values
        )

    def test_deepcopy_clears_children(self):
        parent = Line().with_rhythm('q').with_pitches('c4')
        child = Line().with_rhythm('e').with_pitches('g4')
        parent.add_generator(child)
        self.assertEqual(len(parent.generators), 1)
        copied = parent.deepcopy()
        self.assertEqual(len(copied.generators), 0)

    def test_deepcopy_original_keeps_children(self):
        parent = Line().with_rhythm('q').with_pitches('c4')
        child = Line().with_rhythm('e').with_pitches('g4')
        parent.add_generator(child)
        parent.deepcopy()
        self.assertEqual(len(parent.generators), 1)

    def test_deepcopy_context_is_independent(self):
        original = Line().with_rhythm('q').with_pitches('c4')
        original.context['counter'] = 0
        copied = original.deepcopy()
        copied.context['counter'] = 99
        self.assertEqual(original.context['counter'], 0)

    def test_deepcopy_tree_includes_children(self):
        parent = Line().with_rhythm('q').with_pitches('c4')
        child = Line().with_rhythm('e').with_pitches('g4')
        parent.add_generator(child)
        copied = parent.deepcopy_tree()
        self.assertEqual(len(copied.generators), 1)

    # ------------------------------------------------------------------ #
    # chording
    # ------------------------------------------------------------------ #

    def test_chording_produces_simultaneous_notes(self):
        # A nested list in the pitch stream should produce multiple notes
        # at the same start_time (a chord)
        g = Line()
        g.set_stream(keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm))
        g.set_stream(keys.duration, Itemstream([.5]))
        g.set_stream(keys.frequency, Itemstream(
            [['c4', 'e4', 'g4'], 'd4'],
            notetype=notetypes.pitch,
            streammode=streammodes.sequence
        ))
        g.time_limit = 2.0
        g.generate_notes()
        # First beat should produce 3 notes at t=0.0 (the chord)
        start_times = [float(n.split()[1]) for n in g.notes]
        first_beat_notes = [t for t in start_times if t == 0.0]
        self.assertEqual(len(first_beat_notes), 3)

    def test_chording_advances_time_once(self):
        # Time should advance only once for a chord, not once per chord note
        g = Line()
        g.set_stream(keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm))
        g.set_stream(keys.duration, Itemstream([.5]))
        g.set_stream(keys.frequency, Itemstream(
            [['c4', 'e4'], 'd4'],
            notetype=notetypes.pitch,
            streammode=streammodes.sequence
        ))
        g.note_limit = 3  # chord (2 notes) + 1 single note
        g.generate_notes()
        start_times = sorted(set(float(n.split()[1]) for n in g.notes))
        # Should have exactly 2 distinct start times: 0.0 (chord) and 0.5 (next note)
        self.assertEqual(len(start_times), 2)

    # ------------------------------------------------------------------ #
    # child generator inheritance
    # ------------------------------------------------------------------ #

    def test_child_inherits_parent_time_limit(self):
        # Child with no time_limit set should inherit parent's time_limit
        parent = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]), note_limit=1)
        parent.time_limit = 2.0

        child = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]))
        # child has no time_limit set

        parent.add_generator(child)
        parent.generate_notes()

        # All child notes should fall within parent's time_limit
        child_notes = g.notes if False else [
            n for n in parent.notes
            if float(n.split()[1]) > 0  # parent note is at t=0
        ]
        for note in child_notes:
            self.assertLess(float(note.split()[1]), parent.time_limit)

    def test_child_start_time_offset_by_parent(self):
        # Child's start_time should be offset by parent's start_time
        parent = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]), note_limit=1, start_time=2.0)

        child = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]), note_limit=1)
        child.start_time = 1.0  # relative to parent

        parent.add_generator(child)
        parent.generate_notes()

        start_times = sorted([float(n.split()[1]) for n in parent.notes])
        # parent note at 2.0, child note at 2.0 + 1.0 = 3.0
        self.assertIn(2.0, start_times)
        self.assertIn(3.0, start_times)

    def test_child_notes_merged_and_sorted(self):
        # Notes from parent and child should be sorted by start_time
        parent = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['h'], notetype=notetypes.rhythm)),
        ]), note_limit=2)

        child = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]), note_limit=4)
        child.start_time = 0.0

        parent.add_generator(child)
        parent.generate_notes()

        start_times = [float(n.split()[1]) for n in parent.notes]
        self.assertEqual(start_times, sorted(start_times))

    def test_child_inherits_parent_note_limit(self):
        # Child with no note_limit should inherit parent's note_limit.
        # Parent generates 3 notes; child inherits note_limit=3 and also
        # generates 3, giving 6 total.
        parent = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]), note_limit=3)

        child = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([.5])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]))
        # child has no note_limit set (0)

        parent.add_generator(child)
        parent.generate_notes()

        self.assertEqual(len(parent.notes), 6)  # 3 parent + 3 inherited by child

    def test_setup_index_params(self):
        # Regression test for issue #18: setup_index_params_with_file() extracted
        # from Line to utils.setup_index_params(generator, filename).
        line = Line().with_rhythm('q').with_pitches('c4')
        utils.setup_index_params(line, '/path/to/file.wav')
        self.assertIn('orig_rhythm', line.streams)
        self.assertIn('inst_file', line.streams)
        self.assertIn('fade_in', line.streams)
        self.assertIn('fade_out', line.streams)
        self.assertIn(keys.index, line.pfields)
        self.assertIn('orig_rhythm', line.pfields)
        self.assertIn('inst_file', line.pfields)

    def test_set_stream_itemstream(self):
        # set_stream() should be available on NoteGenerator, not just Line
        g = NoteGenerator(streams=OrderedDict([(keys.instrument, Itemstream([1]))]))
        stream = Itemstream([2])
        g.set_stream(keys.instrument, stream)
        self.assertIs(g.streams[keys.instrument], stream)

    def test_set_stream_string(self):
        g = NoteGenerator(streams=OrderedDict([(keys.instrument, Itemstream([1]))]))
        g.set_stream(keys.instrument, '1 2 3')
        self.assertIsInstance(g.streams[keys.instrument], Itemstream)
        self.assertEqual(g.streams[keys.instrument].values, ['1', '2', '3'])

    def test_set_stream_list(self):
        g = NoteGenerator(streams=OrderedDict([(keys.instrument, Itemstream([1]))]))
        g.set_stream(keys.instrument, [1, 2, 3])
        self.assertIsInstance(g.streams[keys.instrument], Itemstream)

    def test_set_stream_callable(self):
        g = NoteGenerator(streams=OrderedDict([(keys.duration, Itemstream([1]))]))
        fn = lambda note: note.rhythm * 2
        g.set_stream(keys.duration, fn)
        self.assertTrue(callable(g.streams[keys.duration]))

    def test_g_on_note_generator(self):
        # g() should be available on NoteGenerator, not just Line
        g = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([1])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]), note_limit=4)
        result = g.g()
        self.assertIs(result, g)
        self.assertEqual(len(g.notes), 4)

    def test_randomize_on_note_generator(self):
        # randomize() should be available on NoteGenerator, not just Line
        g = NoteGenerator(streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([1])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
        ]), note_limit=4)
        result = g.randomize()
        self.assertIs(result, g)

    def test_get_tempo_on_note_generator(self):
        # Regression test for issue #14: NoteGenerator.tempo() renamed to get_tempo()
        # to avoid collision with Line.tempo(x) fluent setter.
        g = NoteGenerator(streams=OrderedDict([
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm))
        ]))
        g.streams[keys.rhythm].tempo = 90
        self.assertEqual(g.get_tempo(), 90)

    def test_line_tempo_setter_still_works(self):
        line = Line().with_rhythm('q').with_tempo(90)
        self.assertEqual(line.streams[keys.rhythm].tempo, 90)

    def test_with_streams_ordered_dict(self):
        # Regression test for issue #15: with_streams() with an OrderedDict was
        # being overwritten by the else branch, and didn't return self.
        od = OrderedDict([(keys.instrument, Itemstream([1]))])
        g = NoteGenerator().with_streams(od)
        self.assertIs(g.streams, od)

    def test_with_streams_plain_dict(self):
        d = [(keys.instrument, Itemstream([1]))]
        g = NoteGenerator().with_streams(d)
        self.assertIsInstance(g.streams, OrderedDict)
        self.assertIn(keys.instrument, g.streams)

    def test_with_streams_returns_self(self):
        g = NoteGenerator()
        result = g.with_streams(OrderedDict())
        self.assertIs(result, g)

    def test_mutable_default_args(self):
        # Regression test for issue #13: post_processes=[] and gen_lines=[] as default
        # args caused all instances to share the same list object.
        g1 = NoteGenerator()
        g2 = NoteGenerator()
        g1.post_processes.append(lambda note: note)
        g1.gen_lines.append('f 1 0 16384 10 1')
        self.assertEqual(len(g2.post_processes), 0)
        self.assertEqual(len(g2.gen_lines), 0)

    def test_line_pitches_with_string(self):
        # Regression test for issue #12: Line.pitches() with a string arg was raising
        # NameError because it referenced Notetypes() instead of notetypes.
        line = Line().with_pitches('c4 d4 e4')
        self.assertEqual(line.streams[keys.frequency].notetype, notetypes.pitch)

    def test_line_pitches_with_list(self):
        line = Line().with_pitches(['c4', 'd4', 'e4'])
        self.assertEqual(line.streams[keys.frequency].notetype, notetypes.pitch)

    def test_line_pitches_with_itemstream(self):
        stream = Itemstream(['c4', 'd4'], notetype=notetypes.pitch)
        line = Line().with_pitches(stream)
        self.assertEqual(line.streams[keys.frequency].notetype, notetypes.pitch)

    # ------------------------------------------------------------------ #
    # Line fluent API: with_instr, with_index, path notetype, pfields  (#34)
    # ------------------------------------------------------------------ #
    # Line default pfield order in the score string (split by whitespace):
    #   [0] = 'i' + instrument    instrument is embedded: 'i1', 'i4', etc.
    #   [1] = start_time
    #   [2] = duration
    #   [3] = amplitude
    #   [4] = frequency
    #   [5] = pan  ...

    def test_with_instr_sets_instrument_number_in_score(self):
        # with_instr(n) sets p1 — the Csound instrument number.
        # In the score string, instrument is embedded in split()[0] as 'i<n>'.
        gen = (Line()
               .with_rhythm(Itemstream(['q'], notetype=notetypes.rhythm))
               .with_pitches('c4')
               .with_instr(7))
        gen.note_limit = 1
        gen.generate_notes()

        instr = int(gen.notes[0].split()[0][1:])   # strip leading 'i'
        self.assertEqual(instr, 7)

    def test_with_index_value_appears_in_score(self):
        # with_index(n) adds an index stream, but index must also be in pfields
        # to appear in the score — this mirrors the real usage pattern where
        # setup_index_params or manual pfields.append() is required.
        gen = (Line()
               .with_rhythm(Itemstream(['q'], notetype=notetypes.rhythm))
               .with_pitches('c4')
               .with_index(3.5))
        gen.pfields.append(keys.index)
        gen.note_limit = 1
        gen.generate_notes()

        fields = gen.notes[0].split()
        index_val = float(fields[len(fields) - 1])   # last column
        self.assertAlmostEqual(index_val, 3.5)

    def test_path_notetype_returns_quoted_string_unchanged(self):
        # notetypes.path wraps the string in double-quotes and passes it through
        # without any pitch or rhythm conversion.
        stream = Itemstream(['/samples/kick.wav'], notetype=notetypes.path)
        val = stream.get_next_value()
        self.assertEqual(val, '"/samples/kick.wav"')

    def test_path_notetype_does_not_convert_to_frequency(self):
        # A path string would raise an error or produce garbage if treated as pitch.
        # Confirm notetypes.path leaves the value intact as a string.
        stream = Itemstream(['/samples/snare.wav'], notetype=notetypes.path)
        val = stream.get_next_value()
        self.assertIsInstance(val, str)
        self.assertIn('/samples/snare.wav', val)

    def test_custom_pfield_appended_to_pfields_appears_in_score(self):
        # A custom stream added via set_stream() only appears in the score
        # when its key is also appended to generator.pfields.
        gen = (Line()
               .with_rhythm(Itemstream(['q'], notetype=notetypes.rhythm))
               .with_pitches('c4'))
        gen.set_stream('my_param', 42.0)
        gen.pfields.append('my_param')
        gen.note_limit = 1
        gen.generate_notes()

        # my_param should be the last column in the score line
        fields = gen.notes[0].split()
        self.assertAlmostEqual(float(fields[-1]), 42.0)

    def test_custom_pfield_absent_from_score_if_not_in_pfields(self):
        # A stream key that exists in streams but NOT in pfields does not
        # produce an extra column in the score output.
        gen = (Line()
               .with_rhythm(Itemstream(['q'], notetype=notetypes.rhythm))
               .with_pitches('c4'))
        default_field_count = len(gen.pfields)
        gen.set_stream('hidden', 99.0)
        # deliberately NOT appending 'hidden' to pfields
        gen.note_limit = 1
        gen.generate_notes()

        fields = gen.notes[0].split()
        # +1 for the 'i' prefix on instrument field
        self.assertEqual(len(fields), default_field_count + 1)

    def test_pfields_append_pattern_used_in_csound_pieces(self):
        # Real-world pattern: container.pfields += [keys.index, 'orig_rhythm', 'inst_file']
        # Each appended key must also have a stream, otherwise it emits empty string.
        gen = (Line()
               .with_rhythm(Itemstream(['q'], notetype=notetypes.rhythm))
               .with_pitches('c4'))
        gen.set_stream(keys.index, 7.0)
        gen.set_stream('fade_in', 0.001)
        gen.pfields += [keys.index, 'fade_in']
        gen.note_limit = 1
        gen.generate_notes()

        fields = gen.notes[0].split()
        # Second-to-last: index, last: fade_in
        self.assertAlmostEqual(float(fields[-2]), 7.0)
        self.assertAlmostEqual(float(fields[-1]), 0.001)

    def test_generator_dur_limits_child_to_relative_duration(self):
        # generator_dur sets a relative duration for a child generator.
        # The child's effective time_limit becomes child.start_time + generator_dur.
        # At 120bpm, q = 0.5s.  Child starts at 2.0 with generator_dur=1.0,
        # so time_limit = 3.0.  Notes at 2.0 and 2.5 are within; 3.0 is not.
        parent = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([0.5])),
                (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
            ]),
            note_limit=1
        )
        child = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([0.5])),
                (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
            ]),
            start_time=2.0,
            note_limit=100   # high enough that only generator_dur stops it
        )
        child.generator_dur = 1.0

        parent.add_generator(child)
        parent.generate_notes()

        child_notes = [n for n in parent.notes if float(n.split()[1]) >= 2.0]
        child_start_times = sorted([float(n.split()[1]) for n in child_notes])

        # Only notes at 2.0 and 2.5 should appear; 3.0+ is beyond time_limit
        self.assertEqual(child_start_times, [2.0, 2.5])

    def test_generator_dur_start_time_is_absolute_not_offset_by_parent(self):
        # When generator_dur > 0, the child's start_time is treated as absolute
        # and is NOT offset by the parent's start_time.  This is different from
        # the normal child behavior where start_time is relative to the parent.
        parent = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([0.5])),
                (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
            ]),
            note_limit=1,
            start_time=5.0    # parent starts at t=5.0
        )
        child = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([0.5])),
                (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
            ]),
            start_time=2.0,   # absolute — NOT relative to parent's 5.0
            note_limit=1
        )
        child.generator_dur = 1.0

        parent.add_generator(child)
        parent.generate_notes()

        child_start_times = [float(n.split()[1]) for n in parent.notes
                             if float(n.split()[1]) != 5.0]
        # Child starts at 2.0 (absolute), NOT 5.0 + 2.0 = 7.0
        self.assertIn(2.0, child_start_times)
        self.assertNotIn(7.0, child_start_times)

    def test_generator_dur_vs_time_limit_distinction(self):
        # time_limit is an absolute clock position; generator_dur is relative
        # to the child's own start_time.
        #
        # A child at start_time=2.0 with generator_dur=1.0 stops at 3.0.
        # A child at start_time=0.0 with time_limit=3.0 also stops at 3.0.
        # Both should produce notes at 0.0, 0.5, 1.0, 1.5, 2.0, 2.5 — 6 notes.
        # (Note at 3.0 is excluded because cur_time becomes 3.5 > time_limit.)
        def make_parent_with_child(child):
            parent = NoteGenerator(
                streams=OrderedDict([
                    (keys.instrument, Itemstream([1])),
                    (keys.duration, Itemstream([0.5])),
                    (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
                ]),
                note_limit=1
            )
            parent.add_generator(child)
            parent.generate_notes()
            return parent

        child_time_limit = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([0.5])),
                (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
            ]),
            note_limit=100
        )
        child_time_limit.time_limit = 3.0   # absolute: stop when clock >= 3.0

        child_generator_dur = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([1])),
                (keys.duration, Itemstream([0.5])),
                (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
            ]),
            start_time=2.0,
            note_limit=100
        )
        child_generator_dur.generator_dur = 1.0  # relative: span 1.0s from start_time

        parent_a = make_parent_with_child(child_time_limit)
        parent_b = make_parent_with_child(child_generator_dur)

        a_child_times = sorted([float(n.split()[1]) for n in parent_a.notes
                                 if float(n.split()[1]) > 0])
        b_child_times = sorted([float(n.split()[1]) for n in parent_b.notes
                                 if float(n.split()[1]) >= 2.0])

        # time_limit child: notes at 0.5, 1.0, 1.5, 2.0, 2.5 (start_time offset by parent's 0)
        self.assertEqual(a_child_times, [0.5, 1.0, 1.5, 2.0, 2.5])
        # generator_dur child: notes at 2.0, 2.5
        self.assertEqual(b_child_times, [2.0, 2.5])

if __name__ == '__main__':
    unittest.main()
