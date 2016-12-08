from composition.generator import Generator
from composition.generator import keys
from composition.itemstream import Itemstream
from collections import OrderedDict
import numpy as np

rhythms = 'q q s e s s e s q e. e q e s'.split()
indexes = [0.018, .697, 1.376, 1.538, 1.869, 2.032, 2.2, 2.543, 2.705, 3.373, 3.895, 4.232, 4.894, 5.236]
rhy_to_idx = Itemstream(mapping_keys=[keys.rhythm, keys.index], mapping_lists=[rhythms, indexes])




