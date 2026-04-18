Configuration
=============

``keep.yml`` lives at the workspace root. All keys are optional — omitting a
section falls back to the app defaults shown below.

.. code-block:: yaml

   schema_version: 1   # required — must match the installed Keep version

   staleness:
     draft:     { days: 14 }    # flag after 2 weeks of no meaningful change
     review:    { days: 28 }    # flag after 4 weeks
     published: { days: 180 }   # flag after 6 months
     canon:     { days: null }  # never flag canon documents as stale

   completeness:
     min_ratio: 0.6             # flag if fewer than 60% of recommended fields set
     required_fields:
       - kind
       - tags
     required_relations: 1      # flag if document has no authored relations

   extensions:
     genealogy:
       applies_when: { kind: person }
       additional_required:
         - birth_date
         - family_name
       fields:
         birth_date:  { type: isodate }
         death_date:  { type: isodate }
         family_name: { type: string }

     experiment:
       applies_when: { kind: experiment }
       additional_required:
         - hypothesis
         - outcome
       fields:
         hypothesis: { type: string }
         outcome:    { type: string, enum: [succeeded, failed, inconclusive] }

A minimal ``keep.yml`` using all defaults::

   schema_version: 1

Staleness thresholds
--------------------

Staleness is calculated from ``last_meaningful_modification`` in
``.keep/state.json``, not from ``date_created``. Only these frontmatter
changes count as meaningful:

- ``status`` promoted or demoted
- ``kind`` assigned or changed
- ``relations`` added or removed
- Extension fields populated

Cosmetic edits — prose rewrites, summary updates, tag changes — do not reset
the staleness clock.

Extensions
----------

Extensions add required fields to documents of a specific ``kind``. The bar
for adding one is intentionally high: add an extension only when the absence
of a field would make a document of that kind structurally incomplete, not
just less useful.

Three conditions must all be true before adding an extension:

1. The field is required, not optional.
2. The field would be meaningless on other document kinds.
3. You already have at least two or three real documents of this kind.

To define a custom extension in ``keep.yml``::

   extensions:
     my-kind:
       applies_when: { kind: my-kind }
       additional_required:
         - my_field
       fields:
         my_field:     { type: string }
         optional_one: { type: string }

Schema versioning
-----------------

``schema_version`` in ``keep.yml`` must match the version declared in Keep's
bundled ``schema.yml``. Keep rejects a mismatch at startup to prevent silent
incompatibilities. The current schema version is ``1``.
