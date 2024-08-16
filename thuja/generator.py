import random
import sys

from thuja.itemstream import Itemstream
from thuja.itemstream import Streammodes
from thuja.itemstream import notetypes

from thuja.event import Event
from thuja import utils
from collections import OrderedDict
import copy
import funcsigs
import socket
import logging
import threading
import time


class StreamKey:

    instrument = 'instr'
    start_time = 'start_time'
    duration = 'dur'
    rhythm = 'rhy'
    amplitude = 'amp'
    frequency = 'freq'

    # support loopindx
    index = 'indx'

    # locsig support
    pan = 'pan'
    distance = 'dist'
    percent = 'pct'

    def __init__(self):
        # the usual suspects
        self.instrument = 'instr'
        self.start_time = 'start_time'
        self.duration = 'dur'
        self.rhythm = 'rhy'
        self.amplitude = 'amp'
        self.frequency = 'freq'

        # support loopindx
        self.index = 'indx'

        # locsig support
        self.pan = 'pan'
        self.distance = 'dist'
        self.percent = 'pct'




class Generator:

    def __init__(self, note_limit=16,
                 start_time=0.0,
                 streams=None,
                 pfields=None,
                 post_processes=[],
                 init_context={},
                 gen_lines=[]):
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
        if streams is not None:
            self.streams = OrderedDict(streams)
        self.note_limit = note_limit

        self.cur_time = 0.0
        self.time_limit = 0

        self.gen_lines = gen_lines
        self.note_count = 0
        self.notes = []
        self.end_lines = []
        self.score_dur = 0

        self.pfields = pfields
        if pfields is None:
            if self.streams is not None:
                self.pfields = list(self.streams.keys())
                self.pfields.insert(1, keys.start_time)

        # a place to put stuff to refer to in callables - not sure best way forward here
        self.context = init_context
        self.post_processes = post_processes
        self.generators = []

    def with_streams(self, streams):
        if isinstance(streams, OrderedDict):
            self.streams = streams
        if streams is None:
            pass
        else:
            self.streams = OrderedDict(streams)

    def with_pfields(self, pfields):
        self.pfields = pfields
        return self

    def deepcopy(self):
        result = copy.deepcopy(self)
        result.streams = OrderedDict()
        for k, v in self.streams.items():
            # setattr(result, k, deepcopy(v, memo))
            result.streams.__setitem__(k, copy.deepcopy(v))
        return result

    def update_stream(self, key, stream):
        self.streams[key] = stream
        return self

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

    def generate_notes(self):
        self.note_count = 0
        self.cur_time = self.start_time
        ret_lines = []
        # todo - audit this, but looks like I intended note_limit to trump time_limit
        while (self.note_limit > 0 and (self.note_count < self.note_limit)) or (self.time_limit > 0):
        # while (self.note_limit > 0 and (self.note_count < self.note_limit)) or ((self.time_limit > 0) and self.cur_time < self.time_limit):
            note = Event(pfields=self.pfields)
            note.pfields[keys.start_time] = self.cur_time

            # todo - validate we're ok to roll: we have at least an instr and rhythm
            note_is_chording = False
            rhythm = None
            for key in self.streams.keys():
                if key is keys.rhythm:
                    continue
                # this could be a literal or ItemStream
                if not isinstance(self.streams[key], Itemstream) and not callable(self.streams[key]):
                    note.pfields[key] = self.streams[key]
                elif isinstance(self.streams[key], Itemstream):
                    value = self.streams[key].get_next_value()

                    # support mapping stream
                    # i.e.  [{"rhy": "h", "indx": 5.54}, {"rhy": "h", "indx": 6.67}, {"rhy": "h", "indx": 8.0}]
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
                    # 2024.01.31 added this clause instead of this being the default.
                    #   test_generator was tripping here. A todo might be to be prescriptive in checking that - if
                    #   if rhy isn't set in post_processes OR here, we should error out.
                    rhythm = self.streams[keys.rhythm].get_next_value()
                    self.cur_time = self.cur_time + rhythm
                    note.rhythm = rhythm

            # 2024.01.07 - not sure if this is an issue, but I'm changing this so callables can access rhythm
            #   did I think we would want to do post-processing BEFORE curtime is set or something?
            for item in self.post_processes:
                if callable(item):
                    if len(funcsigs.signature(item).parameters) > 1:
                        item(note, self.context)
                    else:
                        item(note)

            # after setting primitives and ItemStream-driven values, evaluate functions
            for key in self.streams.keys():
                # this could be a literal or ItemStream
                if callable(self.streams[key]):
                    value = self.streams[key](note)
                    note.pfields[key] = value

            if self.cur_time > self.time_limit > 0:
                break
            else:
                ret_lines.append(str(note) + "\n")
                self.notes.append(str(note) + "\n")
                self.note_count += 1
                if (note.pfields[keys.start_time] + note.pfields[keys.duration]) > self.score_dur:
                    self.score_dur = (note.pfields[keys.start_time] + note.pfields[keys.duration])

        for g in self.generators:
            g.start_time += self.start_time
            if self.time_limit > 0 and g.time_limit == 0:
                g.time_limit = self.time_limit
            if self.note_limit > 0 and g.note_limit == 0:
                g.note_limit = self.note_limit
            g.generate_notes()
            self.notes.extend(g.notes)
            if g.score_dur > self.score_dur:
                self.score_dur = g.score_dur

        return self

    def add_generator(self, other):
        if isinstance(other, Generator):
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

    def tempo(self):
        return self.streams[keys.rhythm].tempo

    def set_streams_to_seed(self, seed):
        for s in self.streams.values():
            if isinstance(s, Itemstream):
                s.set_seed(seed)


class BasicLine(Generator):

    def __init__(self):
        Generator.__init__(self)
        self.streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([1])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
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
        self.note_limit = 1


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
            # assume this is an single item string and pass value through to ItemStream
            self.streams[k] = Itemstream(v)

    def with_rhythm(self, v):
        self.rhythms(v)
        return self

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

    def with_tempo(self, x):
        self.tempo(x)
        return self

    def tempo(self, x):
        self.streams[keys.rhythm].tempo = x

    def with_duration(self, v):
        self.durs(v)
        return self

    def durs(self, v):
        self.set_stream(StreamKey().duration, v)

    def with_amps(self, v):
        self.amps(v)
        return self

    def amps(self, v):
        self.set_stream(StreamKey().amplitude, v)

    def with_pitches(self, v):
        self.pitches(v)
        return self

    def pitches(self, v):
        if isinstance(v, str) or isinstance(v, list):
            self.set_stream(StreamKey().frequency, Itemstream(v, notetype=Notetypes().pitch))
        elif isinstance(v, Itemstream):
            v.notetype = notetypes.pitch
            self.set_stream(StreamKey().frequency, v)
        else:
            raise Exception("pitches not set - supply ItemStream, string, or list")

    def with_freqs(self, v):
        self.freqs(v)
        return self

    def freqs(self, v):
        self.set_stream(StreamKey().frequency, v)

    def with_pan(self, v):
        self.pan(v)
        return self

    def pan(self, v):
        self.set_stream(StreamKey().pan, v)

    def with_dist(self, v):
        self.dist(v)
        return self

    def dist(self, v):
        self.set_stream(StreamKey().distance, v)

    def with_percent(self, v):
        self.pct(v)
        return self

    def pct(self, v):
        self.set_stream(StreamKey().percent, v)

    def randomize(self):
        seed = random.Random().randint(0, sys.maxsize)
        self.set_streams_to_seed(seed)
        print(str(seed))
        return self

    def with_index(self, v):
        self.index(v)
        return self

    def index(self, v):
        self.set_stream(StreamKey().index, v)


    def setup_index_params_with_file(self, filename):
        self.set_stream('orig_rhythm', .01)
        self.set_stream('inst_file', ['\"' + filename + '\"'])
        self.set_stream('fade_in', .0001)
        self.set_stream('fade_out', .01)
        self.pfields += [keys.index, 'orig_rhythm', 'inst_file', 'fade_in', 'fade_out']
        return self



class GeneratorThread(threading.Thread):

    def __init__(self, g, cs, sleep_interval=.1):
        self.g = g
        self.cs = cs
        self.sleep_interval = sleep_interval
        self.stop_event = threading.Event()
        threading.Thread.__init__(self)
        return

    def run(self):
        g = self.g
        cs = self.cs
        sleep_interval = self.sleep_interval
        g.thread_started = True
        g.cur_time = 0

        # automatically generate notes if not already generated
        if g.notes is None or len(g.notes) < 1:
            g.generate_notes()

        while not self.stop_event.is_set():
            score_time = cs.scoreTime()
            if score_time > g.cur_time:
                g.time_limit = score_time
                print(str(g.cur_time) + " - " + str(score_time))
                # g.generate_notes(g.cur_time)
                for note in g.notes:
                    # continue if note is not in window between cur time or score time + sleep interval?
                    cs.inputMessage(str(note))
                    print(str(note))
                g.notes = []
                time.sleep(sleep_interval)

        self.stop_event.clear()

keys = StreamKey()
