import heapq
import math
import random
import sys
from operator import truediv

from thuja.streamkeys import StreamKey, keys
from thuja.itemstream import Itemstream, notetypes, streammodes
from thuja.event import Event
from collections import OrderedDict, namedtuple, deque
import copy
import funcsigs
import threading
import time

import thuja.utils as utils
import thuja.csound_utils as cs_utils

import ctcsound



class NoteGenerator:

    def __init__(self, note_limit=0,
                 start_time=0.0,
                 streams=None,
                 pfields=None,
                 post_processes=None,
                 init_context=None,
                 gen_lines=None):
        """
        Initializes a Generator object.ˆ

        Parameters:
            note_limit (int): The maximum number of notes to generate. Defaults to 16.
            start_time (float): The starting time of the generator. Defaults to 0.0.
            streams (OrderedDict): A dictionary of streams. Defaults to None.
            pfields (list): A list of parameter fields. Defaults to None.
            post_processes (list): A list of post-processing functions to be applied after
                generating notes. Defaults to an empty list.
            init_context (dict): An initial context for the generator, designed to be leveraged by post_processes but
                can be referenced wherever. Defaults to an empty dictionary.
            gen_lines (list): A list of strings (csound score events) to append to generated score string. Defaults to an empty list.
        """
        self.start_time = start_time
        self.streams = None
        if isinstance(streams, OrderedDict):
            self.streams = streams
        elif streams is not None:
            self.streams = OrderedDict(streams)
        self.note_limit = note_limit

        self.cur_time = 0.0
        # absolute time limit
        self.time_limit = 0
        # in cases where this is a child generator, and the start time is offset by the parent's start time,
        #   generator_dur can be used to set a relative time limit after that offset occurs in generate_notes
        self.generator_dur = 0

        self.gen_lines = gen_lines if gen_lines is not None else []
        self.note_count = 0
        self.notes = []
        self.end_lines = []
        self.score_dur = 0

        self.pfields = pfields
        if pfields is None:
            if self.streams is not None:
                self.pfields = list(self.streams.keys())
                self.pfields.insert(1, keys.start_time)

        # a place to put stuff to refer to in callables
        if init_context is not None:
            self.context = init_context
        else:
            self.context = {}

        # an array of callables, called in sequence after each note is initialized.
        self.post_processes = post_processes if post_processes is not None else []

        self.generators = []

    def with_streams(self, streams):
        if isinstance(streams, OrderedDict):
            self.streams = streams
        elif streams is not None:
            self.streams = OrderedDict(streams)
        return self

    def with_pfields(self, pfields):
        self.pfields = pfields
        return self

    # replicates Generator, not children
    def deepcopy(self):
        result = copy.deepcopy(self)
        result.generators = []
        result.streams = OrderedDict()
        for k, v in self.streams.items():
            # setattr(result, k, deepcopy(v, memo))
            result.streams.__setitem__(k, copy.deepcopy(v))
        if self.context is not None:
            for k, v in self.context.items():
                # setattr(result, k, deepcopy(v, memo))
                result.context.__setitem__(k, copy.deepcopy(v))
        return result

    # replicates Generator, includes children
    def deepcopy_tree(self):
        result = copy.deepcopy(self)
        result.streams = OrderedDict()
        for k, v in self.streams.items():
            # setattr(result, k, deepcopy(v, memo))
            result.streams.__setitem__(k, copy.deepcopy(v))
        if self.context is not None:
            for k, v in self.context.items():
                # setattr(result, k, deepcopy(v, memo))
                result.context.__setitem__(k, copy.deepcopy(v))
        return result

    def update_stream(self, key, stream):
        self.streams[key] = stream
        return self

    def set_stream(self, k, v):
        if isinstance(v, Itemstream):
            self.streams[k] = v
        elif isinstance(v, str):
            self.streams[k] = Itemstream(v.split())
        elif isinstance(v, list):
            self.streams[k] = Itemstream(v)
        elif callable(v):
            self.streams[k] = v
        else:
            # assume this is a single item and pass value through to ItemStream
            self.streams[k] = Itemstream(v)

    def generate_score(self, filename=None):
        self.note_count = 0
        self.notes = []
        self.cur_time = self.start_time

        f = None
        if filename is not None:
            f = open(filename, 'w')

        for gendx in range(len(self.gen_lines)):
            if f is None:
                print(self.gen_lines[gendx] + "\n")
            else:
                f.writelines(self.gen_lines[gendx] + "\n")

        for x in range(len(self.notes)):
            if f is None:
                print(self.notes[x])
            else:
                f.writelines(self.notes[x])

        for x in range(len(self.end_lines)):
            if f is None:
                print(self.end_lines[x] + "\n")
            else:
                f.writelines(self.end_lines[x] + "\n")

        if f is not None:
            f.close()
        return self

    def clear_notes(self):
        self.note_count = 0
        self.notes = []
        self.score_dur = 0

    def generate_next_note(self):
        """Generate one note, advancing all stream state.

        Returns a note string (e.g. 'i1\t0.0\t0.5\t...\n') or None when
        note_limit / time_limit is exhausted.

        This is the single-note equivalent of generate_notes(). It drives the
        same algorithm one iteration at a time so NoteGeneratorThread can fill
        a lookahead buffer on demand rather than pre-baking the full score.
        Call reset_cursor() to restart from the beginning.
        """
        # Mirror the while-loop guard from generate_notes().
        if not ((self.note_limit > 0 and self.note_count < self.note_limit) or (self.time_limit > 0)):
            return None

        note = Event(pfields=self.pfields, start_time=self.cur_time)
        note_is_chording = False
        rhythm = None

        for key in self.streams.keys():
            if key is keys.rhythm:
                continue
            if not isinstance(self.streams[key], Itemstream) and not callable(self.streams[key]):
                note.pfields[key] = self.streams[key]
            elif isinstance(self.streams[key], Itemstream):
                value = self.streams[key].get_next_value()
                if isinstance(value, dict):
                    for item in value.keys():
                        if item == keys.rhythm:
                            rhythm = utils.rhythm_to_duration(value[item], self.streams[key].tempo)
                        elif item == "freq":
                            result = utils.pc_to_freq(value[item], self.streams[key].current_octave)
                            self.streams[item].current_octave = result["octave"]
                            note.pfields[item] = result["value"]
                        else:
                            note.pfields[item] = value[item]
                else:
                    note.pfields[key] = value
                if self.streams[key].is_chording:
                    note_is_chording = True

        if not note_is_chording:
            if rhythm is not None:
                self.cur_time = self.cur_time + rhythm
                note.rhythm = rhythm
            elif note.rhythm is not None:
                self.cur_time = self.cur_time + note.rhythm
            elif keys.rhythm in self.streams and self.streams[keys.rhythm] is not None:
                rhythm = self.streams[keys.rhythm].get_next_value()
                self.cur_time = self.cur_time + rhythm
                note.rhythm = rhythm
            else:
                pass
        else:
            if isinstance(self.streams[keys.rhythm].values[self.streams[keys.rhythm].index], list):
                print("in chording case, rhythm stream must be a flat list - current value is a list (Nested list case)")
                assert False
            tempo = self.streams[keys.rhythm].tempo
            if isinstance(self.streams[keys.rhythm].tempo, list):
                tempo = self.streams[keys.rhythm].tempo[self.streams[keys.rhythm].note_count % len(self.streams[keys.rhythm].tempo)]
            note.rhythm = utils.rhythm_to_duration(self.streams[keys.rhythm].values[self.streams[keys.rhythm].index], tempo)

        for key in self.streams.keys():
            if key is not keys.rhythm and key in note.pfields:
                if callable(self.streams[key]):
                    value = self.streams[key](note)
                    note.pfields[key] = value

        for item in self.post_processes:
            rhythm_not_set = (note.rhythm == None)
            if callable(item):
                if len(funcsigs.signature(item).parameters) > 1:
                    item(note, self.context)
                else:
                    item(note)
            if rhythm_not_set:
                assert note.rhythm is not None
                self.cur_time = self.cur_time + note.rhythm

        for key in self.streams.keys():
            if key is not keys.rhythm and key in note.pfields:
                if (note.pfields[key] == None or note.pfields[key] == '') and callable(self.streams[key]):
                    value = self.streams[key](note)
                    note.pfields[key] = value

        # Enforce time limit — mirrors the break in the original generate_notes() loop.
        if self.cur_time > self.time_limit > 0:
            return None

        self.note_count += 1
        if (note.pfields[keys.start_time] + note.pfields[keys.duration]) > self.score_dur:
            self.score_dur = (note.pfields[keys.start_time] + note.pfields[keys.duration])

        return str(note) + "\n"

    def reset_cursor(self, reset_streams=False):
        """Rewind the generation cursor to start_time.

        reset_streams=False (default): keep Itemstream positions — the pattern
            continues from its current state with time reset to start_time.
        reset_streams=True: reset all stream indices, heap state, and octave
            tracking — full restart of the pattern from the beginning.
        """
        self.cur_time = self.start_time
        self.note_count = 0
        self.score_dur = 0
        if reset_streams:
            for s in self.streams.values():
                if isinstance(s, Itemstream):
                    s.index = 0
                    s.heapdict = set()
                    s.note_count = 0
                    s.current_octave = 0
                    s.is_chording = False
                    s.chording_index = 0
                    if s.streammode in (streammodes.heap, streammodes.random):
                        s.index = s.rand.randrange(0, len(s.values))
                        if s.streammode == streammodes.heap:
                            s.heapdict.add(s.index)

    def generate_notes(self):
        self.note_count = 0
        self.cur_time = self.start_time
        self.notes = []

        while True:
            note_str = self.generate_next_note()
            if note_str is None:
                break
            self.notes.append(note_str)

        for g in self.generators:
            # Parent limits are DEFAULTS, not hard constraints (#27). If a child
            # sets its own time_limit or note_limit, the child's value wins — even
            # if it exceeds the parent's. This matches all real usage in csound-pieces
            # and is replicated in _collect_cursors() for the streaming path.
            #
            # start_time is relative to the parent (accumulated at each level).
            # generator_dur is a relative duration: time_limit = start_time + dur.
            if g.generator_dur > 0:
                g.time_limit = g.start_time + g.generator_dur
                # assume here that g.start_time is absolute and should not be offset.
            else:
                g.start_time += self.start_time
            if self.time_limit > 0 and g.time_limit == 0:
                g.time_limit = self.time_limit
            if self.note_limit > 0 and g.note_limit == 0:
                g.note_limit = self.note_limit
            g.generate_notes()
            self.notes.extend(g.notes)
            if g.score_dur > self.score_dur:
                self.score_dur = g.score_dur


        # sort by start time - remember, these are string representations of the note.
        self.notes.sort(key=lambda note:float(note.split()[1]))

        return self

    def add_generator(self, other):
        if isinstance(other, NoteGenerator):
            self.generators.append(other)

    def add_bars_to_starttime(self, bars=1, beats=0, num=4, denom=4, tempo=120):
        beat_duration = 60.0 / tempo
        self.start_time += (beat_duration * num * bars) + (beat_duration * beats)

    def generate_score_string(self):
        retstring = ""
        for x in range(len(self.gen_lines)):
            retstring += self.gen_lines[x] + '\n'
        for y in range(len(self.notes)):
            retstring += self.notes[y]
        for x in range(len(self.end_lines)):
            retstring += self.end_lines[x] + '\n'
        return retstring

    def send_gens_to_udp(self, sock, UDP_IP="127.0.0.1", UDP_PORT=8088):
        for x in range(len(self.gen_lines)):
            sock.sendto(("&" + self.gen_lines[x]).encode(), (UDP_IP, UDP_PORT))

    def send_notes_to_udp(self, sock, UDP_IP="127.0.0.1", UDP_PORT=8088):
        for x in range(len(self.notes)):
            sock.sendto(("&" + self.notes[x]).encode(), (UDP_IP, UDP_PORT))

    def get_tempo(self):
        return self.streams[keys.rhythm].tempo

    def randomize(self):
        seed = random.Random().randint(0, sys.maxsize)
        self.set_streams_to_seed(seed)
        return self

    def g(self):
        self.generate_notes()
        return self

    def set_streams_to_seed(self, seed):
        for s in self.streams.values():
            if isinstance(s, Itemstream):
                s.set_seed(seed)
        if self.context is not None:
            for s in self.context.values():
                if isinstance(s, Itemstream):
                    s.set_seed(seed)


class Line(NoteGenerator):

    def __init__(self):
        super().__init__()
        self.streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([1])),
            # (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
            (keys.amplitude, Itemstream([1])),
            (keys.frequency, Itemstream([1])),
            (keys.pan, Itemstream([45])),
            (keys.distance, Itemstream([10])),
            (keys.percent, Itemstream([.01]))
        ])
        self.pfields=[
            keys.instrument,
            keys.start_time,
            keys.duration,
            keys.amplitude,
            keys.frequency,
            keys.pan,
            keys.distance,
            keys.percent
        ]

        self.gen_lines = [';sine\n',
                               'f 1 0 16384 10 1\n',
                               ';saw',
                               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
                               ';pulse\n',
                               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        self.note_limit = 0


    def with_rhythm(self, v):
        return self.rhythms(v)

    # for brevity, pfield setters
    # 2024.05.27: for rhythms, I added this safeguard since I seem to forget to set all the things for rhythms to
    #   be generated as I work through the fluent interface.
    def rhythms(self, v):
        if isinstance(v, str) or isinstance(v, list):
            self.set_stream(StreamKey().rhythm, Itemstream(v, notetype=notetypes.rhythm))
        elif isinstance(v, Itemstream):
            # don't assume this is notetypes==rhythm - this could be numbers
            # v.notetype = notetypes.rhythm
            self.set_stream(StreamKey().rhythm, v)
        else:
            raise Exception("rhythm not set - supply ItemStream, string, or list")
        return self

    def with_tempo(self, x):
        return self.tempo(x)

    def tempo(self, x):
        self.streams[keys.rhythm].tempo = x
        return self

    def with_instr(self, v):
        return self.instr(v)

    def instr(self, v):
        self.set_stream(StreamKey().instrument, v)
        return self


    def with_duration(self, v):
        return self.durs(v)

    def durs(self, v):
        self.set_stream(StreamKey().duration, v)
        return self

    def with_amps(self, v):
        return self.amps(v)

    def amps(self, v):
        self.set_stream(StreamKey().amplitude, v)
        return self

    def with_pitches(self, v):
        return self.pitches(v)

    def pitches(self, v):
        if isinstance(v, str) or isinstance(v, list):
            self.set_stream(StreamKey().frequency, Itemstream(v, notetype=notetypes.pitch))
        elif isinstance(v, Itemstream):
            v.notetype = notetypes.pitch
            self.set_stream(StreamKey().frequency, v)
        else:
            raise Exception("pitches not set - supply ItemStream, string, or list")
        return self

    def with_freqs(self, v):
        return self.freqs(v)

    def freqs(self, v):
        self.set_stream(StreamKey().frequency, v)
        return self

    def with_pan(self, v):
        return self.pan(v)

    def pan(self, v):
        self.set_stream(StreamKey().pan, v)
        return self

    def with_dist(self, v):
        return self.dist(v)

    def dist(self, v):
        self.set_stream(StreamKey().distance, v)
        return self

    def with_percent(self, v):
        return self.pct(v)

    def pct(self, v):
        self.set_stream(StreamKey().percent, v)
        return self

    def with_index(self, v):
        return self.index(v)

    def index(self, v):
        self.set_stream(StreamKey().index, v)
        return self




_PendingSwap = namedtuple('PendingSwap', ['notes', 'target_beat'])


class NoteGeneratorThread(threading.Thread):

    def __init__(self, g, cs, cpt, sleep_interval=.0001, link_follower=None, streaming=False,
                 lookahead_secs=2.0):
        self.g = g
        self.cs = cs
        self.cpt = cpt
        self.sleep_interval = sleep_interval
        self.stop_event = threading.Event()
        self.thread = threading.Thread.__init__(self)
        self.lock = threading.Lock()
        self.link_follower = link_follower
        self._pending_swap = None
        self._streaming = streaming
        self._lookahead_secs = lookahead_secs
        self._buffer = deque()   # (start_time_float, note_str) pairs, time-ordered
        self._dispatch_ahead = 0.1  # dispatch notes up to 100ms before due time
        self._probe_interval = 2.0  # seconds between sync probes
        self._last_probe_time = 0.0
        self._cursor_heap = []   # (cur_time, cursor_index, generator) min-heap
        self._cursors = []       # flat list of all generators (parent + children)
        return

    def run(self):
        g = self.g
        cs = self.cs
        cpt = self.cpt
        sleep_interval = self.sleep_interval
        g.thread_started = True

        arbitrary_score_time = 0
        while not self.stop_event.is_set():
            score_time = cs.scoreTime()

            self._poll_link()
            self._check_pending_swap()

            if self._streaming:
                self._fill_buffer(score_time + self._lookahead_secs)
                while self._buffer and self._buffer[0][0] <= score_time + self._dispatch_ahead:
                    start, note_str = self._buffer.popleft()
                    n = note_str.split()
                    n[1] = '{:.6f}'.format(max(0.0, start - score_time))
                    cpt.inputMessage('\t'.join(n))
                    beat_at_sched = self.link_follower.current_beat(start) if self.link_follower else None
                    if beat_at_sched is not None:
                        print("[dispatch] sched={:.4f} score={:.4f} beat={:.4f} beat%1={:.4f}".format(
                            start, score_time, beat_at_sched, beat_at_sched % 1), flush=True)
            else:
                if not self.lock.locked():
                    self.lock.acquire()
                    for note in [note for note in g.notes if
                                 float(note.split()[1]) >= arbitrary_score_time and float(note.split()[1]) < score_time]:
                        n = note.split()
                        n[1] = '0.0'
                        cpt.inputMessage('\t'.join(n))
                    self.lock.release()

            # Periodic sync probe: compare our model against fresh carabiner data
            if self.link_follower is not None and self._streaming:
                if score_time - self._last_probe_time >= self._probe_interval:
                    self._last_probe_time = score_time
                    mono_before = time.monotonic()
                    score_before = self._csound_time()
                    model_b, probe_b, delta, drained_b, drained_a, rtt = self.link_follower.probe_sync(score_before)
                    model_recv = self.link_follower.current_beat(score_before + rtt)
                    model_mid = self.link_follower.current_beat(score_before + rtt / 2.0)
                    delta_recv = model_recv - probe_b
                    delta_mid = model_mid - probe_b
                    bpm = self.link_follower.bpm
                    print("[probe] score={:.4f} bpm={:.0f} rtt={:.3f}ms | delta_send={:+.3f}ms delta_mid={:+.3f}ms delta_recv={:+.3f}ms".format(
                        score_time, bpm, rtt * 1000,
                        delta * 60000.0 / bpm,
                        delta_mid * 60000.0 / bpm,
                        delta_recv * 60000.0 / bpm), flush=True)

            arbitrary_score_time = score_time
            time.sleep(sleep_interval)

        self.stop_event.clear()

    def gen(self, quantize=None):
        if self._streaming:
            if quantize is None or self.link_follower is None:
                self._reset_all_cursors()
                self._flush_stale_buffer()
                if self.link_follower is not None:
                    self._beat_snap_all_cursors()
                else:
                    self._fast_forward_to(self._csound_time())
                print("Streaming: cursor reset, buffer flushed.")
            else:
                q = {'beat': 1, 'bar': 4}.get(quantize, quantize)
                target = self.link_follower.next_boundary(self._csound_time(), quantum=q)
                self._pending_swap = _PendingSwap(notes=None, target_beat=target)
                print("Streaming reset queued at beat " + str(target))
        else:
            print(str(len(self.g.notes)) + " pre-copy.")
            temp = self.g.deepcopy_tree()
            temp.generate_notes()
            print(str(len(temp.notes)) + " generated. Copying...")
            if quantize is None or self.link_follower is None:
                self.lock.acquire()
                self.g.notes = temp.notes
                self.lock.release()
                print(str(len(self.g.notes)) + " post-copy.")
            else:
                q = {'beat': 1, 'bar': 4}.get(quantize, quantize)
                target = self.link_follower.next_boundary(self._csound_time(), quantum=q)
                self._pending_swap = _PendingSwap(notes=temp.notes, target_beat=target)
                print("Swap queued at beat " + str(target))

    def _csound_time(self):
        return self.cs.scoreTime()

    def _init_cursors(self):
        """Flatten the generator tree into a cursor list and build the heap.

        Calls reset_cursor() on each generator so streaming starts fresh
        even if generate_notes() was called earlier (which exhausts
        note_count and cur_time).
        """
        self._cursors = []
        self._collect_cursors(self.g, parent=None)
        for c in self._cursors:
            c.reset_cursor()
        self._cursor_heap = [(c.cur_time, i, c) for i, c in enumerate(self._cursors)]
        heapq.heapify(self._cursor_heap)

    def _collect_cursors(self, generator, parent):
        """Recursively walk the tree, applying limit inheritance and start_time offsets.

        Mirrors the child-setup logic in generate_notes() (lines 305-325) so that
        streaming and batch produce identical output for the same generator tree.
        """
        if parent is not None:
            if generator.generator_dur > 0:
                generator.time_limit = generator.start_time + generator.generator_dur
            else:
                generator.start_time += parent.start_time
            if parent.time_limit > 0 and generator.time_limit == 0:
                generator.time_limit = parent.time_limit
            if parent.note_limit > 0 and generator.note_limit == 0:
                generator.note_limit = parent.note_limit
        self._cursors.append(generator)
        for child in generator.generators:
            self._collect_cursors(child, parent=generator)

    def _reset_all_cursors(self, reset_streams=False):
        """Reset every cursor in the tree and rebuild the heap."""
        if not self._cursors:
            self._init_cursors()
        for c in self._cursors:
            c.reset_cursor(reset_streams=reset_streams)
        self._cursor_heap = [(c.cur_time, i, c) for i, c in enumerate(self._cursors)]
        heapq.heapify(self._cursor_heap)

    def _fill_buffer(self, target_time):
        """Generate notes into the lookahead buffer up to target_time.

        When the generator has children, pulls from a min-heap of cursors so
        notes from all voices are interleaved by start time.
        """
        if not self._cursors:
            self._init_cursors()

        while self._cursor_heap:
            next_time, idx, cursor = self._cursor_heap[0]
            if next_time >= target_time:
                break
            heapq.heappop(self._cursor_heap)
            note_str = cursor.generate_next_note()
            if note_str is None:
                continue
            start = float(note_str.split()[1])
            self._buffer.append((start, note_str))
            heapq.heappush(self._cursor_heap, (cursor.cur_time, idx, cursor))

    def _flush_stale_buffer(self):
        """Discard all buffered notes past the current score time."""
        score_time = self._csound_time()
        self._buffer = deque((t, n) for t, n in self._buffer if t <= score_time)

    def _fast_forward_to(self, target_time):
        """Generate and discard notes until g.cur_time reaches target_time.

        Used after reset_cursor() so stream state advances to the correct
        musical position without dispatching old notes as a burst.
        """
        while self.g.cur_time < target_time:
            note_str = self.g.generate_next_note()
            if note_str is None:
                break

    def _poll_link(self):
        """Check for a BPM change from the Link session and update tempos."""
        if self.link_follower is None or not self.link_follower.connected:
            return
        new_bpm = self.link_follower.poll()
        if new_bpm is not None:
            # Re-anchor with an active probe rather than trusting the
            # pushed status line (which was in-flight for an unknown
            # amount of time, introducing a stale-read offset).
            self.link_follower.establish_sync_via_probe(self._csound_time)
            self._update_tempos(new_bpm)
            if self._streaming:
                self._flush_stale_buffer()
                self._beat_snap_all_cursors()
                print("[poll_link] new_bpm={} score_time={} last_beat={} g.cur_time={}".format(
                    new_bpm, self._csound_time(), self.link_follower._last_beat, self.g.cur_time), flush=True)

    def _beat_snap_cursor(self):
        """Set g.cur_time to the Csound time of the next Link beat boundary.

        Replaces _fast_forward_to() in streaming mode: instead of advancing
        stream state to score_time (which lands mid-beat), we position the
        cursor exactly on the next integer beat so the first generated note
        is phase-locked to the Link grid.
        """
        score_time = self._csound_time()
        current_beat = self.link_follower.current_beat(score_time)
        next_beat = math.floor(current_beat) + 1
        self.g.cur_time = self.link_follower.csound_time_for_beat(next_beat)

    def _beat_snap_all_cursors(self):
        """Snap all cursors to the next Link beat boundary and rebuild the heap."""
        if not self._cursors:
            self._init_cursors()
        snap_time = self._csound_time()
        current_beat = self.link_follower.current_beat(snap_time)
        next_beat = math.floor(current_beat) + 1
        beat_csound_time = self.link_follower.csound_time_for_beat(next_beat)
        for cursor in self._cursors:
            if cursor.start_time <= beat_csound_time:
                cursor.cur_time = beat_csound_time
            # else: child hasn't started yet — leave cur_time at its start_time
        self._cursor_heap = [(c.cur_time, i, c) for i, c in enumerate(self._cursors)]
        heapq.heapify(self._cursor_heap)

    def _check_pending_swap(self):
        """Fire a queued quantized swap (batch) or cursor reset (streaming)."""
        if self._pending_swap is None or self.link_follower is None:
            return
        if self.link_follower.current_beat(self._csound_time()) >= self._pending_swap.target_beat:
            if self._streaming:
                self._reset_all_cursors()
                self._flush_stale_buffer()
                self._beat_snap_all_cursors()
                self._pending_swap = None
            else:
                with self.lock:
                    self.g.notes = self._pending_swap.notes
                    self._pending_swap = None

    def _update_tempos(self, bpm):
        """Set tempo on all rhythm-notetype Itemstreams in generator and children."""
        self._set_generator_tempos(self.g, bpm)

    def _set_generator_tempos(self, generator, bpm):
        for stream in generator.streams.values():
            if isinstance(stream, Itemstream) and stream.notetype == notetypes.rhythm:
                stream.tempo = bpm
        for child in generator.generators:
            self._set_generator_tempos(child, bpm)


def kickoff(g, orc_file, scorestring="f1 0 513 10 1\ni99 0 3600 10\ne\n", device_string='dac',
            link_follower=None, streaming=False, lookahead_secs=2.0):
    cs = cs_utils.init_csound_with_orc(['-o'+device_string, '--devices', '-+rtaudio=CoreAudio'],
                                       orc_file,
                                       True,
                                       None)
    cs.readScore(scorestring)
    cs.start()
    cpt = ctcsound.CsoundPerformanceThread(cs.csound())
    cpt.play()

    if link_follower is not None:
        link_follower.establish_sync_via_probe(lambda: cs.scoreTime())
        if streaming:
            # Snap generator cursor to the next beat boundary so the first note
            # lands on a beat rather than wherever Csound happened to start.
            score_time = cs.scoreTime()
            current_beat = link_follower.current_beat(score_time)
            next_beat = math.floor(current_beat) + 1
            g.cur_time = link_follower.csound_time_for_beat(next_beat)

    t = NoteGeneratorThread(g, cs, cpt, link_follower=link_follower,
                            streaming=streaming, lookahead_secs=lookahead_secs)
    if streaming and link_follower is not None:
        # Sync generator tempo to the current Link BPM before the thread starts.
        # _update_tempos() only fires on BPM *changes* in the run loop, so if the
        # session has been at a steady tempo since connect() the generator would
        # otherwise keep its constructor tempo indefinitely.
        t._update_tempos(link_follower.bpm)
    t.daemon = True
    t.start()
    return t

def ko(g, orc_file, scorestring="f1 0 513 10 1\ni99 0 3600 10\ne\n", device_string='dac',
       link_follower=None, streaming=False, lookahead_secs=2.0):
    return kickoff(g, orc_file, scorestring=scorestring, device_string=device_string,
                   link_follower=link_follower, streaming=streaming, lookahead_secs=lookahead_secs)