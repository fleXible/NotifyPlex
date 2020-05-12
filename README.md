# NotifyPlex

Post-processing script for [NZBGet](http://nzbget.net).

This script will inform a targeted Plex to refresh/update the library upon successful download and send a GUI Notification to Plex Home Theater.

## Installation

 - Download the newest version from [releases page](https://github.com/fleXible/NotifyPlex/releases)
 - Unpack and move `NotifyPlex.py` into your pp-scripts directory
 - Install python package `requests` with command `pip install requests`
  - With Python 3.x you might need to use `pip3 install requests`
 - Open settings tab in NZBGet web-interface
  - Fill in the _**PlexUser**_ and temporarily the _**PlexPassword**_ fields
  - Use the _**Generate Plex Auth-Token**_ button and put the resulting string into _**PlexAuthToken**_
  - Remove your password
 - Define your settings for NotifyPlex
  - If using [VideoSort](https://github.com/nzbget/VideoSort) or other Sort/Rename Scripts, run NotifyPlex after those scripts have sorted/renamed your files
 - Save changes and restart NZBGet

For further information and history, please read the original [forum thread](https://forum.nzbget.net/viewtopic.php?f=8&t=1393).

## Issues and suggestions

If you experience any issues or have suggestions for changes and enhancements, please use the
[GitHub issue tracker](https://github.com/fleXible/NotifyPlex/issues).

## Contributing

The Python code follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
Please check your code with [autopep8](https://github.com/hhatto/autopep8)
before submitting a PR.

The needed configuration is provided in the file `.pep8` and automatically recognized by autopep8.

Be sure to update **README**, **CHANGELOG** and **Script-Version** if necessary.

Credits
-------
This script was originally published by [mannibis](https://forum.nzbget.net/memberlist.php?mode=viewprofile&u=998)
in 2014 on the official [NZBGet Forum](https://forum.nzbget.net/viewtopic.php?f=8&t=1393).
