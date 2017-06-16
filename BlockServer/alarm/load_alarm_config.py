import threading
import time


class AlarmConfigLoader(object):
    """
    Alarm configuration loader class will create a new configuration and load it into the alarm server. While the
    instance exists it will count down when it get to 0 it will no longer be the current instance and will then
    restart the alarm server with a new config

    Currently it does this by restarting the alarm server after a delay. It is a singleton there is only one
    at any one time.
    """

    # Instance of this singleton
    _instance = None

    # Number of seconds to delay the reload by so that IOC has started and published its alarmed PVs
    DELAY = 20

    # lock for accessing the delay and instance variables.
    lock = threading.Lock()

    thread = None

    def __init__(self, ioc_control):
        """
        Constructor
        :param ioc_control: ioc control class to enable this class to restart the Alarm IOC
        """

        self._delay_left = AlarmConfigLoader.DELAY
        self._ioc_control = ioc_control

    def run(self):
        """
        Delay until the time has run out then recreate the alarm config and reload it. This method should be called in
        a thread because it is blocking
        """
        while self._is_still_delayed():
            time.sleep(1)

        self._ioc_control.restart_ioc("ALARM", force=True)

    def do_reset_alarm(self):
        """
        Thread safe way to restart the counter
        :return:
        """
        with AlarmConfigLoader.lock:
            self._delay_left = AlarmConfigLoader.DELAY
            print "Alarm server will update in {0} seconds from now\n".format(self._delay_left)

    def _is_still_delayed(self):
        """
        Reduce the delay by 1 and check if it has run out. If it is no longer delayed remove this instance
        :return: True if still delayed; False otherwise
        """
        with AlarmConfigLoader.lock:
            self._delay_left -= 1

            if self._delay_left > 0:
                return True

            AlarmConfigLoader._instance = None
            return False

    @staticmethod
    def restart_alarm_server(ioc_control):
        instance = AlarmConfigLoader._get_instance(ioc_control)
        instance.do_reset_alarm()

    @staticmethod
    def _get_instance(ioc_control):
        """
        Get the instance of the load alarm config

        :param ioc_control (BlockServer.core.ioc_controlIocControl):
        :return (AlarmConfigLoader): instance of the alarm config loader
        """
        with AlarmConfigLoader.lock:
            if AlarmConfigLoader._instance is None:

                AlarmConfigLoader._instance = AlarmConfigLoader(ioc_control)

                AlarmConfigLoader.thread = threading.Thread(target=AlarmConfigLoader._instance.run)
                AlarmConfigLoader.thread.start()

            return AlarmConfigLoader._instance
