import subprocess
import threading
import os
import time


class AlarmConfigLoader(object):

    # Instance of this singleton
    instance = None
    # The subprocess that the alarm server reloads itself in
    process = None

    @staticmethod
    def get_instance():

        if AlarmConfigLoader.instance is None:
            AlarmConfigLoader.instance = AlarmConfigLoader()

        return AlarmConfigLoader.instance

    def _load(self):
        """
        Simple wrapper around a batch script which reloads the configuration in the alarm server.
        """

        # Terminate the last batch job if it is still running
        # (prevents two instances from running concurrently which might cause problems).
        if self.process is not None:
            self.process.kill()

        print "Alarm server will update in 20 seconds\n"
        time.sleep(20)
        print "Alarm server updating...\n"

        filepath = os.path.join('C:\\', 'Instrument', 'Apps', 'EPICS', 'CSS', 'master', 'AlarmServer', 'run_alarm_server.bat')

        try:
            with open(filepath, 'r') and open(os.devnull) as devnull:
                self.process = subprocess.Popen(filepath, stderr=devnull)
                self.process.communicate(input=None)
        except Exception as e:
            print "Error while reloading alarm server."
            print e

        print "Alarm server updated\n"

    def load_in_new_thread(self):
        thread = threading.Thread(target=self._load)
        thread.start()

if __name__ == "__main__":
    AlarmConfigLoader.get_instance().load_in_new_thread()
    print "finished\n"
