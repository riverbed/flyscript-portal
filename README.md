Riverbed FlyScript Dashboard
============================

This Django project provides a web-based reporting capability utilitizing the
FlyScript python package.

Quick Start
-----------

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

Once the requirements are either downloaded or upgraded, you can get started
with a default portal setup by editing the first part of sample-setup.py to
point to a local Profiler and Shark appliance.  Then run the clean script which
will apply those changes, and run the django development server by issuing the
following commands:

    $ ./clean
    $ python manage.py runserver

Now, navigate to [http://localhost:8000](http://localhost:8000) and you should
see some plots: 
<p align="center">
<img src="https://splash.riverbed.com/servlet/JiveServlet/showImage/102-1751-1-2059/Screen+Shot+2013-04-01+at+12.32.15+AM.png?raw=true" alt="FlyScript Portal Example Page" />
</p>

*Note:*
This project utilizes file storage caching of the data results, and these files are
stored in the `datacache` directory.  Eventually these files will be automatically
cleaned, but in the interim, there are no ill effects if they are manually deleted
periodically to reclaim storage space.
