"""Tests for LinkFollower and its integration with NoteGeneratorThread.

Tests 1–9 cover LinkFollower in isolation using a mock socket — no live
carabiner process required.

Tests 10–12 cover NoteGeneratorThread integration (tempo following, quantized
swap). These also use mocks for both carabiner and Csound.
"""
from __future__ import print_function
import time
import unittest
from unittest.mock import MagicMock, patch, call

from thuja.link_follower import LinkFollower
from thuja.notegenerator import NoteGenerator, NoteGeneratorThread, Line
from thuja.itemstream import Itemstream, notetypes
from thuja.streamkeys import keys
from collections import OrderedDict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Carabiner legacy format (pre-1.2)
STATUS_120 = '(status bpm 120.000 beat 4.000 phase 0.000 metro (0.000 0.000))\n'
STATUS_140 = '(status bpm 140.000 beat 8.000 phase 0.000 metro (0.000 0.000))\n'
# Carabiner 1.2+ format
STATUS_120_NEW = 'status { :peers 1 :bpm 120.000000 :start 285332905719 :beat 4.000000 }\n'
STATUS_140_NEW = 'status { :peers 1 :bpm 140.000000 :start 285332905719 :beat 8.000000 }\n'


def _make_mock_socket(responses):
    """Return a mock socket whose recv() serves the given response strings in order.

    Each string in `responses` is returned as a complete chunk (including
    newline if present). When exhausted, raises BlockingIOError.
    """
    mock = MagicMock()
    mock._blocking = True
    mock._responses = list(responses)

    def setblocking(flag):
        mock._blocking = flag

    def recv(n):
        if not mock._responses:
            if not mock._blocking:
                raise BlockingIOError
            return b''
        data = mock._responses.pop(0)
        if isinstance(data, str):
            data = data.encode('utf-8')
        return data

    mock.setblocking.side_effect = setblocking
    mock.recv.side_effect = recv
    return mock


def _make_follower(initial_status=STATUS_120, extra_responses=None):
    """Return a connected LinkFollower backed by a mock socket."""
    responses = [initial_status] + (extra_responses or [])
    sock = _make_mock_socket(responses)
    lf = LinkFollower(_socket_factory=lambda: sock)
    lf.connect()
    return lf, sock


# ---------------------------------------------------------------------------
# 1. connect() parses BPM and beat from initial status
# ---------------------------------------------------------------------------

class TestConnect(unittest.TestCase):

    def test_connect_parses_status(self):
        lf, _ = _make_follower(STATUS_120)
        self.assertAlmostEqual(lf.bpm, 120.0)
        self.assertTrue(lf.connected)

    def test_connect_parses_beat(self):
        lf, _ = _make_follower(STATUS_120)
        # internal _last_beat should be 4.0 (from STATUS_120)
        self.assertAlmostEqual(lf._last_beat, 4.0)

    def test_connect_parses_new_format(self):
        # Carabiner 1.2+ format: status { :peers N :bpm X :start N :beat X }
        lf, _ = _make_follower(STATUS_120_NEW)
        self.assertAlmostEqual(lf.bpm, 120.0)
        self.assertAlmostEqual(lf._last_beat, 4.0)

    def test_poll_returns_bpm_on_change_new_format(self):
        lf, sock = _make_follower(STATUS_120_NEW)
        sock.recv.side_effect = [STATUS_140_NEW.encode('utf-8'), BlockingIOError]
        result = lf.poll()
        self.assertAlmostEqual(result, 140.0)
        self.assertAlmostEqual(lf.bpm, 140.0)


# ---------------------------------------------------------------------------
# 2. establish_sync stores sync point correctly
# ---------------------------------------------------------------------------

class TestEstablishSync(unittest.TestCase):

    def test_establish_sync(self):
        lf, _ = _make_follower(STATUS_120)
        lf._last_beat_wall_time = time.monotonic()  # reset so elapsed correction is ~0
        lf.establish_sync(10.0)
        sp = lf._sync_point
        self.assertAlmostEqual(sp.csound_time, 10.0)
        self.assertAlmostEqual(sp.link_beat, 4.0, places=5)
        self.assertAlmostEqual(sp.bpm, 120.0)


# ---------------------------------------------------------------------------
# 3. current_beat math
# ---------------------------------------------------------------------------

class TestCurrentBeat(unittest.TestCase):

    def _synced_follower(self, sync_csound=0.0, sync_beat=0.0, bpm=120.0):
        lf, _ = _make_follower(STATUS_120)
        lf._bpm = bpm
        lf._last_beat = sync_beat
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(sync_csound)
        return lf

    def test_current_beat_math(self):
        # sync at csound=0, beat=0, bpm=120 (2 beats/sec)
        lf = self._synced_follower(sync_csound=0.0, sync_beat=0.0, bpm=120.0)
        self.assertAlmostEqual(lf.current_beat(1.0), 2.0, places=5)
        self.assertAlmostEqual(lf.current_beat(2.0), 4.0, places=5)
        self.assertAlmostEqual(lf.current_beat(0.5), 1.0, places=5)

    def test_current_beat_with_offset(self):
        # sync at csound=5.0, beat=10.0, bpm=120
        lf = self._synced_follower(sync_csound=5.0, sync_beat=10.0, bpm=120.0)
        # at csound=6.0, 1 more sec = 2 more beats → beat 12
        self.assertAlmostEqual(lf.current_beat(6.0), 12.0, places=5)


# ---------------------------------------------------------------------------
# 4. csound_time_for_beat math (inverse of current_beat)
# ---------------------------------------------------------------------------

class TestCsoundTimeForBeat(unittest.TestCase):

    def test_csound_time_for_beat_math(self):
        lf, _ = _make_follower(STATUS_120)
        lf._bpm = 120.0
        lf._last_beat = 0.0
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(0.0)
        # beat 2 at 120bpm = 1 second
        self.assertAlmostEqual(lf.csound_time_for_beat(2.0), 1.0, places=5)
        self.assertAlmostEqual(lf.csound_time_for_beat(4.0), 2.0, places=5)

    def test_round_trip(self):
        lf, _ = _make_follower(STATUS_120)
        lf._bpm = 120.0
        lf._last_beat = 4.0
        lf.establish_sync(5.0)
        for beat in (4.0, 8.0, 12.5, 16.0):
            t = lf.csound_time_for_beat(beat)
            self.assertAlmostEqual(lf.current_beat(t), beat)


# ---------------------------------------------------------------------------
# 5. current_beat survives a tempo change
# ---------------------------------------------------------------------------

class TestCurrentBeatSurvivsTempoChange(unittest.TestCase):

    def test_current_beat_survives_tempo_change(self):
        lf, _ = _make_follower(STATUS_120)
        # Initial sync: csound=0, beat=0, bpm=120
        lf._bpm = 120.0
        lf._last_beat = 0.0
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(0.0)

        # At csound=2.0 we should be at beat 4 (2 sec * 2 beats/sec)
        self.assertAlmostEqual(lf.current_beat(2.0), 4.0, places=5)

        # Now at csound=2.0, tempo changes to 60bpm. Carabiner reports beat=4.
        lf._bpm = 60.0
        lf._last_beat = 4.0
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(2.0)

        # At csound=4.0, 2 more secs at 60bpm = 2 more beats → beat 6
        self.assertAlmostEqual(lf.current_beat(4.0), 6.0, places=5)


# ---------------------------------------------------------------------------
# 6. next_boundary with quantum=1 (next beat)
# ---------------------------------------------------------------------------

class TestNextBoundaryBeat(unittest.TestCase):

    def _follower_at_beat(self, current_beat_val, bpm=120.0):
        lf, _ = _make_follower(STATUS_120)
        lf._bpm = bpm
        lf._last_beat = current_beat_val
        lf._last_phase = current_beat_val % lf.quantum
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(0.0)
        return lf

    def test_next_boundary_beat(self):
        lf = self._follower_at_beat(2.3)
        self.assertAlmostEqual(lf.next_boundary(0.0, quantum=1), 3.0)

    def test_next_boundary_beat_exactly_on(self):
        lf = self._follower_at_beat(3.0)
        # exactly on a beat boundary → next one
        self.assertAlmostEqual(lf.next_boundary(0.0, quantum=1), 4.0)


# ---------------------------------------------------------------------------
# 7. next_boundary with quantum=4 (next bar)
# ---------------------------------------------------------------------------

class TestNextBoundaryBar(unittest.TestCase):

    def _follower_at_beat(self, current_beat_val):
        lf, _ = _make_follower(STATUS_120)
        lf._bpm = 120.0
        lf._last_beat = current_beat_val
        lf._last_phase = current_beat_val % lf.quantum
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(0.0)
        return lf

    def test_next_boundary_bar(self):
        # at beat 3.9, next 4-beat boundary is 4
        lf = self._follower_at_beat(3.9)
        self.assertAlmostEqual(lf.next_boundary(0.0, quantum=4), 4.0)

    def test_next_boundary_bar_past_first(self):
        # at beat 5.1, next 4-beat boundary is 8
        lf = self._follower_at_beat(5.1)
        self.assertAlmostEqual(lf.next_boundary(0.0, quantum=4), 8.0)

    def test_next_boundary_bar_exactly_on(self):
        # at beat 4.0 exactly, next boundary is 8
        lf = self._follower_at_beat(4.0)
        self.assertAlmostEqual(lf.next_boundary(0.0, quantum=4), 8.0)

    def test_next_boundary_uses_default_quantum(self):
        lf = self._follower_at_beat(3.9)
        lf.quantum = 4
        self.assertAlmostEqual(lf.next_boundary(0.0), 4.0)

    def test_next_boundary_bar_with_phase_offset(self):
        # Regression: if Link's beat origin is offset from Ableton's bar
        # structure by 2 beats, bar boundaries should still align with
        # Ableton's downbeats, not multiples of 4 from beat 0.
        # Scenario: Ableton downbeats at beats 2, 6, 10, 14...
        # current_beat = 3.5 → next downbeat should be 6.0, not 4.0.
        lf, _ = _make_follower(STATUS_120)
        lf._bpm = 120.0
        lf._last_beat = 3.5
        lf._last_phase = 1.5   # 1.5 beats into the bar → downbeat was at 2.0
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(0.0)
        self.assertAlmostEqual(lf.next_boundary(0.0, quantum=4), 6.0)

    def test_next_boundary_beat_unaffected_by_phase_offset(self):
        # quantum=1 should give next integer beat regardless of bar phase.
        lf, _ = _make_follower(STATUS_120)
        lf._bpm = 120.0
        lf._last_beat = 3.5
        lf._last_phase = 1.5
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(0.0)
        self.assertAlmostEqual(lf.next_boundary(0.0, quantum=1), 4.0)


# ---------------------------------------------------------------------------
# 8. poll() returns None when no new data
# ---------------------------------------------------------------------------

class TestPollNoChange(unittest.TestCase):

    def test_poll_returns_none_when_no_data(self):
        lf, sock = _make_follower(STATUS_120)
        # socket has no more data — recv raises BlockingIOError
        sock.recv.side_effect = BlockingIOError
        result = lf.poll()
        self.assertIsNone(result)

    def test_poll_returns_none_when_bpm_unchanged(self):
        lf, sock = _make_follower(STATUS_120)
        # socket returns same BPM
        sock.recv.side_effect = [STATUS_120.encode('utf-8'), BlockingIOError]
        result = lf.poll()
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# 9. poll() returns new BPM when carabiner sends updated status
# ---------------------------------------------------------------------------

class TestPollBpmChange(unittest.TestCase):

    def test_poll_returns_bpm_on_change(self):
        lf, sock = _make_follower(STATUS_120)
        sock.recv.side_effect = [STATUS_140.encode('utf-8'), BlockingIOError]
        result = lf.poll()
        self.assertAlmostEqual(result, 140.0)
        self.assertAlmostEqual(lf.bpm, 140.0)

    def test_poll_updates_last_beat(self):
        lf, sock = _make_follower(STATUS_120)
        sock.recv.side_effect = [STATUS_140.encode('utf-8'), BlockingIOError]
        lf.poll()
        self.assertAlmostEqual(lf._last_beat, 8.0)


# ---------------------------------------------------------------------------
# 10. NoteGeneratorThread calls _update_tempos when poll returns new BPM
# ---------------------------------------------------------------------------

class TestThreadTempoFollowing(unittest.TestCase):

    def _make_thread(self, link_follower):
        g = Line().rhythms('q').pitches('c4').with_amps([1])
        g.note_limit = 4
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        t = NoteGeneratorThread(g, cs_mock, cpt_mock, link_follower=link_follower)
        return t

    def test_update_tempos_sets_rhythm_stream(self):
        lf = MagicMock(spec=LinkFollower)
        t = self._make_thread(lf)
        t._update_tempos(140.0)
        rhythm_stream = t.g.streams[keys.rhythm]
        self.assertAlmostEqual(rhythm_stream.tempo, 140.0)

    def test_poll_link_calls_update_tempos_on_change(self):
        lf = MagicMock(spec=LinkFollower)
        lf.connected = True
        lf.poll.return_value = 140.0
        t = self._make_thread(lf)
        t._poll_link()
        self.assertAlmostEqual(t.g.streams[keys.rhythm].tempo, 140.0)

    def test_poll_link_does_nothing_when_poll_returns_none(self):
        lf = MagicMock(spec=LinkFollower)
        lf.connected = True
        lf.poll.return_value = None
        t = self._make_thread(lf)
        original_tempo = t.g.streams[keys.rhythm].tempo
        t._poll_link()
        self.assertEqual(t.g.streams[keys.rhythm].tempo, original_tempo)


# ---------------------------------------------------------------------------
# 11. gen(quantize=...) sets _pending_swap with correct target_beat
# ---------------------------------------------------------------------------

class TestGenQuantize(unittest.TestCase):

    def _make_thread_with_follower(self, current_beat_val=3.9, bpm=120.0):
        g = Line().rhythms('q').pitches('c4').with_amps([1])
        g.note_limit = 4
        g.generate_notes()
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        lf = MagicMock(spec=LinkFollower)
        lf.connected = True
        lf.next_boundary.return_value = 4.0  # next 4-beat boundary
        lf.current_beat.return_value = current_beat_val
        t = NoteGeneratorThread(g, cs_mock, cpt_mock, link_follower=lf)
        return t, lf

    def test_gen_immediate_when_no_quantize(self):
        t, lf = self._make_thread_with_follower()
        t.g.generate_notes()
        t.gen()
        self.assertIsNone(t._pending_swap)

    def test_gen_quantize_sets_pending_swap(self):
        t, lf = self._make_thread_with_follower()
        t.gen(quantize=4)
        self.assertIsNotNone(t._pending_swap)
        self.assertAlmostEqual(t._pending_swap.target_beat, 4.0)

    def test_check_pending_swap_fires_when_beat_reached(self):
        t, lf = self._make_thread_with_follower()
        t.gen(quantize=4)
        # Simulate beat having reached the target
        lf.current_beat.return_value = 4.0
        t._check_pending_swap()
        self.assertIsNone(t._pending_swap)  # swap fired, cleared

    def test_check_pending_swap_does_not_fire_early(self):
        t, lf = self._make_thread_with_follower()
        t.gen(quantize=4)
        lf.current_beat.return_value = 3.99
        t._check_pending_swap()
        self.assertIsNotNone(t._pending_swap)  # not yet


# ---------------------------------------------------------------------------
# 12. target_beat survives a tempo change
# ---------------------------------------------------------------------------

class TestQuantizeTargetBeatSurvivesTempoChange(unittest.TestCase):

    def test_target_beat_unchanged_after_tempo_change(self):
        g = Line().rhythms('q').pitches('c4').with_amps([1])
        g.note_limit = 4
        g.generate_notes()
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        lf = MagicMock(spec=LinkFollower)
        lf.connected = True
        lf.next_boundary.return_value = 8.0

        t = NoteGeneratorThread(g, cs_mock, cpt_mock, link_follower=lf)
        t.gen(quantize=4)

        original_target = t._pending_swap.target_beat  # 8.0

        # Simulate tempo change: poll returns new BPM, establish_sync is called
        lf.poll.return_value = 140.0
        t._poll_link()

        # target_beat must be unchanged — it's a Link beat number, not a Csound time
        self.assertAlmostEqual(t._pending_swap.target_beat, original_target)

    def test_swap_fires_at_target_beat_after_tempo_change(self):
        g = Line().rhythms('q').pitches('c4').with_amps([1])
        g.note_limit = 4
        g.generate_notes()
        cs_mock = MagicMock()
        cs_mock.scoreTime.return_value = 0.0
        cpt_mock = MagicMock()
        lf = MagicMock(spec=LinkFollower)
        lf.connected = True
        lf.next_boundary.return_value = 8.0

        t = NoteGeneratorThread(g, cs_mock, cpt_mock, link_follower=lf)
        t.gen(quantize=4)

        # Tempo changes, but at csound_time=X current_beat is now 8
        lf.current_beat.return_value = 8.0
        t._check_pending_swap()
        self.assertIsNone(t._pending_swap)  # fired at target beat


# ---------------------------------------------------------------------------
# 13. latency_offset_secs
# ---------------------------------------------------------------------------

class TestLatencyOffset(unittest.TestCase):

    def _synced_follower(self, offset=0.0, sync_csound=0.0, sync_beat=0.0, bpm=120.0):
        lf, _ = _make_follower(STATUS_120)
        lf.latency_offset_secs = offset
        lf._bpm = bpm
        lf._last_beat = sync_beat
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(sync_csound)
        return lf

    def test_identity_at_zero_offset(self):
        lf = self._synced_follower(offset=0.0)
        self.assertAlmostEqual(lf.current_beat(1.0), 2.0, places=5)
        self.assertAlmostEqual(lf.csound_time_for_beat(2.0), 1.0, places=5)

    def test_current_beat_shifted_forward(self):
        lf = self._synced_follower(offset=0.0)
        beat_no_offset = lf.current_beat(1.0)
        lf.latency_offset_secs = 0.5
        beat_with_offset = lf.current_beat(1.0)
        # offset=0.5 at 120bpm → 1 extra beat
        self.assertAlmostEqual(beat_with_offset - beat_no_offset, 1.0, places=5)

    def test_csound_time_shifted_earlier(self):
        lf = self._synced_follower(offset=0.0)
        time_no_offset = lf.csound_time_for_beat(4.0)
        lf.latency_offset_secs = 0.5
        time_with_offset = lf.csound_time_for_beat(4.0)
        self.assertAlmostEqual(time_no_offset - time_with_offset, 0.5, places=5)

    def test_round_trip_with_offset(self):
        lf = self._synced_follower(offset=0.1, sync_beat=4.0, sync_csound=5.0)
        for t in (5.0, 6.0, 7.5, 10.0):
            beat = lf.current_beat(t)
            self.assertAlmostEqual(lf.csound_time_for_beat(beat), t, places=5)

    def test_live_mutable(self):
        lf = self._synced_follower(offset=0.0)
        beat_before = lf.current_beat(1.0)
        lf.latency_offset_secs = 1.0
        beat_after = lf.current_beat(1.0)
        # 1 second at 120bpm = 2 beats difference
        self.assertAlmostEqual(beat_after - beat_before, 2.0, places=5)

    def test_constructor_default_is_zero(self):
        lf, _ = _make_follower(STATUS_120)
        self.assertEqual(lf.latency_offset_secs, 0.0)

    def test_constructor_accepts_offset(self):
        responses = [STATUS_120]
        sock = _make_mock_socket(responses)
        lf = LinkFollower(latency_offset_secs=0.05, _socket_factory=lambda: sock)
        self.assertAlmostEqual(lf.latency_offset_secs, 0.05)


# ---------------------------------------------------------------------------
# 14. establish_sync_via_probe
# ---------------------------------------------------------------------------

class TestEstablishSyncViaProbe(unittest.TestCase):

    def _probe_responses(self, drain=None, reply=STATUS_120, post=None):
        """Build a recv side_effect list matching establish_sync_via_probe's call pattern.

        _drain_nonblocking: 1 recv call (non-blocking)
        _recv_line_blocking: 1 recv call (blocking)
        post-recv drain: 1 recv call (non-blocking)
        """
        effects = []
        # drain: one non-blocking recv
        effects.append(drain.encode('utf-8') if isinstance(drain, str) else (drain or BlockingIOError))
        # reply: one blocking recv
        effects.append(reply.encode('utf-8') if isinstance(reply, str) else reply)
        # post-recv drain: one non-blocking recv
        effects.append(post.encode('utf-8') if isinstance(post, str) else (post or BlockingIOError))
        return effects

    def test_anchors_from_fresh_status(self):
        lf, sock = _make_follower(STATUS_120)
        sock.recv.side_effect = self._probe_responses(reply=STATUS_140)
        rtt = lf.establish_sync_via_probe(lambda: 10.0)
        sp = lf._sync_point
        self.assertAlmostEqual(sp.csound_time, 10.0)
        self.assertAlmostEqual(sp.link_beat, 8.0)  # from STATUS_140
        self.assertAlmostEqual(sp.bpm, 140.0)

    def test_returns_rtt(self):
        lf, sock = _make_follower(STATUS_120)
        sock.recv.side_effect = self._probe_responses()
        rtt = lf.establish_sync_via_probe(lambda: 0.0)
        self.assertIsInstance(rtt, float)
        self.assertGreaterEqual(rtt, 0.0)

    def test_sends_status_request(self):
        lf, sock = _make_follower(STATUS_120)
        sock.recv.side_effect = self._probe_responses()
        lf.establish_sync_via_probe(lambda: 0.0)
        sock.sendall.assert_called_with(b'status\n')

    def test_drains_stale_lines_before_send(self):
        lf, sock = _make_follower(STATUS_120)
        # Stale STATUS_140 in buffer; fresh STATUS_120 is the reply
        sock.recv.side_effect = self._probe_responses(drain=STATUS_140, reply=STATUS_120)
        lf.establish_sync_via_probe(lambda: 5.0)
        sp = lf._sync_point
        # Anchored to fresh reply, not stale drain
        self.assertAlmostEqual(sp.link_beat, 4.0)
        self.assertAlmostEqual(sp.bpm, 120.0)

    def test_prefers_latest_post_recv_line(self):
        lf, sock = _make_follower(STATUS_120)
        # Reply is STATUS_120, but STATUS_140 arrives in post-drain
        sock.recv.side_effect = self._probe_responses(reply=STATUS_120, post=STATUS_140)
        lf.establish_sync_via_probe(lambda: 5.0)
        sp = lf._sync_point
        self.assertAlmostEqual(sp.link_beat, 8.0)
        self.assertAlmostEqual(sp.bpm, 140.0)

    def test_uses_csound_time_fn(self):
        lf, sock = _make_follower(STATUS_120)
        sock.recv.side_effect = self._probe_responses()
        call_count = [0]
        def time_fn():
            call_count[0] += 1
            return 42.0
        lf.establish_sync_via_probe(time_fn)
        self.assertEqual(call_count[0], 1)
        self.assertAlmostEqual(lf._sync_point.csound_time, 42.0)


# ---------------------------------------------------------------------------
# 15. probe_sync
# ---------------------------------------------------------------------------

class TestProbeSync(unittest.TestCase):

    def _probe_responses(self, drain=None, reply=STATUS_120, post=None):
        """Build recv side_effect list matching probe_sync's call pattern.

        Same as establish_sync_via_probe: 3 recv calls total.
        """
        effects = []
        effects.append(drain.encode('utf-8') if isinstance(drain, str) else (drain or BlockingIOError))
        effects.append(reply.encode('utf-8') if isinstance(reply, str) else reply)
        effects.append(post.encode('utf-8') if isinstance(post, str) else (post or BlockingIOError))
        return effects

    def _synced_follower(self, probe_responses, sync_beat=0.0, bpm=120.0):
        lf, sock = _make_follower(STATUS_120)
        lf._bpm = bpm
        lf._last_beat = sync_beat
        lf._last_beat_wall_time = time.monotonic()
        lf.establish_sync(0.0)
        sock.recv.side_effect = probe_responses
        return lf, sock

    def test_returns_six_tuple(self):
        lf, sock = self._synced_follower(self._probe_responses())
        result = lf.probe_sync(0.0)
        self.assertEqual(len(result), 6)

    def test_delta_is_model_minus_probe(self):
        lf, sock = self._synced_follower(self._probe_responses())
        model_b, probe_b, delta, _, _, _ = lf.probe_sync(0.0)
        self.assertAlmostEqual(delta, model_b - probe_b, places=5)

    def test_sends_status_request(self):
        lf, sock = self._synced_follower(self._probe_responses())
        lf.probe_sync(0.0)
        sock.sendall.assert_called_with(b'status\n')

    def test_drained_before_counts_stale_lines(self):
        lf, sock = self._synced_follower(
            self._probe_responses(drain=STATUS_140, reply=STATUS_120))
        _, _, _, drained_before, _, _ = lf.probe_sync(0.0)
        self.assertEqual(drained_before, 1)

    def test_drained_after_counts_late_lines(self):
        lf, sock = self._synced_follower(
            self._probe_responses(reply=STATUS_120, post=STATUS_140))
        _, _, _, _, drained_after, _ = lf.probe_sync(0.0)
        self.assertEqual(drained_after, 1)

    def test_rtt_is_non_negative(self):
        lf, sock = self._synced_follower(self._probe_responses())
        _, _, _, _, _, rtt = lf.probe_sync(0.0)
        self.assertGreaterEqual(rtt, 0.0)


if __name__ == '__main__':
    unittest.main()
