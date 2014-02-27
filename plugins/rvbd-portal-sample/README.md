This directory contains sample code for developing a new plugin.  A plugin may
include any of:

   * Datasources
   * Devices
   * Reports

This sample contains example code for each of the above.

The directory structure is as follows:

  ./README.md -- this file
  ./setup.py -- package installation parameters
  ./rvbd_portal_sample -- package files
  ./rvbd_portal_sample/plugin.py -- plugin information
  ./rvbd_portal_sample/datasources
  ./rvbd_portal_sample/devices
  ./rvbd_portal_sample/reports

1. Pick the simple name for your plugin -- this one is 'sample'

2. Copy this entire directory, call the root directory
   rvbd-portal-<name>

3. Rename rvbd_portal_sample to rvbd_portal_<name>

4. Edit setup.py

   - Docstring for the plugin at the top
   - setup
      - required changes
      - name - match the directory name: rvbd-portal-myplugin
      - verson - pick a reasonable staring version, update as needed
      - entry_points - update to reflet your new plugin name

   - optional
      - author / author_email
      - description

5. Edit rvbd_portal_myplugin/plugin.py
   - title, description, version, author

6. Edit the code in datasources to define a one or more new
   sources of data.  Each datasource must provide a
   'TableQuery' class that implements the 'run()' method.

7. Edit the code in devices to define new device instances.
   A device instance is shared by multiple queries, so must
   be thread-safe.  Typically this is used by datasources,
   but may be used by other modules as well.

8. Edit the code in reports to define one or more sample
   reports showing how to leverage the datasources and
   devices.

Once you have made your code changes, you can install and test
as follows in development mode:

1. Install the code (do this from the virtualenv if you have one defined):

   $ cd ${PLUGIN_ROOT}
   $ python setup.py develop

2. Run the clean script to load any reports that your code defines:

   $ cd ${FLYSCRIPT_PORTAL_ROOT}
   $ ./clean

   You might want to use "./clean --traceback" if you have errors.

3. Start the development server:

   $ python manage.py runserver

4. Run your reports!

The logfile at ${FLYSCRIPT_PORTAL_ROOT}/log.txt is the place to look
for log messages and tracebacks
