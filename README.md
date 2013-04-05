Riverbed FlyScript Dashboard
============================

This Django project provides a web-based reporting capability utilizing the
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

The config directory defines a set of 4 reports based on two devices
named "profiler" and "shark1" defined in config/devices.py. 

To get started, edit the file `config/devices.py` and fill appropriate
values for the PROFILER device and the SHARK device.  At a minimum,
set the `host`, `username`, and `password` fields for each device.  For
the SHARK, a live view named 'flyscript-portal' is created on the
first available capture interface.

(If you only have a SHARK device, you can ignore the PROFILER
settings, it just means you won't be able to render any of the sample
PROFILER widgets.  Similarly if you just have a PROFILER, ignore the SHARK
settings.)

Customize the `config/locations.py` file to setup the IP address for 
addresses spaces in your network (those addresses that are in the private
non-routable IP space such as 10/8 or 192.168/16).  This should typically
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

Mapping locations for public IP address
---------------------------------------

The maps widget can identify public IP address using the GeoLite
database.  To enable this integration, download the GeoLite City database from
[MaxMind GeoLite Free Downloadable Databases](http://dev.maxmind.com/geoip/geolite#Downloads-5).

Install the unpacked database at the file location: /tmp/GeoLiteCity.dat

Running Reports
===============

Currently, each report has the same criteria:

- End Time - the end time/date of the reporting interval that will be used 

- Duration - the duration the reporting interval.  If left at 'Default', each
  widget in the report will use the duration configured for that widget's associated
  data table, which may be different for each table.  

- Filter Expression - an arbitrary filter expression to be passed to the
  data source that will execute the query for a table.  The syntax of the
  expression is dependent on the datasource. 

Note that since there may be a mix of different data sources in the
same report, the filter expression generally will not work in such
mixed reports because the filter expression syntax differs for each data
source.  This will will be addressed in a future release.

Defining Tables
===============

A data table is the root of data for a widget.  It defines the data source (one
of the modules in the apps/datasource/modules directory) and general table
attributes such as the default duration.  

Columns are associated with the table and define the keys and values of interest.
Each data table may have any number of columns.  

A column has the following common attributes:

- `name` - a simple name for referring to this column in the widget
- `label` - string label to used for display
- `iskey` - boolean indicating if this is a key column
- `datatype` - null, or one of 'metric', 'bytes', or 'time'
  - use 'metric' to automatically format the value with with metric unites
  - use 'bytes' to format as metric, but with Bytes attached
  - use 'time' for time based columns
- `units` - optional units for display purposes
- `module` - defines the module to use to query for data

In addition, each column supports an `options` attribute with defines additional
configuration options relevant to the the data source that will be performing
the query for this column.

A new data source may be defined by adding a new module to the apps/datasource/modules
directory.  See the existing modules as an example.  

Defining Widgets
================

Widgets are the UI representations of a data table.  Multiple widgets may be 
associated with the same table, for example to show both a bar chart and a
pie chart of the same data.

Each widget simply binds a table to a particular widget type.  The possible
widget types are defined by the modules in apps/report/modules.  

Widgets have the following attributes:

- `title` - the display title
- `width` - the column width for the widget, each page is 12 columns wide, defaults
  to 6 for half width
- `height` - the height in pixels, defaults to 300
- `module` - defines the module to use to render this widget
- `uiwidget` - defines the specific widget within the module

Widget specific options are specified in the `options` attribute.

A new widget may be defined by adding appropriate code to an existing
module or create new module in the apps/datasource/modules
directory.  See the existing modules and widgets as an example.  
Note that each module and uiwidget has associated JavaScript code
in the apps/report/static/js directory that handles turning the
data and options into rendered widget.

License
=======

Copyright (c) 2013 Riverbed Technology, Inc.

FlyScript Portal is licensed under the terms and conditions of the MIT
License set forth at
[LICENSE](https://github.com/riverbed/flyscript-portal/blob/master/LICENSE)
("License").  FlyScript Portal is distributed "AS IS" as set forth in
the License.  FlyScript Portal also includes certain third party code.
All such third party code is also distributed "AS IS" and is licensed
by the respective copyright holders under the applicable terms and
conditions (including, without limitation, warranty and liability
disclaimers) identified at
[LICENSE](https://github.com/riverbed/flyscript-portal/blob/master/LICENSE).
