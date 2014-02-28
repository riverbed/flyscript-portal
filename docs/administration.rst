===============================================================================
FlyScript Portal Administration
===============================================================================

Starting and Stopping the Web Server
====================================

Starting and Stopping the Server in Development Mode (Django)
-------------------------------------------------------------

The Django web server is started up using the manage.py script:

    ``python manage.py runserver``

This starts up a development server running on port 8000 by default.  To stop
the server, press ``Control+C``.

Starting and Stopping the Server in Apache
------------------------------------------

On Red Hat Enterprise Linux and CentOS, use the following commands to start and
stop the FlyScript Portal:

    | ``sudo apachectl start``
    | ``sudo apachectl graceful-stop``

On Ubuntu Linux, use the following commands to start and stop the FlyScript 
Portal:

    | ``sudo apache2ctl start``
    | ``sudo apache2ctl graceful-stop``


Re-Initializing the Database
============================

The `clean` script at the root of the project will perform the following:

    - Initialize the database, if it doesn't exist
    - Clean out any temporary files (log files, cache files, etc.)
    - Reload configurations from the config directory
    - Setup a default admin user with the login/password combo of 'admin'/'admin'
      (if the user already exists, the password will be reset to 'admin')

Run this script to reset everything.  This is useful if you experience oddities
when trying to access pages.  Given that all configuration is stored in config
files, this operation is safe to run at just about any time.

Note that the `clean` script is a bash shell script and will work on unix-like
systems.  If you are running this on Windows, you'll need to manually execute
each command or run this from the Git-Bash or Cygwin shell.

On unix-like systems:

    ``./clean``

To force the database to its original state, and really reset everything to ground-zero,
pass the ``--reset`` command to the script as follows:

    ``./clean --reset``


Changing the Administrative Password
====================================

After logging into the FlyScript Portal web page, there will be an option under the
upper-right `Configure` button called `Preferences`.  From there, follow the link
titled `Change User Password` and a typical password change page will be shown.

Enabling Google Maps
====================

Google Maps/Google Earth API

Use of the Google Maps/Google Earth API may require login credentials from
Google such as an API Key or Client ID.  Please see Google's website at
https://developers.google.com/maps/documentation/javascript/tutorial and
https://developers.google.com/maps/documentation/business/clientside/#MapsJS
for more information.  Please also see the LICENSE file available at
https://github.com/riverbed/flyscript-portal/blob/master/LICENSE for
information regarding licensing.


Enabling OpenStreetMap
======================

Please see the LICENSE file available at
https://github.com/riverbed/flyscript-portal/blob/master/LICENSE for
information regarding licensing of OpenStreetMap and MapQuest-OSM tiles.


Mapping IP Addresses to Locations
=================================

Public IP Addresses
-------------------

The maps widget can identify public IP address using the GeoLite
database.  To enable this integration, download the GeoLite City database from
[MaxMind GeoLite Free Downloadable Databases](http://dev.maxmind.com/geoip/geolite#Downloads-5).

Install the unpacked database at the file location: ``/tmp/GeoLiteCity.dat``

Private IP Addresses
--------------------

You can customize the following file to configure location information (such as
City, latitude, longitude, etc) for private IP addresses in your network, such 
as 10/8 or 192.168/16):

    | ``$FLYSCRIPT_ROOT/flyscript-portal/config/location.py``

This should typically match your ByLocation host group configuration on Cascade 
Profiler.


