import unittest
from context import thuja
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
import thuja.utils as utils

from collections import OrderedDict
import numpy as np


class TestUtils(unittest.TestCase):

    def test_midinote_to_pc(self):
        self.assertTrue(utils.midi_note_to_pc(1) == 'cs1')
        self.assertTrue(utils.midi_note_to_pc(1, False) == 'cs')
        self.assertTrue(utils.midi_note_to_pc(0) == 'c1')
        self.assertTrue(utils.midi_note_to_pc(36, False) == 'c')
        self.assertTrue(utils.midi_note_to_pc(36) == 'c4')

    def test_freq_to_midinote(self):
        self.assertTrue(utils.freq_to_midi_note(73.4161919794) == 38)
        self.assertTrue(utils.freq_to_midi_note(8.1757989156) == 0)
        self.assertTrue(utils.freq_to_midi_note(8.6619572180) == 1)
        self.assertTrue(utils.freq_to_midi_note(10.9133822323) == 5)
        self.assertTrue(utils.freq_to_midi_note(2793.8258514640) == 101)
        self.assertTrue(utils.freq_to_midi_note(8.66) == 1)
        self.assertTrue(utils.freq_to_midi_note(110) == 45)

    def test_midinote_to_freq(self):
        self.assertTrue(round(utils.midinote_to_freq(38), 2) == 73.42)
        self.assertTrue(round(utils.midinote_to_freq(0), 2) == 8.18)
        self.assertTrue(round(utils.midinote_to_freq(1), 2) == 8.66)
        self.assertTrue(round(utils.midinote_to_freq(5), 2) == 10.91)
        self.assertTrue(round(utils.midinote_to_freq(101), 2) == 2793.83)
        self.assertTrue(round(utils.midinote_to_freq(45), 2) == 110)

    def test_freq_to_pc(self):
        self.assertTrue(utils.freq_to_pc(8.66, False) == 'cs')
        self.assertTrue(utils.freq_to_pc(110, True) == 'a4')


    def test_pc_to_freq(self):
        self.assertTrue(round(utils.pc_to_freq('a4',4)['value'] ,2) == 110.0)
        self.assertTrue(round(utils.pc_to_freq('a4',1)['value'] ,2) == 110.0)
        self.assertTrue(round(utils.pc_to_freq('a6',1)['value'] ,2) == 440.0)

if __name__ == '__main__':
    unittest.main()
