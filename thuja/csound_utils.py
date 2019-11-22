import ctcsound


def play_csound(orc_file, generator, args_list=['-odac', '-W'], string_values=None, silent=False):
    with open(orc_file, "r") as f:
        orc_string = f.read()
    if silent:
        args_list.append("-m0")
        args_list.append("-d")
    score_string = generator.generate_score_string()
    cs = ctcsound.Csound()

    cs.compileOrc(orc_string)
    cs.readScore(score_string)
    for x in args_list:
        cs.setOption(x)
    if string_values:
        for k in string_values.keys():
            cs.setStringChannel(k, string_values[k])
    cs.start()
    cs.perform()
    cs.stop()
