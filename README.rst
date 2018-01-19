==================
ckanext-satreasury
==================

This is the South Africa National Treasury CKAN theme extension. It customises CKAN for Treasury's requirements.

Features:

- de-emphasise Organisations and Groups
- add a financial year tag

------------
Installation
------------

To install ckanext-satreasury:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-satreasury Python package into your virtual environment::

     pip install ckanext-satreasury

3. Add ``satreasury-dataset`` and ``satreasury-organization`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload

------------------------
Development Installation
------------------------

To install ckanext-satreasury for development, activate your CKAN virtualenv and
do::

    git clone https://github.com//ckanext-satreasury.git
    cd ckanext-satreasury
    python setup.py develop
    pip install -r dev-requirements.txt
