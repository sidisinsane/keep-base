Installation
============

Keep requires Python 3.12 or later.

From PyPI
---------

Once published, install Keep with::

   uv tool install keep

Verify the installation::

   keep --help

From source
-----------

To install the latest version directly from the repository::

   uv tool install git+https://github.com/your-username/keep

To upgrade::

   uv tool install --force git+https://github.com/your-username/keep

Requirements
------------

Keep has a single runtime dependency: `ruamel-yaml <https://pypi.org/project/ruamel-yaml/>`_,
which is installed automatically.
