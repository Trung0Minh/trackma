# This file is part of Trackma.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import subprocess
import time

from trackma import utils
from trackma.tracker import tracker


class PollingTracker(tracker.TrackerBase):
    name = 'Tracker (polling)'

    def get_playing_file(self, watch_dirs, players):
        for path in watch_dirs:
            # TODO: We'll run lsof once for each directory for now.
            try:
                lsof = subprocess.Popen(
                    ['lsof', '-w', '-n', '-c', ''.join(['/', players, '/']), '-Fn', path], stdout=subprocess.PIPE)
            except OSError:
                self.msg.warn("Couldn't execute lsof. Disabling tracker.")
                self.disable()
                return None

            output = lsof.communicate()[0].decode('utf-8')

            for line in output.splitlines():
                if line[0] == 'n' and utils.is_media(line):
                    return os.path.basename(line[1:])

        return None

    def observe(self, config, watch_dirs):
        self.msg.info("pyinotify not available; using polling (slow).")
        last_files = set()
        # Initial scan to avoid detecting everything as new on startup
        for path in watch_dirs:
            for fullpath, filename in utils.regex_find_videos(path):
                last_files.add(fullpath)

        while self.active:
            # Check for new files in library
            current_files = set()
            for path in watch_dirs:
                for fullpath, filename in utils.regex_find_videos(path):
                    current_files.add(fullpath)
                    if fullpath not in last_files:
                        self.msg.debug(f"Polling detected new file: {fullpath}")
                        self._emit_signal('detected', path, filename)
            
            # Check for removed files
            for fullpath in last_files:
                if fullpath not in current_files:
                    path, filename = os.path.split(fullpath)
                    self.msg.debug(f"Polling detected removed file: {fullpath}")
                    self._emit_signal('removed', path, filename)
            
            last_files = current_files

            # This runs the tracker and update the playing show if necessary
            filename = self.get_playing_file(
                watch_dirs, config['tracker_process'])
            (state, show_tuple) = self._get_playing_show(filename)
            self.update_show_if_needed(state, show_tuple)

            # Wait for the interval before running check again
            time.sleep(config['tracker_interval'])
