import csnd6

def play_csound(orc_file, generator, args_string='-odac', string_values=None):
    with open(orc_file, "r") as f:
        orc_string = f.read()
    score_string = generator.generate_score_string()
    cs = csnd6.Csound()
    cs.CompileOrc(orc_string)
    cs.ReadScore(score_string)
    cs.SetOption(args_string)
    if string_values:
        for k in string_values.keys():
            cs.SetStringChannel(k, string_values[k])
    cs.Start()
    cs.Perform()
    cs.Stop()
