Getting Started
===============

This guide takes you from an empty directory to a linted, indexed wiki in a
few minutes.

Create a workspace
------------------

A Keep **workspace** is any directory containing a ``keep.yml`` file. Create
one::

   mkdir my-wiki
   cd my-wiki

Add ``keep.yml``
----------------

Every workspace needs a ``keep.yml`` at its root. The minimal configuration
is::

   schema_version: 1

That is all you need to start. See :doc:`configuration` for the full list of
options.

Write your first document
--------------------------

Create ``recipes/soffritto.md``::

   ---
   slug: soffritto
   title: Soffritto Base
   kind: recipe
   status: canon
   date_created: "2025-11-03"
   tags: [italian, base, vegetables]
   summary: Foundational aromatic base of onion, celery, and carrot for Italian sauces.
   ---

   Soffritto is the backbone of Italian cooking.

The frontmatter fields are explained in the :ref:`frontmatter reference <frontmatter>`.

Run ``keep state``
------------------

State tracking is the foundation for staleness detection. Run it first::

   keep state
   # state written to .keep/state.json (1 document(s))

Keep hashes each document's meaningful fields and records the last modification
timestamp. Run this after any editing session.

Run ``keep graph``
------------------

::

   keep graph
   # graph written to .keep/graph.json (1 node(s), 0 edge(s))

Add a second document with a relation
--------------------------------------

Create ``recipes/ragu.md``::

   ---
   slug: ragu
   title: Ragù alla Bolognese
   kind: recipe
   status: published
   date_created: "2026-01-10"
   tags: [italian, pasta, meat]
   summary: Classic slow-cooked Bolognese built on a soffritto base.
   relations:
     - target: soffritto
       type: derived_from
   ---

   A proper Bolognese takes time. The soffritto is the foundation.

Rebuild the graph::

   keep graph
   # graph written to .keep/graph.json (2 node(s), 1 edge(s))

Run ``keep index``
------------------

::

   keep index
   # index written to index.md (2 document(s))

Open ``index.md`` to see the generated catalog — the file an LLM reads at the
start of every session to orient itself.

Run ``keep lint``
-----------------

::

   keep lint
   # lint: ✓ clean — 2 document(s), 0 hard violation(s), 0 warning(s), 0 injected

The linter exits with code ``1`` when hard violations are found, making it
suitable as a CI gate. See :ref:`lint violations <violations>` for a full list
of what is checked.

Reciprocal auto-injection
--------------------------

Change ``ragu``'s relation to ``supersedes``::

   relations:
     - target: soffritto
       type: supersedes

Run ``keep lint``::

   keep lint
   # lint: ✓ clean — 2 document(s), 0 hard violation(s), 0 warning(s), 1 injected
   #
   #   soffritto [canon]
   #     ↩ injected 'superseded_by' from 'ragu'

Keep automatically wrote a reciprocal ``superseded_by`` relation into
``soffritto.md``, marked ``auto_injected: true``.

.. _frontmatter:

Frontmatter reference
---------------------

Every document must have a frontmatter block between ``---`` delimiters.

.. list-table::
   :header-rows: 1
   :widths: 15 10 10 65

   * - Field
     - Type
     - Required
     - Description
   * - ``slug``
     - string
     - yes
     - Unique identifier. URL-safe, kebab-case.
   * - ``title``
     - string
     - yes
     - Human-readable document title.
   * - ``kind``
     - string
     - yes
     - Semantic document type. Examples: ``recipe``, ``person``, ``note``.
   * - ``status``
     - string
     - yes
     - One of: ``draft``, ``review``, ``published``, ``canon``.
   * - ``date_created``
     - ISO 8601
     - yes
     - Creation date. Format: ``"2026-01-10"``.
   * - ``tags``
     - list
     - yes
     - Freeform tags for discovery.
   * - ``summary``
     - string
     - no
     - One sentence describing the document. Populates ``index.md``.
   * - ``private``
     - boolean
     - no
     - Excludes from ``index.md`` and blocks relations from public docs.
   * - ``relations``
     - list
     - no
     - Typed directed edges to other documents.

.. _violations:

Lint violations
---------------

Hard violations (block promotion to ``published`` or ``canon``):

- ``dangling_slug`` — a relation target does not exist
- ``private_target_in_public_doc`` — a public document relates to a private one
- ``missing_reciprocal`` — a symmetric relation has no backlink
- ``invalid_promotion`` — a gated document has outstanding violations

Soft warnings (advisory):

- ``incomplete`` — missing recommended fields or insufficient relations
- ``stale`` — no meaningful modification within the status threshold
