from __future__ import print_function
import unittest
from context import thuja
import thuja.utils as utils
from thuja import sounds


class TestUtils(unittest.TestCase):
    semitones = [
        # (frequency, midi, pitch1, pitch2, octave),
        (    0.00,   0, 'c',  'C',  -1),
        (    8.66,   1, 'cs', 'C#', -1),
        (    9.18,   2, 'd',  'D',  -1),
        (   10.30,   4, 'e',  'E',  -1),
        (   10.91,   5, 'f',  'F',  -1),
        (   12.98,   8, 'gs', 'G#', -1),
        (   20.60,  16, 'e',  'E',   0),
        (   32.70,  24, 'c',  'C',   1),
        (   34.65,  25, 'cs', 'C#',  1),
        (   51.91,  32, 'gs', 'G#',  1),
        (   73.42,  38, 'd',  'D',   2),
        (  110.00,  45, 'a',  'A',   2),
        (  261.63,  60, 'c',  'C',   4),
        (  329.63,  64, 'e',  'E',   4),
        ( 1760.00,  93, 'a',  'A',   6),
        ( 2793.83, 101, 'f',  'F',   7),
        (13289.75, 128, 'gs', 'G#',  9),
        ]

    def test_midi_to_pitch(self):
        for freq, midi, _, pitch, octave in self.semitones:
            midi = sounds.MidiNote(midi)

            self.assertTrue(pitch == midi.pitch)

            pc = f"{pitch}{octave}"
            self.assertTrue(pc == midi.to_pitch_class())

    def test_freq_to_midi(self):
        for freq, midi, _, pitch, octave in self.semitones:
            calc_midi = sounds.MidiNote.from_frequency(freq).note
            self.assertTrue(midi == calc_midi)

    def test_midi_to_freq(self):
        for freq, midi, _, pitch, octave in self.semitones:
            midi = sounds.MidiNote(midi)
            calc_freq = round(midi.frequency, 2)
            self.assertTrue(freq == calc_freq)

    def test_freq_to_pc(self):
        for freq, midi, _, pitch, octave in self.semitones:
            pitch_w_octave = f"{pitch}{octave}"
            pc = sounds.PitchClass.from_frequency(freq)
            self.assertTrue(pitch_w_octave == str(pc))
            self.assertTrue(pitch == pc.pitch)

    def test_pc_to_freq(self):
        for freq, midi, _, pitch, octave in self.semitones:
            pitch_w_octave = f"{pitch}{octave}"
            pc = sounds.PitchClass(pitch_w_octave)
            calc_freq = round(pc.frequency, 2)
            self.assertTrue(freq == calc_freq)

if __name__ == '__main__':
    unittest.main()
