import csnd6


def play_csound(orc_file, generator, args_list=['-odac', '-W'], string_values=None, silent=False):
    with open(orc_file, "r") as f:
        orc_string = f.read()
    if silent:
        args_list.append("-m0")
        args_list.append("-d")
    score_string = generator.generate_score_string()
    cs = csnd6.Csound()
    cs.CompileOrc(orc_string)
    cs.ReadScore(score_string)
    for x in args_list:
        cs.SetOption(x)
    if string_values:
        for k in string_values.keys():
            cs.SetStringChannel(k, string_values[k])
    cs.Start()
    cs.Perform()
    cs.Stop()
