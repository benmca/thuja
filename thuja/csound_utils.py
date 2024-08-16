import ctcsound


def init_csound_with_orc(args_list, orc_file, silent, string_values):
    """
    Initializes a Csound instance with an ORC file.

    Parameters:
        args_list (list): A list of command-line arguments to be passed to Csound.
        orc_file (str): The path to the ORC file to be compiled.
        silent (bool): A flag indicating whether to run Csound in silent mode.
        string_values (dict): A dictionary of string values to be set as Csound channels.

    Returns:
        ctcsound.Csound: The initialized Csound instance.
    """
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
    """
    Initializes a Csound instance with a CSD file.

    Args:
        args_list (list): A list of command-line arguments to be passed to Csound.
        csd_file (str): The path to the CSD file to be compiled.
        silent (bool): A flag indicating whether to run Csound in silent mode.
        string_values (dict): A dictionary of string values to be set as Csound channels.

    Returns:
        ctcsound.Csound: The initialized Csound instance.
    """
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


def play_csound(orc_file, generator, args_list=['-odac', '-W'], string_values=None, silent=False):
    """
    Plays a Csound instance with the given ORC file, generator, and arguments.

    Parameters:
        orc_file (str): The path to the ORC file to be compiled.
        generator: An object that generates a score string.
        args_list (list): A list of command-line arguments to be passed to Csound. Defaults to ['-odac', '-W'].
        string_values (dict): A dictionary of string values to be set as Csound channels. Defaults to None.
        silent (bool): A flag indicating whether to run Csound in silent mode. Defaults to False.

    Returns:
        None
    """
    with open(orc_file, "r") as f:
        orc_string = f.read()
    if silent:
        args_list.append("-m0")
        args_list.append("-d")
    score_string = generator.generate_score_string()
    cs = init_csound_with_orc(args_list, orc_file, silent, string_values)
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

