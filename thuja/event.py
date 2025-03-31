from collections import OrderedDict
from streamkeys import keys

class Event:
    """
    This little primitive is the Note in Thuja - it contains the pfield dictionary and
    provides access to rhythm and string representation for csound score export.
    """
    # ----------------------------------------------------------------------
    def __init__(self, pfields=None, start_time=None):
        """Constructor"""
        # OrderedDict here
        self.pfields = OrderedDict()
        for item in pfields:
            self.pfields[item] = ''

        # 2025.03.25 todo - how to make keys a singleton that can be imported here
        self.pfields[keys.start_time] = start_time
        self.rhythm = None

    def __str__(self):
        return 'i'+'\t'.join(map(str, self.pfields.values()))
