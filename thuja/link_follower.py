import math
import re
import socket
from collections import namedtuple

_SyncPoint = namedtuple('SyncPoint', ['csound_time', 'link_beat', 'bpm'])
_PendingSwap = namedtuple('PendingSwap', ['notes', 'target_beat'])

_STATUS_RE = re.compile(r'\(status bpm ([\d.]+) beat ([\d.]+)')


class LinkFollower:
    """Follows an Ableton Link session via the carabiner bridge (TCP, port 17000).

    Maintains a sync point — the mapping between Csound score time and Link beat
    time recorded at a specific moment — from which all beat/time conversions
    are derived. Call establish_sync() after connect() and after every tempo change.

    This class has no thuja dependency and can be used standalone.
    """

    def __init__(self, host='localhost', port=17000, quantum=4, _socket_factory=None):
        self._host = host
        self._port = port
        self.quantum = quantum
        self._sock = None
        self._bpm = None
        self._last_beat = None
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
        line = self._recv_line_blocking()
        if not line:
            raise ValueError("carabiner connected but sent no data within " + str(timeout) + "s")
        print("[LinkFollower] raw status: " + repr(line), flush=True)
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
        """
        self._sync_point = _SyncPoint(
            csound_time=csound_time,
            link_beat=self._last_beat,
            bpm=self._bpm,
        )

    # ------------------------------------------------------------------
    # Beat / time conversions
    # ------------------------------------------------------------------

    def current_beat(self, csound_time):
        """Return Link beat number corresponding to the given Csound score time."""
        sp = self._sync_point
        return sp.link_beat + (csound_time - sp.csound_time) * (sp.bpm / 60.0)

    def csound_time_for_beat(self, beat):
        """Return Csound score time corresponding to the given Link beat number."""
        sp = self._sync_point
        return sp.csound_time + (beat - sp.link_beat) * (60.0 / sp.bpm)

    def next_boundary(self, csound_time, quantum=None):
        """Return the Link beat number of the next quantum boundary after csound_time.

        quantum=1 → next beat; quantum=4 → next bar; quantum=8 → next 2-bar phrase.
        Defaults to self.quantum (set at construction, default 4).
        """
        q = quantum if quantum is not None else self.quantum
        cb = self.current_beat(csound_time)
        # Always the strictly next boundary: floor(cb/q) + 1
        # so calling gen() exactly on a boundary waits for the following one.
        return (math.floor(cb / q) + 1) * q

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
        """Parse a carabiner status s-expression and update internal state.

        Format: (status bpm 120.000 beat 0.000 phase 0.000 metro (0.000 0.000))
        """
        m = _STATUS_RE.search(line)
        if m:
            self._bpm = float(m.group(1))
            self._last_beat = float(m.group(2))
