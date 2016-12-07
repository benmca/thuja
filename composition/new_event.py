from collections import OrderedDict

class NewEvent:
    # ----------------------------------------------------------------------
    def __init__(self, pfields=None):
        """Constructor"""
        # OrderedDict here
        self.pfields = OrderedDict()
        for item in pfields:
            self.pfields[item] = ''

    def __str__(self):
        return 'i'+'\t'.join(map(str, self.pfields.values()))
