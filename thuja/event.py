from collections import OrderedDict


class Event:
    """
    This little primitive is the Note in Thuja - it contains the pfield dictionary and
    provides access to rhythm and string representation for csound score export.
    """
    # ----------------------------------------------------------------------
    def __init__(self, pfields=None):
        """Constructor"""
        # OrderedDict here
        self.pfields = OrderedDict()
        for item in pfields:
            self.pfields[item] = ''
        #rhythm sometimes used as basis for calculating other params, so save it here
        self.rhythm = None

    def __str__(self):
        return 'i'+'\t'.join(map(str, self.pfields.values()))
