class event:
    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.instr = 1
        self.starttime = 0.0
        self.dur = None
        self.freq = None
        self.amp = None
        self.indx = None
        self.pfields = []

    def __str__(self):
        rep = ["i" + str(self.instr), str(self.starttime)]
        pfield_indx = 0

        if (self.dur != None):
            rep.append(str(self.dur))
        else:
            rep.append(str(self.pfields[0]))
            pfield_indx = pfield_indx + 1

        if (self.amp != None):
            rep.append(str(self.amp))
        else:
            rep.append(str(self.pfields[pfield_indx]))
            pfield_indx = pfield_indx + 1

        if (self.freq != None):
            rep.append(str(self.freq))
        else:
            rep.append(str(self.pfields[pfield_indx]))
            pfield_indx = pfield_indx + 1

        if (self.indx != None):
            rep.append(str(self.indx))

        rep = sum([rep, self.pfields[pfield_indx:]], [])

        return "\t".join(rep)
