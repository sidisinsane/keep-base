{{ fullname | escape | underline }}

.. automodule:: {{ fullname }}
   :show-inheritance:

{%- if modules %}

Submodules
----------

.. autosummary::
   :toctree:
   :recursive:

{% for item in modules if item != "keep.data" %}
   {{ item }}
{% endfor %}

{%- endif %}