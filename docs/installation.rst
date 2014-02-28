===============================================================================
 FlyScript Portal Installation Guide for Red Hat Enterprise Linux and CentOS
===============================================================================


Overview
========

This document describes the installation and configuration procedures for 
installing the FlyScript Portal and custom reports on Red Hat Enterprise Linux 
6.2 or CentOS 6.2.

System Requirements
===================

Hardware Requirements
---------------------

The server should have at least 1GB of RAM and 20GB of available hard disk 
space.  If the database (eg, MySQL) will be installed on the same machine, then
the machine should have at least 2GB of RAM and 40GB of available hard disk 
space.  Typically, CPU speed is not a limiting factor; a reasonably-modern 
single or dual core CPU should be sufficient.

Required System Packages
------------------------

These installation instructions are for Python 2.6.  Note that Python 2.6 is 
the default Python installation for RHEL 6.2 and CentOS 6.2.

The following packages are required in order to install the FlyScript Portal.  
These packages should be installed by a system administrator or a user with 
root privileges:

======================================  =======================================
Package                                 Installation Command
======================================  =======================================
Python 2.6                              *typically installed by default*
gcc-c++                                 sudo yum install gcc-c++
httpd                                   sudo yum install httpd
                                        *(typically installed by default)*
mod_ssl                                 sudo yum install mod_ssl
mod_wsgi                                sudo yum install mod_wsgi
python-devel                            sudo yum install python-devel
libselinux-python                       sudo yum install libselinux-python
MySQL Server                            sudo yum install mysql-server
                                        *(optional)*
MySQL Development Package               sudo yum install mysql-devel
                                        *(optional, if MySQL Server is not 
                                        installed)*
libxslt-devel                           sudo yum install libxslt-devel
python-setuptools                       sudo python setup.py install 
                                        *(setuptools-2.1.tar.gz is provided, if
                                        required)*
pip                                     sudo easy_install pip
virtualenv                              sudo pip install virtualenv
ipython                                 sudo pip install ipython
======================================  =======================================

Additionally, these instructions will refer to the "install_resources.tar.gz" 
file, which contains the FlyScript and FlyScript Portal packages, as well as 
other required software.

Flyscript Portal User Account
-----------------------------

You may wish to create a separate user account for the FlyScript portal during
installation (for example, "portal_admin").  This account will be the owner
of files and directories created during installation.


Directory Structure
===================
The deployed directory structure will look like the following, where 
$FLYSCRIPT_ROOT is determined by sysadmins or other convention.  Typically 
this will be either:

    | /flyscript
    | /opt/flyscript

The FlyScript Portal directory structure is as follows:

    | $FLYSCRIPT_ROOT/flyscript-portal
    | $FLYSCRIPT_ROOT/install_resources
    | $FLYSCRIPT_ROOT/virtualenv
    | $FLYSCRIPT_ROOT/wsgi
    | $FLYSCRIPT_ROOT/<custom_report_directory>
    | /etc/httpd/conf.d/flyscript_portal_site.conf

During installation, you will also need a working directory (for example, 
~/flyscript_files).  This directory will be referred to as $FLYSCRIPT_WORK_DIR.

Installing the FlyScript Portal
===============================

1. Ensure that the server has been provisioned with all of the Required System
   Packages.
2. Ensure that the account being used for installation has 'umask 022' 
   configured.  To ensure that this property is configured correctly, run 
   ``umask 022`` at the command prompt. 
3. Create the ``$FLYSCRIPT_ROOT`` directory on the server.
      * Make sure that the directory is owned by the correct user.  Typically, 
        you do not want it to be owned by the "root" user, although that may be 
        the default owner if you created it in "/".  To change the directory’s 
        owner, use the command ``sudo  chown  <username>:<group>  <directory>``.  
        For example, ``sudo chown portal_admin:portal_admin /flyscript``.
4. Copy the ``install_resources.tar.gz`` file to ``$FLYSCRIPT_WORK_DIR``.
5. Unzip the ``install_resources.tar.gz`` file using the command
       ``tar –xf install_resources.tar.gz``.
6. Create the following directory:
   ``$FLYSCRIPT_ROOT/install_resources/packages``
7. Copy the ``packages`` directory to the newly-created ``install_resources`` directory:
       ``cp $FLYSCRIPT_WORK_DIR/install_resources/flyscript-portal-packages/packages/*  $FLYSCRIPT_ROOT/install_resources/packages``
8. In the ``$FLYSCRIPT_ROOT`` directory, create a new virtual Python environment using the command: 
       ``virtualenv  virtualenv``
9. Activate the new virtual Python environment using the command:
       ``source  virtualenv/bin/activate``
10. Change directory to ``$FLYSCRIPT_ROOT/install_resources``.
11. Install the following Python packages using the commands listed:
        a. ``pip install --no-index --find-links=file://$FLYSCRIPT_ROOT/install_resources/packages numpy``
        b. ``pip install --no-index --find-links=file://$FLYSCRIPT_ROOT/install_resources/packages pandas``
        c. ``pip install --no-index --find-links=file://$FLYSCRIPT_ROOT/install_resources/packages requests``
12. Install FlyScript using the commands listed below:
        a. Change directory to ``$FLYSCRIPT_ROOT/install_resources/packages/``.
        b. Unzip the FlyScript Python package.  The FlyScript Python package is
           typically distributed as a .zip or .tar.gz file using the following
           naming convention: ``flyscript-<version>.(zip|tar.gz)``.  For 
           example, FlyScript version 0.6.0 might be available in a file
           called "flyscript-0.6.0_3_g83cd.zip".  To unzip this file, you
           would use the following command:

               ``unzip flyscript-0.6.0_3_g83cd.zip``

        c. Change directory into ``flyscript``.
        d. Run ``python setup.py install``.
13. Change directory to ``$FLYSCRIPT_WORK_DIR/install_resources/flyscript-portal-packages``.
14. Install the following Python packages using the commands listed below:
        a. ``pip install --no-index --find-links=file://$FLYSCRIPT_ROOT/install_resources/packages -r flyscript-portal/requirements.txt``
        b. ``pip install --no-index --find-links=file://$FLYSCRIPT_ROOT/install_resources/packages sharepoint``
        c. ``pip install --no-index --find-links=file://$FLYSCRIPT_ROOT/install_resources/packages importlib``
        d. ``pip install --no-index --find-links=file://$FLYSCRIPT_ROOT/install_resources/packages pysubnettree``
15. Copy ``$FLYSCRIPT_WORK_DIR/flyscript-portal-packages/flyscript-portal`` to ``$FLYSCRIPT_ROOT``:
        ``cp -r $FLYSCRIPT_WORK_DIR/install_resources/flyscript-portal-packages/flyscript-portal $FLYSCRIPT_ROOT``
16. Change directory to ``$FLYSCRIPT_ROOT/flyscript-portal`` and run the following command:
        ``./bootstrap.py install``
17. Run the following commands to initialize the portal:
        a. ``./clean  --reset  --force  --trace``
        b. ``python  manage.py  collectstatic``
        c. ``python  manage.py  runserver  0.0.0.0:8000``
18. Navigate to ``http://<ip_address>:8000`` to confirm that the portal is loaded.
    See the section "Logging Into the FlyScript Portal for the First Time"
19. Press ``Control+C`` to shut down the server.

Logging Into the FlyScript Portal for the First Time
====================================================

The first time you connect to the FlyScript Portal, you will be prompted to 
specify your username and password.  The default username and password for the
FlyScript Portal administrator is:

    | Username: **admin**
    | Password: **admin**

Once you log in, you will be prompted to specify the IP addresses, ports and
credentials for the Cascade Shark and Cascade Profiler devices in your network.

After specifying the required information for your Cascade Shark and Profiler
devices, you will be brought to the default "landing page".  From this page,
you can select to run one of the default reports:

==================  ===========================================================
Default Report      Description
==================  ===========================================================
Overall             Shows overall bandwidth and application throughput across
                    all Cascade Shark and Profiler devices.
Profiler            Shows bandwidth and application throughput for each Cascade
                    Profiler in your network.
Shark               Shows bandwidth and packet statistics from each Cascade 
                    Shark in your network.
Response Time Map   Shows application response time as measured by Cascade 
                    Profiler.
==================  ===========================================================

Note that you can also install custom reports, as described in the following
section.

Installing Custom Reports
=========================

Custom reports can be added to the FlyScript Portal using the following procedure:

1. Copy the tar.gz of the custom report to ``$FLYSCRIPT_WORK_DIR/install_resources``.
2. Unzip the custom report using the command:
       ``tar  –xf  <custom_report_name>.tar.gz``
3. Move the newly-unzipped directory to $FLYSCRIPT_ROOT using the following command:
       ``mv  <custom_report_name>  $FLYSCRIPT_ROOT``
4. Change directory to ``$FLYSCRIPT_ROOT/<custom_report_name>``.
5. Run the following command:
        ``python  setup.py  install``
6. Change directory to ``$FLYSCRIPT_ROOT/flyscript-portal`` and run the following command to add the new report:
        ``python manage.py reload``
7. Start the server using the following command:
         ``python  manage.py  runserver  0.0.0.0:8000``
8. Navigate to ``http://<ip_address>:8000`` to confirm that the custom report 
   has been added to the list of available reports.
9. Press ``Control+C`` to shut down the server


Database Installation and Configuration
=========================================
By default, the FlyScript Portal uses SQLite as its back-end database.  While
SQLite should be sufficient for light workloads during development and testing,
this should be changed to a more scalable database platform for production use.

The FlyScript Portal supports the following database platforms for production
use:

    * MySQL
    * PostgreSQL
    * Oracle

If you do not already have access to a database server, the instructions below
will explain how to install MySQL.  If you would like to use another database
which has already been installed (either on the same machine as the FlyScript
Portal, or a different machine), you can skip the section titled "Installing
MySQL" and proceed to "Configuring MySQL".


Installing MySQL
----------------

1. If MySQL Server has not already been installed (as described in "Required
   System Packages"), it can be installed now, using the following command:
   
       ``sudo yum install mysql-server``

   Note that you will need Internet access to run this command.

2. If the MySQL Development Package has not already been installed (as 
   desribed in "Required System Packages"), it can be installed now, using the
   following command:

       ``sudo yum install mysql-devel``

   Note that you will need Internet access to run this command.

3. Change directory to ``$FLYSCRIPT_ROOT/install_resources/packages``.
   
4. Install MySQL Python using the following command:
       ``pip install  MySQL-python-1.2.5.zip``
5. To enable MySQL to automatically start when the machine is rebooted, use the following command:
        ``sudo chkconfig  --level  235  mysqld  on``
6. Start MySQL if it isn’t running already:
       ``sudo  service  mysqld  start``
7. Configure your MySQL installation using the following command:
       ``sudo /usr/bin/mysql_secure_installation``
8. When prompted for a password for the “root” user, simply press ``Enter``.
   The default password for the root user in MySQL is blank.  You will be 
   prompted to change this.
9. After changing the root password, you will be prompted with a series of 
   questions (eg, "Remove anonymous users?", "Disallow root login remotely?", 
   etc).  Select the default response ("Yes") for all of these.

Configuring MySQL
-----------------

Once a database server (such as MySQL) has been installed, you will need to 
create a database and database user for the FlyScript Portal.  The
instructions below explain how to configure a database and a user for MySQL;
for other database server platforms, consult your database administrator.

1. Once you have installed MySQL, log in as root:
        ``mysql –u root –p``
2. Create the database using the following command:
       ``CREATE DATABASE flyscript_portal;``
3. Create a user (and corresponding password) for this database using the following command:

        ``CREATE USER 'portal_ user'@'localhost' IDENTIFIED BY '<password>';``
    
    NOTE: Specify a password for the database user  in the <password> field above.
4. Give the newly-created user permission to access/modify the "flyscript_portal" database:
        ``GRANT ALL ON flyscript_portal.*  to  'portal_user'@'localhost';``
5. Exit MySql by typing ``\q`` and pressing ``Enter``.

Configuring the FlyScript Portal to Use MySQL
---------------------------------------------

1. Shut down the FlyScript Portal if it is currently running.
2. Change directory to ``$FLYSCRIPT_ROOT/flyscript-portal/project/settings``.
3. If you are running the FlyScript portal in Apache, then open the file
   ``production.py`` for editing.  Otherwise, open the file ``development.py``
   for editing.
4. Add the following: ::

       DATABASES = {
           'default': {
               'ENGINE': 'django.db.backends.mysql',
               'NAME': 'flyscript_portal',
               'USER': 'portal_user',
               'PASSWORD': '<portal_user_password>',
               'HOST': '',
               'PORT': '',
           }
       }

   Note that if you are connecting to a MySQL server installed on a different
   machine, you will need to provide the machine's name or IP address as a 
   value for the ``HOST`` parameter, and the MySQL port number as a value for
   the ``PORT`` parameter.  The default MySQL port is ``3306``.

   Note that if you are using a database server which is administered by another
   user, the database name and/or the username may be different from the default
   values shown above.  Consult your database administrator for the correct
   values.
   
   Note that the value of ``'ENGINE'`` will change depending on which database
   server you are using.  The following options are available: 
   
       | MySQL:       ``django.db.backends.mysql``
       | PostgreSQL:  ``django.db.backends.postgresql_psycopg2``
       | Oracle:      ``django.db.backends.oracle``
       | SQLite:      ``django.db.backends.sqlite3`` *(not recommended for production use)*

5. Check the list of import statements at the top of the file (ie, 
   ``development.py`` or ``production.py``).  Make sure that the following line
   is included.  If not, add it: ``from settings import *``
6. Change directory to ``$FLYSCRIPT_ROOT/flyscript-portal/initial_data``.
7. Delete the file ``initial_preferences.json``, if it exists.
8. Change directory to ``$FLYSCRIPT_ROOT/flyscript-portal``.
9. Reset the FlyScript Portal so that it uses the new database.  Note that you  must run this command from a prompt where virtualenv has be activated:
        ``./clean  --reset  --force  --trace``
10. Start the FlyScript Portal again:
        ``python  manage.py  runserver  0.0.0.0:8000``
11. Navigate to ``http://127.0.0.1:8000`` in a web browser to verify that the
    FlyScript Portal is running correctly.
12. You can shut down the FlyScript Portal using ``Control+C`` when it is no
    longer needed.


Configuring the FlyScript Portal to Run Under Apache
====================================================

To configure the FlyScript Portal to run under Apache, use the following 
procedure:

1. Make the directory ``$FLYSCRIPT_ROOT/wsgi``.
2. Run the following commands:
       a. ``cp  $FLYSCRIPT_ROOT /flyscript-portal/project/portal.wsgi   wsgi/``
       b. ``sudo cp  $FLYSCRIPT_ROOT /flyscript-portal/project/apache2.conf /etc/httpd/conf.d/flyscript_portal_site.conf``
3. Edit ``/etc/httpd/conf.d/flyscript_portal_site.conf`` and add a line that says:
       ``WSGISocketPrefix /var/run/wsgi``.
4. Set the correct paths in the ``<VirtualHost>`` section of the file.  For 
   instance, if ``$FLYSCRIPT_ROOT`` is ``/flyscript``, then you would define the 
   following: ::
   
       Alias   /static   /flyscript/flyscript-portal/static
       WSGIScriptAlias  /  /flyscript/wsgi/portal.wsgi
       WSGIDaemonProcess   flyscript_portal processes=1   python-path=/flyscript/flyscript-portal:/flyscript/virtualenv/lib/python2.6/site-packages
       WSGIProcessGroup  flyscript_portal

5. Edit ``$FLYSCRIPT_ROOT/wsgi/portal.wsgi`` and make the following changes:
       a. Change ``VIRTUALENV_BIN`` to the appropriate path.  For instance, if ``$FLYSCRIPT_ROOT`` is ``/flyscript``, then this line should read:
              ``VIRTUALENV_BIN = '/flyscript/virtualenv/bin'``
       b. Change ``VIRTUALENV_SITE_PACKAGES`` to the appropriate path.  For instance, if ``$FLYSCRIPT_ROOT`` is ``/flyscript``, then this line should read:
              ``VIRTUALENV_SITE_PACKAGES = '/flyscript/virtualenv/lib/python2.6/site-packages'``
       c. Set ``PORTAL_ROOT`` to the appropriate path.  For instance, if ``$FLYSCRIPT_ROOT`` is ``/flyscript``, then this line should read:
              ``PORTAL_ROOT = '/flyscript/flyscript-portal/project'``
6. Change ownership on the following directories to assign them to Apache:
       a. ``sudo  chown  –R  apache:apache  $FLYSCRIPT_ROOT/flyscript-portal``
       b. ``sudo  chown  –R  apache:apache  $FLYSCRIPT_ROOT/wsgi``
       c. ``sudo  chown  –R  apache:apache  /var/www``
7. Change ownership on the following files and assign them to Apache:
       a. ``sudo  chown  apache:apache  /tmp/*.pd``
8. If SELinux is enabled on your machine, you will either need to update your 
   SELinux policies to permit Apache to load the FlyScript Portal, or you can
   change SELinux to “permissive” mode.  To change SELinux to “permissive” 
   mode, use the following command:
   
       ``sudo  setenforce  permissive``

   Note that this setting will revert back to the default when the machine is rebooted.
9. Start Apache using the following command:
       ``sudo apachectl start``
10. Connect to the FlyScript Portal at ``http://127.0.0.1``.  Note that by 
    default, when running under Apache, the FlyScript Portal can be reached on 
    **port 80**, and not port 8000.
11. To stop and restart Apache, use the following commands:

        | ``sudo apachectl graceful-stop``
        | ``sudo apachectl start``













