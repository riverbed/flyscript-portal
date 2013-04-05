Riverbed FlyScript Dashboard
============================

This Django project provides a web-based reporting capability utilitizing the
FlyScript python package.

Installation
------------

Along with a working python installation, the following packages will need to
be installed:

- Django==1.4.5
- django-model-utils==1.2.0
- djangorestframework==2.2.5
- flyscript==latest
- jsonfield==0.9.13
- numpy==1.7.0
- pandas==0.10.1
- pygeoip==0.2.6
- python-dateutil==2.1
- pytz==2013b
- six==1.3.0
- wsgiref==0.1.2

After cloning this repository to a local directory, these dependencies can be
installed/checked by using the included requirements.txt file.  For example:

    $ cd /tmp
    $ git clone git@github.com:riverbed/flyscript-portal.git
    $ cd flyscript-portal
    $ pip install -r requirements.txt

Configuration
-------------

All device and report configuration configuration is done by a set of configuration
files in the config directory:

- config/devices.py 
    - the set of devices that will be queried for data
- config/locations.py
    - location defintions by CIDR for custom geo-ip mapping
- config/reports/*.py
    - reports, data tables and widgets

The config directoy defines a set of 4 reports based on two devices
named "profiler" and "shark1" defined in config/devices.py. 

To get started, edit the file `config/devices.py` and fill appropriate
values for the PROFILER device and the SHARK device.  At a minimum,
set the `host`, `username`, and `password` fields for each device.

(If you only have a SHARK device, you can leave ignore the PROFILER
settings, it just means you won't be able to render any of the sample
PROFILER widgets.  Similalry if you just have a PROFILER, ignore the SHARK
settings.)

Customize the `config/locations.py` file to setup the IP address for 
addresses spaces in your network (those addresses that are in the private
non-routeable IP space such as 10/8 or 192.168/16).  This should typically
match your ByLocation host group configuration on Cascade Profiler.

Initializing the database
-------------------------

The `clean` script at the root of the project will perform the following:
- reset the database
- clean out any temporary files (log files, cache files, etc.)
- create a new database and import configuration from the config directory

Run this script to reset everything back to ground zero.  This is
useful if you experience oddities when trying to access pages.  Given
that all configuration is stored in config files, this operation is safe
to run at just about any time.

Note that the `clean` script is a bash shell script and will work on unix-like
systems.  If you are running this on Windows, you'll need to manually execute
each command.

On unix-like systems:

    $ ./clean

Starting the server
-------------------

The Django web server is started up using the manage.py script:

    $ python manage.py runserver

This starts up a development server running on port 8000 by default.  
Now, navigate to [http://localhost:8000](http://localhost:8000) and you should
see a page with a criteria box open.  Just click "Run" and you should see some 
plots.

*Note:*
This project utilizes file storage caching of the data results, and these files are
stored in the `datacache` directory.  Eventually these files will be automatically
cleaned, but in the interim, there are no ill effects if they are manually deleted
periodically to reclaim storage space.
