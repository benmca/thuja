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


if __name__ == '__main__':
    unittest.main()
