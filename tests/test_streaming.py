"""Tests for streaming note generation.

Covers:
  - generate_next_note() produces the same notes as generate_notes()
  - reset_cursor() rewinds correctly (with and without stream reset)
  - NoteGeneratorThread buffer fill, flush, and fast-forward helpers
  - Tempo change flushes stale buffer and notes regenerate at new BPM
  - gen() in streaming mode resets cursor immediately or at target beat
"""
from __future__ import print_function
import unittest
from unittest.mock import MagicMock

from thuja.itemstream import Itemstream, notetypes, streammodes
from thuja.notegenerator import NoteGenerator, NoteGeneratorThread, Line
from thuja.streamkeys import keys
from collections import OrderedDict, deque


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_line(note_limit=8):
    g = Line().with_instr(1).with_rhythm('q').with_amps(1).with_pitches('c4 d e f')
    g.note_limit = note_limit
    return g


def _simple_generator(note_limit=8, tempo=120):
    rhythms = Itemstream(['q'], notetype=notetypes.rhythm, tempo=tempo)
    g = NoteGenerator(
        streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.rhythm, rhythms),
            (keys.duration, Itemstream([0.1])),
            (keys.amplitude, Itemstream([1])),
            (keys.frequency, Itemstream([440])),
        ]),
        note_limit=note_limit,
    )
    g.pfields = [keys.instrument, keys.start_time, keys.duration, keys.amplitude, keys.frequency]
    return g


def _make_streaming_thread(g, current_score_time=0.0):
    cs_mock = MagicMock()
    cs_mock.scoreTime.return_value = current_score_time
    cpt_mock = MagicMock()
    t = NoteGeneratorThread(g, cs_mock, cpt_mock, streaming=True)
    return t, cs_mock


# ---------------------------------------------------------------------------
# generate_next_note() equivalence with generate_notes()
# ---------------------------------------------------------------------------

class TestGenerateNextNote(unittest.TestCase):

    def test_next_note_matches_batch(self):
        """generate_next_note() one at a time == generate_notes() batch."""
        g_batch = _simple_generator(note_limit=8)
        g_stream = _simple_generator(note_limit=8)

        g_batch.generate_notes()
        batch_notes = list(g_batch.notes)

        stream_notes = []
        while True:
            n = g_stream.generate_next_note()
            if n is None:
                break
            stream_notes.append(n)

        self.assertEqual(batch_notes, stream_notes)

    def test_next_note_returns_none_when_exhausted(self):
        g = _simple_generator(note_limit=4)
        for _ in range(4):
            self.assertIsNotNone(g.generate_next_note())
        self.assertIsNone(g.generate_next_note())

    def test_next_note_advances_cur_time(self):
        g = _simple_generator(note_limit=4, tempo=120)
        g.generate_next_note()
        # quarter note at 120bpm = 0.5s
        self.assertAlmostEqual(g.cur_time, 0.5, places=5)

    def test_next_note_with_time_limit(self):
        g = _simple_generator(tempo=120)
        g.time_limit = 2.0   # 4 quarter notes at 120bpm
        g.note_limit = 0

        batch = _simple_generator(tempo=120)
        batch.time_limit = 2.0
        batch.note_limit = 0
        batch.generate_notes()

        stream_notes = []
        while True:
            n = g.generate_next_note()
            if n is None:
                break
            stream_notes.append(n)

        self.assertEqual(batch.notes, stream_notes)

    def test_score_dur_matches_batch(self):
        g_batch = _simple_generator(note_limit=8)
        g_stream = _simple_generator(note_limit=8)
        g_batch.generate_notes()
        while g_stream.generate_next_note() is not None:
            pass
        self.assertAlmostEqual(g_batch.score_dur, g_stream.score_dur, places=5)


# ---------------------------------------------------------------------------
# reset_cursor()
# ---------------------------------------------------------------------------

class TestResetCursor(unittest.TestCase):

    def test_reset_cursor_rewinds_time(self):
        g = _simple_generator(note_limit=4)
        for _ in range(4):
            g.generate_next_note()
        self.assertGreater(g.cur_time, 0)
        g.reset_cursor()
        self.assertEqual(g.cur_time, g.start_time)

    def test_reset_cursor_resets_note_count(self):
        g = _simple_generator(note_limit=4)
        for _ in range(4):
            g.generate_next_note()
        g.reset_cursor()
        self.assertEqual(g.note_count, 0)

    def test_reset_cursor_keeps_stream_state_by_default(self):
        """Without reset_streams, stream index is preserved."""
        g = _simple_generator(note_limit=4)
        g.generate_next_note()
        idx_before = g.streams[keys.frequency].index
        g.reset_cursor()
        self.assertEqual(g.streams[keys.frequency].index, idx_before)

    def test_reset_cursor_with_reset_streams(self):
        """reset_streams=True resets stream indices to beginning."""
        g = _simple_generator(note_limit=8)
        for _ in range(4):
            g.generate_next_note()
        g.reset_cursor(reset_streams=True)
        self.assertEqual(g.streams[keys.frequency].index, 0)
        self.assertEqual(g.note_count, 0)

    def test_generate_after_reset_produces_same_first_note(self):
        """After reset_cursor(reset_streams=True) the first note matches the original."""
        g = _simple_generator(note_limit=4)
        first = g.generate_next_note()
        for _ in range(3):
            g.generate_next_note()
        g.reset_cursor(reset_streams=True)
        self.assertEqual(g.generate_next_note(), first)


# ---------------------------------------------------------------------------
# Buffer fill and dispatch helpers
# ---------------------------------------------------------------------------

class TestBufferHelpers(unittest.TestCase):

    def test_fill_buffer_generates_notes(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 10.0
        t, cs = _make_streaming_thread(g)
        t._fill_buffer(2.0)
        self.assertGreater(len(t._buffer), 0)
        # All notes in buffer should have start_time < 2.0 + one rhythm duration
        for start, _ in t._buffer:
            self.assertLess(start, 2.5)

    def test_fill_buffer_stops_at_target(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 100.0
        t, cs = _make_streaming_thread(g)
        t._fill_buffer(2.0)
        # g.cur_time should be at or just past 2.0
        self.assertGreaterEqual(g.cur_time, 2.0)

    def test_flush_stale_buffer_removes_future_notes(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 10.0
        t, cs = _make_streaming_thread(g, current_score_time=1.0)
        t._fill_buffer(3.0)
        pre_count = len(t._buffer)
        cs.scoreTime.return_value = 1.0
        t._flush_stale_buffer()
        # Only notes at or before score_time=1.0 remain
        for start, _ in t._buffer:
            self.assertLessEqual(start, 1.0)

    def test_fast_forward_advances_cur_time(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 10.0
        t, cs = _make_streaming_thread(g)
        t._fast_forward_to(2.0)
        self.assertGreaterEqual(g.cur_time, 2.0)

    def test_fast_forward_does_not_add_to_buffer(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 10.0
        t, cs = _make_streaming_thread(g)
        t._fast_forward_to(2.0)
        self.assertEqual(len(t._buffer), 0)


# ---------------------------------------------------------------------------
# Tempo change: buffer flushed and notes regenerate at new BPM
# ---------------------------------------------------------------------------

class TestStreamingTempoChange(unittest.TestCase):

    def test_tempo_change_flushes_buffer(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 10.0
        lf = MagicMock()
        lf.connected = True
        lf.poll.return_value = 80.0
        lf.current_beat.return_value = 0.0
        lf.csound_time_for_beat.return_value = 1.5
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 1.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g, cs_mock, cpt_mock, link_follower=lf, streaming=True)
        t._fill_buffer(3.0)
        self.assertGreater(len(t._buffer), 0)
        t._poll_link()
        # Notes past score_time=1.0 should be gone
        for start, _ in t._buffer:
            self.assertLessEqual(start, 1.0)

    def test_tempo_change_updates_rhythm_stream(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 10.0
        lf = MagicMock()
        lf.connected = True
        lf.poll.return_value = 80.0
        lf.current_beat.return_value = 0.0
        lf.csound_time_for_beat.return_value = 0.75
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g, cs_mock, cpt_mock, link_follower=lf, streaming=True)
        t._poll_link()
        self.assertAlmostEqual(g.streams[keys.rhythm].tempo, 80.0)

    def test_new_notes_after_tempo_change_use_new_bpm(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 10.0
        lf = MagicMock()
        lf.connected = True
        lf.poll.return_value = 60.0   # 1 beat/sec
        lf.current_beat.return_value = 2.0   # exactly on beat 2
        lf.csound_time_for_beat.return_value = 3.0  # next beat (3) is at score_time 3.0
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 2.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g, cs_mock, cpt_mock, link_follower=lf, streaming=True)
        t._poll_link()   # updates tempo, snaps g.cur_time to next beat boundary (3.0)
        self.assertAlmostEqual(g.cur_time, 3.0, places=5)
        # Next note should start at the snapped beat boundary
        note_str = g.generate_next_note()
        self.assertIsNotNone(note_str)
        start = float(note_str.split()[1])
        self.assertAlmostEqual(start, 3.0, places=5)
        # cur_time should have advanced by 1.0 (quarter at 60bpm)
        self.assertAlmostEqual(g.cur_time, 4.0, places=5)


# ---------------------------------------------------------------------------
# gen() in streaming mode
# ---------------------------------------------------------------------------

class TestStreamingGen(unittest.TestCase):

    def _make_thread(self, score_time=5.0):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 100.0
        lf = MagicMock()
        lf.connected = True
        lf.next_boundary.return_value = 8.0
        lf.current_beat.return_value = 7.0    # floor(7.0)+1 = 8 → next beat
        lf.csound_time_for_beat.return_value = 5.5   # next beat is at score 5.5
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = score_time
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g, cs_mock, cpt_mock, link_follower=lf, streaming=True)
        return t, lf

    def test_gen_immediate_resets_cursor(self):
        t, lf = self._make_thread(score_time=5.0)
        # advance the cursor a bit
        t._fill_buffer(5.0)
        self.assertGreater(t.g.cur_time, 0)
        t.gen()   # no quantize — immediate
        # cursor should be snapped to the next beat boundary
        self.assertAlmostEqual(t.g.cur_time, 5.5, places=5)

    def test_gen_quantize_sets_pending_swap(self):
        t, lf = self._make_thread()
        t.gen(quantize=4)
        self.assertIsNotNone(t._pending_swap)
        self.assertAlmostEqual(t._pending_swap.target_beat, 8.0)
        self.assertIsNone(t._pending_swap.notes)   # streaming: no pre-baked notes

    def test_gen_quantize_fires_at_target_beat(self):
        t, lf = self._make_thread(score_time=5.0)
        t._fill_buffer(5.0)
        t.gen(quantize=4)
        lf.current_beat.return_value = 8.0   # target reached
        t._check_pending_swap()
        self.assertIsNone(t._pending_swap)   # fired and cleared


# ---------------------------------------------------------------------------
# Streaming with child generators
# ---------------------------------------------------------------------------

def _parent_with_child(parent_note_limit=0, child_note_limit=0,
                       parent_time_limit=10.0, child_time_limit=0,
                       child_start_time=0.0, child_generator_dur=0):
    """Create a parent generator with one child, both using quarter notes at 120bpm."""
    parent = _simple_generator(note_limit=parent_note_limit, tempo=120)
    parent.time_limit = parent_time_limit
    child = NoteGenerator(
        streams=OrderedDict([
            (keys.instrument, Itemstream([2])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm, tempo=120)),
            (keys.duration, Itemstream([0.2])),
            (keys.amplitude, Itemstream([0.5])),
            (keys.frequency, Itemstream([880])),
        ]),
        note_limit=child_note_limit,
    )
    child.pfields = [keys.instrument, keys.start_time, keys.duration, keys.amplitude, keys.frequency]
    child.time_limit = child_time_limit
    child.start_time = child_start_time
    child.generator_dur = child_generator_dur
    parent.add_generator(child)
    return parent, child


class TestStreamingChildBasic(unittest.TestCase):

    def test_parent_and_child_interleaved(self):
        parent, child = _parent_with_child(parent_time_limit=3.0)
        t, _ = _make_streaming_thread(parent)
        t._fill_buffer(3.0)
        notes = list(t._buffer)
        self.assertGreater(len(notes), 0)
        instruments = set()
        for _, note_str in notes:
            instruments.add(note_str.split()[0])
        self.assertIn('i1', instruments)
        self.assertIn('i2', instruments)

    def test_notes_in_start_time_order(self):
        parent, child = _parent_with_child(parent_time_limit=3.0)
        t, _ = _make_streaming_thread(parent)
        t._fill_buffer(3.0)
        times = [start for start, _ in t._buffer]
        self.assertEqual(times, sorted(times))

    def test_child_offset_start_time(self):
        parent, child = _parent_with_child(
            parent_time_limit=5.0, child_start_time=2.0)
        t, _ = _make_streaming_thread(parent)
        t._fill_buffer(5.0)
        child_starts = [start for start, n in t._buffer if n.startswith('i2')]
        parent_starts = [start for start, n in t._buffer if n.startswith('i1')]
        self.assertGreater(len(child_starts), 0)
        self.assertGreater(len(parent_starts), 0)
        self.assertGreaterEqual(child_starts[0], 2.0 - 1e-9)
        self.assertTrue(any(s < 2.0 for s in parent_starts))

    def test_child_inherits_parent_time_limit(self):
        parent, child = _parent_with_child(parent_time_limit=2.0)
        t, _ = _make_streaming_thread(parent)
        t._fill_buffer(5.0)
        child_starts = [start for start, n in t._buffer if n.startswith('i2')]
        if child_starts:
            self.assertLess(max(child_starts), 2.0 + 1e-9)

    def test_child_with_generator_dur(self):
        parent, child = _parent_with_child(
            parent_time_limit=10.0, child_start_time=1.0, child_generator_dur=2.0)
        t, _ = _make_streaming_thread(parent)
        t._fill_buffer(10.0)
        child_starts = [start for start, n in t._buffer if n.startswith('i2')]
        self.assertGreater(len(child_starts), 0)
        # generator_dur=2 means time_limit = start_time + 2 = 3.0
        self.assertLess(max(child_starts), 3.0 + 1e-9)

    def test_streaming_matches_batch(self):
        """Streaming output should match batch generate_notes() for the same tree."""
        parent_batch, child_batch = _parent_with_child(parent_time_limit=4.0)
        parent_batch.generate_notes()
        batch_notes = sorted(parent_batch.notes, key=lambda n: float(n.split()[1]))

        parent_stream, child_stream = _parent_with_child(parent_time_limit=4.0)
        t, _ = _make_streaming_thread(parent_stream)
        t._fill_buffer(4.0)
        stream_notes = [n for _, n in t._buffer]

        self.assertEqual(len(batch_notes), len(stream_notes))
        for b, s in zip(batch_notes, stream_notes):
            b_fields = b.strip().split()
            s_fields = s.strip().split()
            self.assertEqual(b_fields[0], s_fields[0])
            self.assertAlmostEqual(float(b_fields[1]), float(s_fields[1]), places=5)


class TestStreamingChildNested(unittest.TestCase):

    def _make_grandchild(self, start_time=0.0):
        gc = NoteGenerator(
            streams=OrderedDict([
                (keys.instrument, Itemstream([3])),
                (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm, tempo=120)),
                (keys.duration, Itemstream([0.3])),
                (keys.amplitude, Itemstream([0.25])),
                (keys.frequency, Itemstream([1760])),
            ]),
            note_limit=0,
        )
        gc.pfields = [keys.instrument, keys.start_time, keys.duration, keys.amplitude, keys.frequency]
        gc.time_limit = 0
        gc.start_time = start_time
        return gc

    def test_three_level_nesting(self):
        """parent -> child -> grandchild, each a different instrument."""
        parent, child = _parent_with_child(
            parent_time_limit=5.0, child_start_time=0.5)
        child.add_generator(self._make_grandchild(start_time=1.0))
        t, _ = _make_streaming_thread(parent)
        t._fill_buffer(5.0)
        instruments = set(n.split()[0] for _, n in t._buffer)
        self.assertIn('i1', instruments)
        self.assertIn('i2', instruments)
        self.assertIn('i3', instruments)

    def test_three_level_start_time_chaining(self):
        """Grandchild start_time accumulates: parent(0) + child(1) + grandchild(0.5) = 1.5."""
        parent, child = _parent_with_child(
            parent_time_limit=5.0, child_start_time=1.0)
        child.add_generator(self._make_grandchild(start_time=0.5))
        t, _ = _make_streaming_thread(parent)
        t._fill_buffer(5.0)
        gc_starts = [start for start, n in t._buffer if n.startswith('i3')]
        self.assertGreater(len(gc_starts), 0)
        self.assertAlmostEqual(gc_starts[0], 1.5, places=5)

    def test_three_level_limit_inheritance(self):
        """Grandchild with no time_limit inherits from child, which inherits from parent."""
        parent, child = _parent_with_child(parent_time_limit=3.0)
        child.add_generator(self._make_grandchild(start_time=0.0))
        t, _ = _make_streaming_thread(parent)
        t._fill_buffer(10.0)
        gc_starts = [start for start, n in t._buffer if n.startswith('i3')]
        if gc_starts:
            self.assertLess(max(gc_starts), 3.0 + 1e-9)


class TestStreamingChildReset(unittest.TestCase):

    def test_gen_resets_all_cursors(self):
        parent, child = _parent_with_child(parent_time_limit=10.0)
        t, _ = _make_streaming_thread(parent, current_score_time=0.0)
        t._fill_buffer(3.0)
        self.assertGreater(len(t._buffer), 0)
        old_parent_time = parent.cur_time
        old_child_time = child.cur_time
        t.gen()
        self.assertLess(parent.cur_time, old_parent_time)
        self.assertLess(child.cur_time, old_child_time)

    def test_gen_flushes_future_notes(self):
        parent, child = _parent_with_child(parent_time_limit=10.0)
        # score_time=1.0: notes before 1.0 are "past" (kept), notes after are stale (flushed)
        t, _ = _make_streaming_thread(parent, current_score_time=1.0)
        t._fill_buffer(5.0)
        total_before = len(t._buffer)
        future_before = sum(1 for start, _ in t._buffer if start > 1.0)
        self.assertGreater(future_before, 0)
        t.gen()
        future_after = sum(1 for start, _ in t._buffer if start > 1.0)
        self.assertEqual(future_after, 0)

    def test_fill_after_reset_produces_notes(self):
        parent, child = _parent_with_child(parent_time_limit=10.0)
        t, _ = _make_streaming_thread(parent, current_score_time=0.0)
        t._fill_buffer(2.0)
        t.gen()
        t._fill_buffer(2.0)
        self.assertGreater(len(t._buffer), 0)


# ---------------------------------------------------------------------------
# Tempo ratio (#46)
# ---------------------------------------------------------------------------

class TestTempoRatio(unittest.TestCase):

    def test_default_ratio_is_one(self):
        g = _simple_generator()
        self.assertEqual(g.tempo_ratio, 1.0)

    def test_ratio_applied_on_tempo_update(self):
        parent = _simple_generator(note_limit=0, tempo=120)
        parent.time_limit = 10.0
        child = _simple_generator(note_limit=0, tempo=120)
        child.time_limit = 10.0
        child.tempo_ratio = 0.5
        parent.add_generator(child)
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(parent, cs_mock, cpt_mock, streaming=True)
        t._update_tempos(100.0)
        self.assertAlmostEqual(parent.streams[keys.rhythm].tempo, 100.0)
        self.assertAlmostEqual(child.streams[keys.rhythm].tempo, 50.0)

    def test_ratio_composes_through_hierarchy(self):
        parent = _simple_generator(note_limit=0, tempo=120)
        parent.time_limit = 10.0
        child = _simple_generator(note_limit=0, tempo=120)
        child.time_limit = 0
        child.tempo_ratio = 0.5
        grandchild = _simple_generator(note_limit=0, tempo=120)
        grandchild.time_limit = 0
        grandchild.tempo_ratio = 2.0
        child.add_generator(grandchild)
        parent.add_generator(child)
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(parent, cs_mock, cpt_mock, streaming=True)
        t._update_tempos(120.0)
        # parent: 120 * 1.0 = 120
        # child: 120 * 0.5 = 60
        # grandchild: 120 * 0.5 * 2.0 = 120
        self.assertAlmostEqual(parent.streams[keys.rhythm].tempo, 120.0)
        self.assertAlmostEqual(child.streams[keys.rhythm].tempo, 60.0)
        self.assertAlmostEqual(grandchild.streams[keys.rhythm].tempo, 120.0)

    def test_ratio_one_is_identity(self):
        g = _simple_generator(note_limit=0, tempo=120)
        g.time_limit = 10.0
        g.tempo_ratio = 1.0
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g, cs_mock, cpt_mock, streaming=True)
        t._update_tempos(90.0)
        self.assertAlmostEqual(g.streams[keys.rhythm].tempo, 90.0)


# ---------------------------------------------------------------------------
# Multiple top-level generators (#47)
# ---------------------------------------------------------------------------

class TestMultiGenerator(unittest.TestCase):

    def test_accepts_single_generator(self):
        g = _simple_generator(note_limit=4)
        t, _ = _make_streaming_thread(g)
        self.assertEqual(len(t._generators), 1)
        self.assertIs(t._generators[0], g)

    def test_accepts_list_of_generators(self):
        g1 = _simple_generator(note_limit=4)
        g2 = _simple_generator(note_limit=4)
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread([g1, g2], cs_mock, cpt_mock, streaming=True)
        self.assertEqual(len(t._generators), 2)

    def test_multiple_generators_interleaved(self):
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 2.0
        g1.streams[keys.instrument] = Itemstream([1])
        g2 = _simple_generator(note_limit=0, tempo=120)
        g2.time_limit = 2.0
        g2.streams[keys.instrument] = Itemstream([2])
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread([g1, g2], cs_mock, cpt_mock, streaming=True)
        t._fill_buffer(2.0)
        instruments = set(n.split()[0] for _, n in t._buffer)
        self.assertIn('i1', instruments)
        self.assertIn('i2', instruments)

    def test_add_generator_mid_run(self):
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 10.0
        g1.streams[keys.instrument] = Itemstream([1])
        t, _ = _make_streaming_thread(g1)
        t._fill_buffer(2.0)
        instruments_before = set(n.split()[0] for _, n in t._buffer)
        self.assertIn('i1', instruments_before)
        self.assertNotIn('i2', instruments_before)

        g2 = _simple_generator(note_limit=0, tempo=120)
        g2.time_limit = 10.0
        g2.streams[keys.instrument] = Itemstream([2])
        t.add_generator(g2)
        t._buffer.clear()
        t._fill_buffer(2.0)
        instruments_after = set(n.split()[0] for _, n in t._buffer)
        self.assertIn('i1', instruments_after)
        self.assertIn('i2', instruments_after)

    def test_remove_generator(self):
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 10.0
        g1.streams[keys.instrument] = Itemstream([1])
        g2 = _simple_generator(note_limit=0, tempo=120)
        g2.time_limit = 10.0
        g2.streams[keys.instrument] = Itemstream([2])
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread([g1, g2], cs_mock, cpt_mock, streaming=True)
        t._fill_buffer(2.0)
        t._buffer.clear()
        t.remove_generator(g2)
        t._fill_buffer(2.0)
        instruments = set(n.split()[0] for _, n in t._buffer)
        self.assertIn('i1', instruments)
        self.assertNotIn('i2', instruments)

    def test_selective_gen_resets_only_target(self):
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 10.0
        g2 = _simple_generator(note_limit=0, tempo=120)
        g2.time_limit = 10.0
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread([g1, g2], cs_mock, cpt_mock, streaming=True)
        t._fill_buffer(3.0)
        g1_time_before = g1.cur_time
        g2_time_before = g2.cur_time
        t.gen(generator=g1)
        # g1 should be reset (cur_time back to start_time)
        self.assertLess(g1.cur_time, g1_time_before)
        # g2 should NOT be reset
        self.assertEqual(g2.cur_time, g2_time_before)

    def test_add_generator_syncs_tempo_to_link_bpm(self):
        # Regression: add_generator didn't sync the new generator's rhythm
        # streams to the current Link BPM. The generator kept its constructor
        # tempo until the next BPM change in the Link session — so initial
        # playback was at the wrong tempo.
        from thuja.link_follower import LinkFollower
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 10.0
        lf = MagicMock(spec=LinkFollower)
        lf.connected = True
        lf.bpm = 73.0
        lf.current_beat.return_value = 0.0
        lf.csound_time_for_beat.return_value = 0.5
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(cs=cs_mock, cpt=cpt_mock, link_follower=lf, streaming=True)
        # Constructor tempo is 120, Link is at 73
        t.add_generator(g1, quantize='beat')
        self.assertAlmostEqual(g1.streams[keys.rhythm].tempo, 73.0)

    def test_add_generator_starts_at_score_time(self):
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 10.0
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 3.5
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g1, cs_mock, cpt_mock, streaming=True)
        g2 = _simple_generator(note_limit=0, tempo=120)
        g2.time_limit = 10.0
        t.add_generator(g2)
        self.assertAlmostEqual(g2.start_time, 3.5)

    def test_add_generator_quantize_beat(self):
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 10.0
        lf = MagicMock()
        lf.connected = True
        lf.next_boundary.return_value = 8.0
        lf.csound_time_for_beat.return_value = 4.0
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 3.5
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g1, cs_mock, cpt_mock, link_follower=lf, streaming=True)
        g2 = _simple_generator(note_limit=0, tempo=120)
        g2.time_limit = 10.0
        t.add_generator(g2, quantize='beat')
        lf.next_boundary.assert_called_with(3.5, quantum=1)
        self.assertAlmostEqual(g2.start_time, 4.0)

    def test_add_generator_quantize_bar(self):
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 10.0
        lf = MagicMock()
        lf.connected = True
        lf.next_boundary.return_value = 12.0
        lf.csound_time_for_beat.return_value = 6.0
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 3.5
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g1, cs_mock, cpt_mock, link_follower=lf, streaming=True)
        g2 = _simple_generator(note_limit=0, tempo=120)
        g2.time_limit = 10.0
        t.add_generator(g2, quantize='bar')
        lf.next_boundary.assert_called_with(3.5, quantum=4)
        self.assertAlmostEqual(g2.start_time, 6.0)

    def test_tempo_update_applies_to_all_generators(self):
        g1 = _simple_generator(note_limit=0, tempo=120)
        g1.time_limit = 10.0
        g2 = _simple_generator(note_limit=0, tempo=120)
        g2.time_limit = 10.0
        g2.tempo_ratio = 0.5
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread([g1, g2], cs_mock, cpt_mock, streaming=True)
        t._update_tempos(100.0)
        self.assertAlmostEqual(g1.streams[keys.rhythm].tempo, 100.0)
        self.assertAlmostEqual(g2.streams[keys.rhythm].tempo, 50.0)


if __name__ == '__main__':
    unittest.main()
