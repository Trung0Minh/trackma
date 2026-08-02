# -*- coding: utf-8 -*-
#
# This hook generates a system notification for Linux when using MAL
#
# Written by matoro, last updated 2016/09/01
# https://github.com/matoro/
# https://myanimelist.net/profile/Matoro_Mahri
#
# To use, copy this file to ~/.trackma/hooks/

import subprocess

from trackma import utils


def episode_changed(engine, show):
    subprocess.run([
        'notify-send',
        '--icon={}'.format(utils.DATADIR + '/mal.jpg'),
        '--app-name=trackma',
        'Updated {}'.format(show['title']),
        'Progress: {}/{}'.format(show['my_progress'], show['total']),
    ], check=False)
