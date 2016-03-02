
def caget(name, as_string=False):
    """Uses CaChannelWrapper from genie_python to get a pv value. We import CaChannelWrapper when used as this means
    the tests can run without having genie_python installed

    Args:
        name (string): The name of the PV to be read
        as_string (bool, optional): Set to read a char array as a string, defaults to false

    Returns:
        obj : The value of the requested PV, None if no value was read
    """

    from genie_python.genie_cachannel_wrapper import CaChannelWrapper
    try:
        return CaChannelWrapper.get_pv_value(name, as_string)
    except Exception as err:
        # Probably has timed out
        print err
        return None


def caput(name, value, wait=False):
    """Uses CaChannelWrapper from genie_python to set a pv value. We import CaChannelWrapper when used as this means
    the tests can run without having genie_python installed

    Args:
        name (string): The name of the PV to be set
        value (object): The data to send to the PV
        wait (bool, optional): Wait for the PV t set before returning

    Raises:
        Exception : If the PV failed to set
    """
    from genie_python.genie_cachannel_wrapper import CaChannelWrapper
    try:
        CaChannelWrapper.set_pv_value(name, value, wait)
    except Exception as err:
        print err
        raise err

