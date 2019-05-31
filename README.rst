==================
ckanext-satreasury
==================

This is the South Africa National Treasury CKAN theme extension. It customises CKAN for Treasury's requirements.

Features:

- de-emphasise Organisations and Groups
- add a financial year tag

To allow users to upload datasets before becoming members of organizations, this plugin requires datasets without an owner organization to be private.

Also set the following config options to allow uploads::

    ckan.auth.create_unowned_dataset = true
    ckan.auth.create_dataset_if_not_in_organization = true

Changes to datasets owned by other organisations than ``national-treasury`` trigger Travis-CI builds of https://travis-ci.org/OpenUpSA/static-budget-portal.

To give the installation access, set ``CKAN_SATREASURY_TRAVIS_TOKEN`` or ``satreasury.travis_token``.

To disable this, set ``CKAN_SATREASURY_BUILD_TRIGGER_ENABLED`` or ``satreasury.build_trigger_enabled`` to "false".

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

To run the tests, run::

     nosetests
