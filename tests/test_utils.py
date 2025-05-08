from __future__ import print_function
import unittest
from context import thuja
from thuja.itemstream import Itemstream
from thuja.notegenerator import NoteGenerator
from thuja.streamkeys import keys
import thuja.utils as utils

from collections import OrderedDict
import numpy as np


class TestUtils(unittest.TestCase):
    semitones = [
        # (frequency, midi, pitch, octave),
        (    0.00,   0, 'c',  -1),
        (    8.66,   1, 'cs', -1),
        (    9.18,   2, 'd',  -1),
        (   10.30,   4, 'e',  -1),
        (   10.91,   5, 'f',  -1),
        (   12.98,   8, 'gs', -1),
        (   20.60,  16, 'e',   0),
        (   32.70,  24, 'c',   1),
        (   34.65,  25, 'cs',  1),
        (   51.91,  32, 'gs',  1),
        (   73.42,  38, 'd',   2),
        (  110.00,  45, 'a',   2),
        (  261.63,  60, 'c',   4),
        (  329.63,  64, 'e',   4),
        ( 1760.00,  93, 'a',   6),
        ( 2793.83, 101, 'f',   7),
        (13289.75, 128, 'gs',  9),
        ]

    def test_rhythms(self):
        self.assertTrue(utils.add_rhythm('w', 's') == 'w+s')
        self.assertTrue(utils.add_rhythm('h', 's') == 'h+s')
        self.assertTrue(utils.add_rhythm('q', 's') == 'q..')
        self.assertTrue(utils.add_rhythm('e', 's') == 'e.')
        self.assertTrue(utils.add_rhythm('s', 's') == 'e')
        self.assertTrue(utils.subtract_rhythm('w', 's') == 'h+q+e.')
        self.assertTrue(utils.subtract_rhythm('h', 's') == 'q+e.')
        self.assertTrue(utils.subtract_rhythm('q', 's') == 'e.')
        self.assertTrue(utils.subtract_rhythm('e', 's') == 's')
        self.assertTrue(utils.subtract_rhythm('s', 's') == '')
        self.assertTrue(utils.rhythm_string_to_val('s') == .25)
        self.assertTrue(round(utils.rhythm_string_to_val('12'), 2) == 0.33)
        self.assertTrue(utils.rhythm_string_to_val('s+s') == .5)
        self.assertTrue(utils.rhythm_string_to_val('s+e') == .75)
        self.assertTrue(utils.rhythm_string_to_val('s.') == .375)
        self.assertTrue(utils.rhythm_string_to_val('s+e+16') == 1)
        self.assertTrue(utils.rhythm_string_to_val('12+12+12') == 1)
        self.assertTrue(utils.val_to_rhythm_string(4) == 'w')
        self.assertTrue(utils.val_to_rhythm_string(3) == 'h.')
        self.assertTrue(utils.val_to_rhythm_string(2) == 'h')
        self.assertTrue(utils.val_to_rhythm_string(1.5) == 'q.')
        self.assertTrue(utils.val_to_rhythm_string(1.25) == 'q..')
        self.assertTrue(utils.val_to_rhythm_string(1.75) == 'q+e.')
        self.assertTrue(utils.val_to_rhythm_string(.75) == 'e.')

    def test_midinote_to_pc(self):
        for freq, midi, pitch, octave in self.semitones:
            pitch_w_octave = f"{pitch}{octave}"
            calc_pitch_w_octave = utils.midi_note_to_pc(midi)
            self.assertTrue(pitch_w_octave == calc_pitch_w_octave)

            calc_pitch = utils.midi_note_to_pc(midi, False)
            self.assertTrue(pitch == calc_pitch)

    def test_freq_to_midinote(self):
        for freq, midi, pitch, octave in self.semitones:
            calc_midi = utils.freq_to_midi_note(freq)
            self.assertTrue(midi == calc_midi)

    def test_midinote_to_freq(self):
        for freq, midi, pitch, octave in self.semitones:
            calc_freq = round(utils.midinote_to_freq(midi), 2)
            self.assertTrue(calc_freq == freq)

    def test_freq_to_pc(self):
        for freq, midi, pitch, octave in self.semitones:
            pitch_w_octave = f"{pitch}{octave}"
            calc_pitch_w_octave = utils.freq_to_pc(freq, True)
            self.assertTrue(pitch_w_octave == calc_pitch_w_octave)

            calc_pitch = utils.freq_to_pc(freq, False)
            self.assertTrue(pitch == calc_pitch)

    def test_pc_to_freq(self):
        for freq, midi, pitch, octave in self.semitones:
            pitch_w_octave = f"{pitch}{octave}"
            for default in (octave, octave+1):  # test with wrong default octave
                calc = utils.pc_to_freq(pitch_w_octave, default)
                calc_freq = round(calc['value'], 2)
                self.assertTrue(freq == calc_freq)

if __name__ == '__main__':
    unittest.main()
