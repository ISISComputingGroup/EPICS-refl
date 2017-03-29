import subprocess
import threading
import os
import time


class AlarmConfigLoader(object):

    instance = None
    loading = False

    @staticmethod
    def get_instance():
        if AlarmConfigLoader.instance is not None:
            return AlarmConfigLoader.instance
        else:
            AlarmConfigLoader.instance = AlarmConfigLoader()
            return AlarmConfigLoader.instance

    def _load(self):
        """
        Simple wrapper around a batch script which reloads the configuration in the alarm server.
        """
        AlarmConfigLoader.loading = True

        print "Alarm server sleeping"
        time.sleep(20)
        print "Alarm server finished sleeping"
        filepath = "C:\Instrument\Apps\EPICS\CSS\master\AlarmServer\load_alarm_config.bat"
        with open(os.devnull, 'w') as devnull:
            p = subprocess.Popen(filepath, shell=True, stdout=devnull, stderr=devnull)

        p.wait()
        AlarmConfigLoader.loading = False
        print "Alarm server updated"

    def load_in_new_thread(self):
        if not AlarmConfigLoader.loading:
            thread = threading.Thread(target=self._load)
            thread.start()

if __name__ == "__main__":
    AlarmConfigLoader.get_instance().load_in_new_thread()
    print "finished"
