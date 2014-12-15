#FUDGE, DO NOT COMMIT

from CaChannel import ca, CaChannel, CaChannelException

TIMEOUT = 15
CACHE = dict()


class CaChannelWrapper(object):
    @staticmethod
    def _waveform2string(data):
        output = ""
        for i in data:
            if i == 0:
                break
            output += str(unichr(i))
        return output

    @staticmethod
    def set_pv_value(name, value, wait=False, timeout=TIMEOUT):
        """Set the PV to a value.
           When getting a PV value this call should be used, unless there is a special requirement.

        Parameters:
            name - the PV name
            value - the value to set
            wait - wait for the value to be set before returning
        """
        if name not in CACHE.keys():
            chan = CaChannel(name)
            chan.setTimeout(TIMEOUT)
            #Try to connect - throws if cannot
            chan.searchw()
            CACHE[name] = chan
        else:
            chan = CACHE[name]
        if wait:
            chan.putw(value)
        else:
            def putCB(epics_args, user_args):
                #Do nothing in the callback
                pass
            ftype = chan.field_type()
            ecount = chan.element_count()
            chan.array_put_callback(value, ftype, ecount, putCB)
            chan.flush_io()

    @staticmethod
    def get_pv_value(name, to_string=False, timeout=TIMEOUT):
        """Get the current value of the PV"""
        if name not in CACHE.keys():
            chan = CaChannel(name)
            chan.setTimeout(TIMEOUT)
            #Try to connect - throws if cannot
            chan.searchw()
            CACHE[name] = chan
        else:
            chan = CACHE[name]
        ftype = chan.field_type()
        if ca.dbr_type_is_ENUM(ftype) or ca.dbr_type_is_CHAR(ftype) or ca.dbr_type_is_STRING(ftype):
            to_string = True
        if to_string:
            if ca.dbr_type_is_ENUM(ftype):
                value = chan.getw(ca.DBR_STRING)
            else:
                value = chan.getw(ca.DBR_CHAR)
            #Could see if the element count is > 1 instead
            if isinstance(value, list):
                return CaChannelWrapper._waveform2string(value)
            else:
                return str(value)
        else:
            return chan.getw()

    @staticmethod
    def pv_exists(name):
        """See if the PV exists"""
        try:
            chan = CaChannel(name)
            #Try to connect - throws if cannot
            chan.searchw()
            return True
        except:
            return False

def caget(name, as_string=False):
    # We import CaChannelWrapper when used as this means the tests can run without
    # having genie_python installed
    #from genie_python.genie_cachannel_wrapper import CaChannelWrapper
    try:
        return CaChannelWrapper.get_pv_value(name, as_string)
    except Exception as err:
        #Probably has timed out
        print err
        return None


def caput(name, value, wait=False):
    # We import CaChannelWrapper when used as this means the tests can run without
    # having genie_python installed
    #from genie_python.genie_cachannel_wrapper import CaChannelWrapper
    try:
        CaChannelWrapper.set_pv_value(name, value, wait)
    except Exception as err:
        print err
        raise err

