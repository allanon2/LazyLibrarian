# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import operator
import platform
import re

USER_AGENT = 'LazyLibrarian' + ' (' + platform.system() + ' ' + platform.release() + ')'

mediaExtensions = ['epub', 'mobi', 'pdf']


### Notification Types
NOTIFY_SNATCH = 1
NOTIFY_DOWNLOAD = 2

notifyStrings = {}
notifyStrings[NOTIFY_SNATCH] = "Started Download"
notifyStrings[NOTIFY_DOWNLOAD] = "Download Finished"


