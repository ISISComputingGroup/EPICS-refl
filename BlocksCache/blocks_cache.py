import ca
import time
import sys
import zlib
import json
import threading
import copy
import os

sys.path.insert(0, os.path.abspath(os.environ["MYDIRBLOCK"]))

from pcaspy import SimpleServer, Driver
from CaChannel import ca, CaChannel, CaChannelException
from server_common.utilities import compress_and_hex, convert_to_json, waveform_to_string, dehex_and_decompress

EXISTS_TIMEOUT = 3 
PEND_EVENT_TIMEOUT = 0.1


PVDB = {
    'CS:BLOCKSERVER:BLOCKVALUES': {
        'type': 'char',
        'count': 64000,
        'value': [0],
    },
}


class BlocksMonitor(Driver):
    def __init__(self, prefix):
        super(BlocksMonitor, self).__init__()    
        # Holds a list of block names 
        self.block_names = None
        # Holds a dict of monitors 
        self.block_monitors = dict()
        # Holds the current values
        self.curr_values = dict()
        # Flag for stopping thread
        self.stop_thread = False
        # Thread lock for monitors
        self.mon_lock = threading.Lock()
        # Thread lock for current values - this probably is not needed, but doesn't do any harm
        self.curr_lock = threading.Lock()
        # The instrument prefix
        self.prefix = prefix
        
    def read(self, reason):
        if reason == 'CS:BLOCKSERVER:BLOCKVALUES':
            ans = convert_to_json(self._get_organised_values())
            value = compress_and_hex(ans)
        else:
            value = self.getParam(reason)
        return value
        
    def _get_organised_values(self):
        def _get_value(name):
            if name in values:
                return values[name]
            else:
                return None, None
        values = self.get_curr_values()
        blks = dict()

        for b in self.block_names:
            full_name = "%sCS:SB:%s" % (self.prefix, b)
            rcname = '%s:RC:ENABLE' % full_name
            rclname = '%s:RC:LOW' % full_name
            rchname = '%s:RC:HIGH' % full_name

            pvinfo = _get_value(full_name)

            if pvinfo[1] is not None:
                if ca.dbr_type_is_ENUM(pvinfo[1]) or ca.dbr_type_is_STRING(pvinfo[1]):
                    ftype = "STRING"
                elif ca.dbr_type_is_CHAR(pvinfo[1]):
                    ftype = "CHAR"
                else:
                    ftype = "NUMERIC"
            else:
                ftype = "UNKNOWN"

            blks[b] = (pvinfo[0], _get_value(rcname)[0], _get_value(rclname)[0], _get_value(rchname)[0], ftype)
            
        return blks
      
    def connect(self):
        def _blocknames_callback(epics_args, user_args):
            names = json.loads(dehex_and_decompress(waveform_to_string(epics_args['pv_value'])))
            if self.block_names is None or names != self.block_names:
                self.block_names = names
                print "Updated"
        
        chan = CaChannel("BLOCKNAMES")
        chan.searchw("%s%s" % (self.prefix, "CS:BLOCKSERVER:BLOCKNAMES"))
        chan.add_masked_array_event(
            ca.DBR_CHAR,
            None,
            ca.DBE_VALUE | ca.DBE_ALARM,
            _blocknames_callback)
            
        chan.pend_event(PEND_EVENT_TIMEOUT)

    def disconnect_block_monitors(self):
        self.mon_lock.acquire()
        try:
            for bn, bv in self.block_monitors.iteritems():
                if bv is not None:
                    print "disconnecting", bn
                    bv.clear_event()
                    bv.pend_event(PEND_EVENT_TIMEOUT)
            self.block_monitors = dict()
        except:
            # Don't care, it is all about releasing the lock
            pass
        finally:
            # Must release lock
            self.mon_lock.release()

    def initialise_block(self, name):
        full_name = '%sCS:SB:%s' % (self.prefix, name)

        self.mon_lock.acquire()
        try:       
            self.block_monitors[full_name] = self._initialise_channel('%s' % full_name)
            self.block_monitors['%s:RC:ENABLE' % full_name] = self._initialise_channel('%s:RC:ENABLE' % full_name)
            self.block_monitors['%s:RC:LOW' % full_name] = self._initialise_channel('%s:RC:LOW' % full_name)
            self.block_monitors['%s:RC:HIGH' % full_name] = self._initialise_channel('%s:RC:HIGH' % full_name)              
        except:
            # Don't care, it is all about releasing the lock
            pass
        finally:
            # Must release lock
            self.mon_lock.release()
            
    def _initialise_channel(self, name):
        """Creates the channel with a connection callback"""
        def _block_connection_callback(epics_args, user_args):
            connection_state = epics_args[1]
            if connection_state == ca.CA_OP_CONN_UP:
                print ca.name(epics_args[0]),  "UP"
                # First time through creates the monitor
                if ca.name(epics_args[0]) not in self.curr_values:
                    self._create_monitor(user_args[0], ca.name(epics_args[0]))
            else:
                print ca.name(epics_args[0]), "DOWN"
                self.curr_lock.acquire()
                try:
                    self.curr_values[ca.name(epics_args[0])] = ("*** disconnected", None)
                except:
                    # Don't care, it is all about releasing the lock
                    pass
                finally:
                    # Must release lock
                    self.curr_lock.release()  
    
        chan = CaChannel()
        chan.setTimeout(EXISTS_TIMEOUT)
        print "initialising %s" % name
        try:
            chan.search_and_connect(name, _block_connection_callback, chan)
            chan.pend_event(PEND_EVENT_TIMEOUT)
            return chan
        except:
            print "Could not connect"
            return None
    
    def _create_monitor(self, chan, name):
        def _block_updated_callback(epics_args, user_args):
            # Update the current value...
            self.curr_lock.acquire()
            try:
                self.curr_values[user_args[0]] = (epics_args['pv_value'], epics_args['type'])
            except:
                # Don't care, it is all about releasing the lock
                print "Could not update value"
                pass
            finally:
                # Must release lock
                self.curr_lock.release()
                pass
                
        ftype = chan.field_type()

        if ca.dbr_type_is_ENUM(ftype) or ca.dbr_type_is_STRING(ftype):
            req_type = ca.DBR_STRING
        else:
            req_type = ca.dbf_type_to_DBR_STS(ftype)
        chan.add_masked_array_event(
            req_type,
            None,
            ca.DBE_VALUE | ca.DBE_ALARM,
            _block_updated_callback,
            name)
        chan.pend_event(PEND_EVENT_TIMEOUT)
            
    def get_curr_values(self):
        self.curr_lock.acquire()
        try:
            ans = copy.deepcopy(self.curr_values)
        except:
            ans = None
        finally:
            # Must release lock
            self.curr_lock.release()        
        return ans
    
    def clear_curr_values(self):
        self.curr_lock.acquire()
        try:
            self.curr_values = dict()
        except:
            # Don't care, it is all about releasing the lock
            # Should not throw anyway
            pass
        finally:
            # Must release lock
            self.curr_lock.release()
            
    @staticmethod        
    def _monitor_changes(blocks_mon):
        count = 0
        local_names = blocks_mon.block_names
        blocks_mon.connect()
        while True:
            if blocks_mon.stop_thread:
                break
            elif local_names != blocks_mon.block_names:
                print "Refreshing blocks"
                blocks_mon.disconnect_block_monitors()
                blocks_mon.clear_curr_values()
                local_names = blocks_mon.block_names
                for b in blocks_mon.block_names:
                    blocks_mon.initialise_block(b)
            else:
                pass
            
            time.sleep(1)
    
    def start_thread(self):
        t = threading.Thread(target=self._monitor_changes, args=(self,))
        t.setDaemon(True)
        t.start()

        
if __name__ == '__main__':   
    prefix = os.environ["MYPVPREFIX"]
    print "Prefix is %s" % prefix
    
    SERVER = SimpleServer()
    SERVER.createPV(prefix, PVDB)
    DRIVER = BlocksMonitor(prefix)
    DRIVER.start_thread()

    # Process CA transactions
    while True:
        SERVER.process(0.1)
