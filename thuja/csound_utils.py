import ctcsound

def init_csound_with_orc(args_list, orc_file, silent, string_values):
    with open(orc_file, "r") as f:
        orc_string = f.read()
    if silent:
        args_list.append("-m0")
        args_list.append("-d")
    cs = ctcsound.Csound()
    cs.compileOrc(orc_string)
    for x in args_list:
        cs.setOption(x)
    if string_values:
        for k in string_values.keys():
            cs.setStringChannel(k, string_values[k])
    return cs


def init_csound_with_csd(args_list, csd_file, silent, string_values):
    with open(csd_file, "r") as f:
        csd_string = f.read()
    if silent:
        args_list.append("-m0")
        args_list.append("-d")
    cs = ctcsound.Csound()
    cs.compileCsd(csd_string)
    for x in args_list:
        cs.setOption(x)
    if string_values:
        for k in string_values.keys():
            cs.setStringChannel(k, string_values[k])
    return cs
