
def caget(name, as_string=False):
    # We import CaChannelWrapper when used as this means the tests can run without
    # having genie_python installed
    from genie_python.genie_cachannel_wrapper import CaChannelWrapper
    try:
        return CaChannelWrapper.get_pv_value(name, as_string)
    except Exception as err:
        #Probably has timed out
        print err
        return None


def caput(name, value, wait=False):
    # We import CaChannelWrapper when used as this means the tests can run without
    # having genie_python installed
    from genie_python.genie_cachannel_wrapper import CaChannelWrapper
    try:
        CaChannelWrapper.set_pv_value(name, value, wait)
    except Exception as err:
        print err
        raise err

