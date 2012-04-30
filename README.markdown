License
------------------------------------------------------------------------------
Copyright 2012 Travis Patterson
Based on SSHMenu, Copyright 2002-2009 Grant McLean <grant@mclean.net.nz>
This attribution is not an endorsement for pySSHMenu by the author of or 
contributors to SSHMenu

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


What is it?
------------------------------------------------------------------------------
SSHMenu is a simple GUI app that provides a menu for initiating SSH
connections.  Select a host from the menu and up pops a new terminal window
containing an SSH session to the selected host.

pySSHMenu is a port of SSHMenu to Python and Gtk 3 that runs as an
AppIndicator rather than as an applet. pySSHMenu reads and writes your old
SSHMenu configuration files to make transitioning easy.


Differences Between pySSHMenu and SSHMenu
------------------------------------------------------------------------------
The biggest difference between pySSHMenu and SSHMenu is that SSHMenu can be
run as a stand-alone application that has no Gnome dependencies whereas
pySSHMenu is designed to be run solely as an AppIndicator in Gnome.
There are some slight feature differences as well:


- pySSHMenu does not have the option to "show text entry next to the menu 
  button." This is something that doesn't make sense in the context of an
  AppIndicator
    

- pySSHMenu does not have the ability to "hide button border." Again this
  doesn't make sense in the context of an AppIndicator
      

- pySSHMenu does not support tear-off menus. These have been deprecated with
  no replacement so they were left out
 

Requirements
------------------------------------------------------------------------------
pySSHMenu requires that PyYaml be installed because the pySSHMenu
configuration file format is yaml.

pySSHMenu also requires Gtk 3.


Installation
------------------------------------------------------------------------------
1. Install PyYaml if it's not already

2. Download SSHMenu.py

3. Copy SSHMenu.py to `/usr/local/bin/SSHMenu`

4. `chmod 755`

5. Launch SSHMenu

6. _Optional:_ add it to the Gnome startup so it starts on login
