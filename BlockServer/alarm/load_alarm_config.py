import subprocess
import threading
import os
import time


class AlarmConfigLoader(object):

    # Instance of this singleton
    instance = None
    # The subprocess that the alarm server reloads itself in
    process = None
    # Number of seconds to delay the reload by
    # (the blockserver must have finished loading the configuration before the alarm server can be restarted)
    delay = 20

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
        if AlarmConfigLoader.process is not None:
            AlarmConfigLoader.process.kill()

        print "Alarm server will update in " + str(self.delay) + " seconds\n"
        time.sleep(AlarmConfigLoader.delay)
        print "Alarm server updating...\n"

        filepath = os.path.join('C:\\', 'Instrument', 'Apps', 'EPICS', 'CSS', 'master', 'AlarmServer', 'run_alarm_server.bat')

        try:
            with open(filepath, 'r') and open(os.devnull) as devnull:
                AlarmConfigLoader.process = subprocess.Popen(filepath, stderr=devnull)
                # Use communicate rather than call because of potential deadlocks based on output volume
                AlarmConfigLoader.process.communicate(input=None)
        except Exception as e:
            print "Error while reloading alarm server."
            print e

        print "Alarm server updated\n"

    def load_in_new_thread(self):
        thread = threading.Thread(target=self._load)
        thread.start()

# Only used if you want to run this file on it's own
# e.g. for testing that the alarm server reload is working correctly.
if __name__ == "__main__":
    AlarmConfigLoader.get_instance().load_in_new_thread()
