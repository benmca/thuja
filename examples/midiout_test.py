import csnd6

with open("test.orc", "r") as f:
    orc_string = f.read()
with open("test.sco", "r") as sco:
    score_string = sco.read()

cs = csnd6.Csound()
cs.CompileOrc(orc_string)
cs.ReadScore(score_string)
cs.SetOption('-odac')
cs.SetOption('-Q0')
cs.SetOption('-b64')
cs.SetOption('-B64')
cs.Start()
cs.Perform()
cs.Stop()
