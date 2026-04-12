import math
import re
import socket
import time
from collections import namedtuple

_SyncPoint = namedtuple('SyncPoint', ['csound_time', 'link_beat', 'bpm'])
_PendingSwap = namedtuple('PendingSwap', ['notes', 'target_beat'])

# Carabiner 1.2+ format: status { :peers N :bpm 120.0 :start N :beat N }
# Carabiner legacy format: (status bpm 120.0 beat 0.0 ...)
# Both are matched by making the leading colon optional.
_BPM_RE   = re.compile(r':?bpm\s+([\d.]+)')
_BEAT_RE  = re.compile(r':?beat\s+([\d.]+)')
_PHASE_RE = re.compile(r':?phase\s+([\d.]+)')


class LinkFollower:
    """Follows an Ableton Link session via the carabiner bridge (TCP, port 17000).

    Maintains a sync point — the mapping between Csound score time and Link beat
    time recorded at a specific moment — from which all beat/time conversions
    are derived. Call establish_sync() after connect() and after every tempo change.

    This class has no thuja dependency and can be used standalone.
    """

    def __init__(self, host='localhost', port=17000, quantum=4,
                 latency_offset_secs=0.0, _socket_factory=None):
        self._host = host
        self._port = port
        self.quantum = quantum
        # Tunable fixed offset applied to all beat/time conversions. Positive
        # values shift notes earlier in wall time (compensating for audio
        # output latency or a consistently-late feel). Live-adjustable.
        self.latency_offset_secs = latency_offset_secs
        self._sock = None
        self._bpm = None
        self._last_beat = None
        self._last_phase = None            # bar phase from carabiner (beat % quantum from Ableton's perspective)
        self._last_beat_wall_time = None   # monotonic time when _last_beat was recorded
        self._sync_point = None
        self._buf = ''
        self._socket_factory = _socket_factory or (
            lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        )

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, timeout=5.0):
        """Open TCP socket to carabiner, receive initial status.

        Raises socket.timeout if carabiner does not respond within `timeout` seconds.
        Raises ValueError if the status line cannot be parsed (wrong protocol/version).
        """
        self._sock = self._socket_factory()
        self._sock.settimeout(timeout)
        self._sock.connect((self._host, self._port))
        # Carabiner 1.2+ does not push status on connect; request it explicitly.
        self._sock.sendall(b'status\n')
        line = self._recv_line_blocking()
        if not line:
            raise ValueError("carabiner connected but sent no data within " + str(timeout) + "s")
        self._apply_status(line)
        if self._bpm is None:
            raise ValueError(
                "carabiner status line did not match expected format.\n"
                "  received: " + repr(line) + "\n"
                "  expected: (status bpm <N> beat <N> ...)"
            )

    def disconnect(self):
        """Close socket cleanly."""
        if self._sock:
            self._sock.close()
            self._sock = None

    # ------------------------------------------------------------------
    # Sync point
    # ------------------------------------------------------------------

    def establish_sync(self, csound_time):
        """Record (csound_time, current_link_beat, current_bpm) as sync point.

        Must be called immediately after connect() and immediately after every
        tempo change so that beat/time conversions stay accurate.

        Corrects _last_beat for the wall-clock time elapsed since it was received,
        so the stored link_beat accurately reflects the beat at csound_time even
        when there is a delay between connect() and the first establish_sync() call.

        NOTE: less accurate than establish_sync_via_probe() — the latter sends a
        fresh status request with RTT midpoint correction, which avoids the
        stale-line error introduced by pushed status updates.
        """
        beat = self._last_beat
        if self._last_beat_wall_time is not None:
            elapsed = time.monotonic() - self._last_beat_wall_time
            beat = self._last_beat + elapsed * self._bpm / 60.0
        self._sync_point = _SyncPoint(
            csound_time=csound_time,
            link_beat=beat,
            bpm=self._bpm,
        )

    def establish_sync_via_probe(self, csound_time_fn):
        """Re-anchor the sync point using a fresh active status probe.

        Sends `status\\n` and anchors (csound_time_at_recv, _last_beat) with
        no projection correction. The anchor is effectively "whatever the
        fresh probe just told us, treated as 'now'".

        This avoids the passive-poll error where `_last_beat` comes from a
        line that was in-flight for an unknown time. A fixed sampling bias
        in carabiner is acceptable because probe measurements have the same
        bias and cancel out.

        `csound_time_fn` is a zero-arg callable returning current scoreTime.
        Returns the measured RTT in seconds.
        """
        self._drain_nonblocking()
        send_mono = time.monotonic()
        self._sock.sendall(b'status\n')
        line = self._recv_line_blocking()
        recv_mono = time.monotonic()
        csound_time = csound_time_fn()
        # If a push raced our reply, prefer the latest line
        self._sock.setblocking(False)
        try:
            chunk = self._sock.recv(4096)
            if chunk:
                self._buf += chunk.decode('utf-8')
        except (BlockingIOError, OSError):
            pass
        finally:
            self._sock.setblocking(True)
        while '\n' in self._buf:
            next_line, self._buf = self._buf.split('\n', 1)
            line = next_line
        self._buf = ''

        self._apply_status(line)
        rtt = recv_mono - send_mono
        self._sync_point = _SyncPoint(
            csound_time=csound_time,
            link_beat=self._last_beat,
            bpm=self._bpm,
        )
        return rtt

    # ------------------------------------------------------------------
    # Beat / time conversions
    # ------------------------------------------------------------------

    def current_beat(self, csound_time):
        """Return Link beat number corresponding to the given Csound score time.

        Applies `latency_offset_secs` so a positive offset makes the model
        report a later beat (dispatch fires sooner).
        """
        sp = self._sync_point
        effective = csound_time + self.latency_offset_secs
        return sp.link_beat + (effective - sp.csound_time) * (sp.bpm / 60.0)

    def csound_time_for_beat(self, beat):
        """Return Csound score time corresponding to the given Link beat number.

        Applies `latency_offset_secs` so a positive offset returns an earlier
        csound time for the same beat (note scheduled sooner).
        """
        sp = self._sync_point
        return sp.csound_time + (beat - sp.link_beat) * (60.0 / sp.bpm) - self.latency_offset_secs

    def next_boundary(self, csound_time, quantum=None):
        """Return the Link beat number of the next quantum boundary after csound_time.

        quantum=1 → next beat; quantum=4 → next bar; quantum=8 → next 2-bar phrase.
        Defaults to self.quantum (set at construction, default 4).

        Uses phase from carabiner to align with Ableton's actual bar structure.
        bar_origin = _last_beat - _last_phase gives a Link beat number that
        corresponds to an Ableton downbeat. All boundaries are multiples of
        quantum from that origin, so they land on Ableton's grid regardless
        of when the Link session started.

        Without phase data, falls back to multiples of quantum from beat 0.
        """
        q = quantum if quantum is not None else self.quantum
        cb = self.current_beat(csound_time)

        if self._last_phase is not None and self._last_beat is not None:
            # bar_origin is a Link beat number on Ableton's downbeat grid.
            # Since phase = beat % session_quantum, bar_origin is always an
            # integer multiple of the session quantum — works for any q.
            bar_origin = self._last_beat - self._last_phase
            dist = cb - bar_origin
            periods = math.floor(dist / q)
            return bar_origin + (periods + 1) * q
        else:
            return (math.floor(cb / q) + 1) * q

    def probe_sync(self, csound_time):
        """Request fresh status from carabiner and compare with sync model.

        Returns (model_beat, probe_beat, delta_beats, drained_before,
        drained_after, rtt_seconds).

        Race-hardened against pushed status updates:
          - Drains any queued pushes before sending the request.
          - After the blocking recv returns, drains any additional lines
            non-blocking and prefers the latest one (a push may have been
            queued ahead of our reply).
        """
        drained_before = self._drain_nonblocking()
        send_wall = time.monotonic()
        self._sock.sendall(b'status\n')
        line = self._recv_line_blocking()
        recv_wall = time.monotonic()
        # Any additional lines that arrived alongside our reply — prefer latest
        self._sock.setblocking(False)
        try:
            chunk = self._sock.recv(4096)
            if chunk:
                self._buf += chunk.decode('utf-8')
        except (BlockingIOError, OSError):
            pass
        finally:
            self._sock.setblocking(True)
        drained_after = 0
        while '\n' in self._buf:
            next_line, self._buf = self._buf.split('\n', 1)
            line = next_line
            drained_after += 1
        self._buf = ''

        self._apply_status(line)
        probe_beat = self._last_beat
        model_beat = self.current_beat(csound_time)
        return (model_beat, probe_beat, model_beat - probe_beat,
                drained_before, drained_after, recv_wall - send_wall)

    def _drain_nonblocking(self):
        """Read and discard any queued status lines. Returns count discarded."""
        self._sock.setblocking(False)
        try:
            chunk = self._sock.recv(4096)
            if chunk:
                self._buf += chunk.decode('utf-8')
        except (BlockingIOError, OSError):
            pass
        finally:
            self._sock.setblocking(True)
        count = 0
        while '\n' in self._buf:
            _line, self._buf = self._buf.split('\n', 1)
            count += 1
        self._buf = ''
        return count

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def poll(self):
        """Non-blocking check for a BPM change from carabiner.

        Returns the new BPM (float) if it changed since last poll, else None.
        Reads whatever data is available on the socket without blocking.
        """
        if self._sock is None:
            return None
        old_bpm = self._bpm
        self._sock.setblocking(False)
        try:
            chunk = self._sock.recv(4096)
            if chunk:
                self._buf += chunk.decode('utf-8')
        except (BlockingIOError, OSError):
            pass
        finally:
            self._sock.setblocking(True)

        new_bpm = None
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            self._apply_status(line)
        if self._bpm != old_bpm:
            new_bpm = self._bpm
        return new_bpm

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def bpm(self):
        return self._bpm

    @property
    def connected(self):
        return self._sock is not None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recv_line_blocking(self):
        """Read one newline-terminated line from the socket, blocking."""
        while '\n' not in self._buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                break
            self._buf += chunk.decode('utf-8')
        if '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            return line
        result = self._buf
        self._buf = ''
        return result

    def _apply_status(self, line):
        """Parse a carabiner status line and update internal state.

        Handles both protocol formats:
          1.2+:   status { :peers N :bpm 120.0 :start N :beat N }
          legacy: (status bpm 120.0 beat 0.0 phase 0.0 metro (...))
        """
        bpm_m   = _BPM_RE.search(line)
        beat_m  = _BEAT_RE.search(line)
        phase_m = _PHASE_RE.search(line)
        if bpm_m:
            self._bpm = float(bpm_m.group(1))
        if beat_m:
            self._last_beat = float(beat_m.group(1))
            self._last_beat_wall_time = time.monotonic()
        if phase_m:
            self._last_phase = float(phase_m.group(1))
