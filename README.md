# Keep

> **Deprecated.** This Python implementation is no longer maintained. It has
> been superseded by [keep-go](https://github.com/sidisinsane/keep-go), a full
> rewrite in Go with improved architecture and schema-driven validation. Please
> use keep-go for all new and existing workspaces.

Keep is a personal wiki tool for people who think carefully and want their
thinking to compound over time. You write Markdown documents with structured
frontmatter. Keep reads that frontmatter and produces derived artefacts — a
relationship graph, a document index, a staleness report — that make your
knowledge base navigable and maintainable even as it grows.

The problem Keep solves is one most people feel but rarely name: you learn
things, you write things, you save things — and then you lose them. Not because
they are deleted, but because they are scattered, unconnected, and contextless.
Keep is the answer to *I know I wrote about this before, but I cannot find it or
pick up the thread.*

---

## Contents

- [How it works](#how-it-works)
- [Installation](#installation)
- [Getting started](#getting-started)
- [Workspace structure](#workspace-structure)
- [Frontmatter reference](#frontmatter-reference)
- [Commands](#commands)
- [Configuration](#configuration)
- [Keep and LLMs](#keep-and-llms)
- [Development](#development)

---

### How it works

A Keep **workspace** is a folder of Markdown files. Each file is a document.
Each document has a YAML frontmatter block at the top that describes it
structurally — its slug, title, status, relations to other documents, and more.

Keep reads that frontmatter and produces four derived artefacts:

| Artefact     | Location           | Purpose                                                                |
| ------------ | ------------------ | ---------------------------------------------------------------------- |
| `graph.json` | `.keep/graph.json` | Machine-readable graph of all documents and relations                  |
| `state.json` | `.keep/state.json` | Staleness tracking — when was each document last meaningfully changed? |
| `lint.json`  | `.keep/lint.json`  | Validation report — violations, warnings, auto-injections              |
| `index.md`   | `index.md`         | Human and LLM-readable catalog of all documents                        |

These artefacts are rebuilt deterministically on each run. You never edit them
directly. The documents themselves are the source of truth.

After a full run, a workspace looks like this:

```text
my-wiki/
├── keep.yml                  # workspace configuration
├── index.md                  # generated catalog
├── .keep/
│   ├── graph.json
│   ├── state.json
│   └── lint.json
├── recipes/
│   ├── ragu.md
│   └── soffritto.md
└── people/
    └── marcella-hazan.md
```

---

#### Installation

Keep requires Python 3.12 or later.

**From PyPI** (once published):

```bash
uv tool install keep
```

**From source** (current):

```bash
uv tool install git+https://github.com/your-username/keep
```

Verify the installation:

```bash
keep --help
```

To upgrade:

```bash
uv tool upgrade keep
# or from source:
uv tool install --force git+https://github.com/your-username/keep
```

---

##### Getting started

This walk-through takes you from an empty directory to a linted, indexed wiki in
a few minutes.

###### 1. Create a workspace

```bash
mkdir my-wiki
cd my-wiki
```

###### 2. Add `keep.yml`

Every workspace needs a `keep.yml` at its root. Create one with the following
content — this is the minimal configuration and uses all defaults:

```yaml
schema_version: 1
```

That is all you need to start. See [Configuration](#configuration) for the full
list of options.

###### 3. Write your first document

Create `recipes/soffritto.md`:

```markdown
---
slug: soffritto
title: Soffritto Base
kind: recipe
status: canon
date_created: "2025-11-03"
tags: [ italian, base, vegetables ]
summary: Foundational aromatic base of onion, celery, and carrot for Italian
  sauces.
---

Soffritto is the backbone of Italian cooking. Equal parts onion, celery, and
carrot, cooked slowly in olive oil until completely soft and sweet. Never brown
— the goal is a melting, fragrant base.
```

The frontmatter fields are:

- `slug` — a unique identifier for this document (URL-safe, kebab-case)
- `title` — the human-readable name
- `kind` — the semantic type (`recipe`, `person`, `note`, etc.)
- `status` — lifecycle stage (`draft`, `review`, `published`, `canon`)
- `date_created` — ISO 8601 date
- `tags` — freeform list
- `summary` — one sentence describing the document (used in `index.md`)

###### 4. Run `keep state`

State tracking is the foundation for staleness detection. Run it first:

```bash
keep state
# state written to .keep/state.json (1 document(s))
```

Keep reads each document's frontmatter, hashes the fields that matter for
staleness, and records the last meaningful modification timestamp. Run this
after any significant editing session.

###### 5. Run `keep graph`

```bash
keep graph
# graph written to .keep/graph.json (1 node(s), 0 edge(s))
```

The graph captures all documents as nodes and all relations as typed directed
edges. With one document and no relations, you get one node and no edges.

###### 6. Add a second document with a relation

Create `recipes/ragu.md`:

```markdown
---
slug: ragu
title: Ragù alla Bolognese
kind: recipe
status: published
date_created: "2026-01-10"
tags: [ italian, pasta, meat ]
summary: Classic slow-cooked Bolognese built on a soffritto base.
relations:
  - target: soffritto
    type: derived_from
---

A proper Bolognese takes time. The soffritto is the foundation.
```

The `relations` field declares that `ragu` derives from `soffritto`. This is a
typed directed edge in the graph.

###### 7. Rebuild the graph

```bash
keep graph
# graph written to .keep/graph.json (2 node(s), 1 edge(s))
```

Two documents, one relation.

###### 8. Run `keep index`

```bash
keep index
# index written to index.md (2 document(s))
```

Open `index.md`:

```markdown
<!-- Auto-generated by keep. Do not edit. -->

| slug      | title               | kind   | status    | summary                                                                     |
| --------- | ------------------- | ------ | --------- | --------------------------------------------------------------------------- |
| ragu      | Ragù alla Bolognese | recipe | published | Classic slow-cooked Bolognese built on a soffritto base.                    |
| soffritto | Soffritto Base      | recipe | canon     | Foundational aromatic base of onion, celery, and carrot for Italian sauces. |
```

This is the catalog an LLM reads at the start of every session to locate
relevant documents before drilling into them.

###### 9. Run `keep lint`

```bash
keep lint
# lint: ✓ clean — 2 document(s), 0 hard violation(s), 0 warning(s), 0 injected
# report written to .keep/lint.json
```

A clean pass. Now add a relation to a document that does not exist:

```yaml
relations:
  - target: ghost-doc
    type: inspired_by
```

Run `keep lint` again:

```bash
keep lint
# lint: ✗ violations found — 2 document(s), 1 hard violation(s), 0 warning(s), 0 injected
#
#   ragu [published]
#     ✗ dangling_slug: target 'ghost-doc' does not exist
#     ✗ invalid_promotion: 'published' requires zero hard violations but 1 found
```

The linter exits with code `1` when hard violations are present. This makes it
suitable as a pre-commit gate. Revert the change and the pass is clean again.

###### 10. See reciprocal auto-injection

Add a `supersedes` relation to `ragu`:

```yaml
relations:
  - target: soffritto
    type: supersedes
```

Run `keep lint`:

```bash
keep lint
# lint: ✓ clean — 2 document(s), 0 hard violation(s), 0 warning(s), 1 injected
#
#   soffritto [canon]
#     ↩ injected 'superseded_by' from 'ragu'
```

Keep automatically wrote a reciprocal `superseded_by` relation into
`soffritto.md`. Open it and you will see the injected entry marked with
`auto_injected: true`.

---

##### Workspace structure

```text
my-wiki/
├── keep.yml          # workspace configuration — edit this
├── index.md          # generated by `keep index` — do not edit
├── .keep/            # generated artefacts — do not edit
│   ├── graph.json
│   ├── state.json
│   └── lint.json
└── <your documents>  # organised however you like
```

**`keep.yml`** is the only file in the workspace you configure directly.
Everything else is either a document you write or an artefact Keep generates.

**`index.md`** lives at the workspace root rather than in `.keep/` because it is
a first-class navigational artefact — useful to humans and LLMs alike, not just
internal tooling state.

**`.keep/`** contains tool-generated state. Never edit these files manually.
`state.json` is the only one that is stateful — if you delete it, staleness
timestamps are re-seeded from filesystem `mtime`.

**Document organisation** is entirely up to you. Keep walks the workspace
recursively, so you can use any folder structure you like. Subfolders by kind,
by project, by year — whatever matches how you think.

---

##### Frontmatter reference

Every document must have a frontmatter block between `---` delimiters at the top
of the file.

###### Core fields

| Field          | Type     | Required | Description                                                                                                                             |
| -------------- | -------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `slug`         | string   | yes      | Unique identifier. URL-safe, kebab-case. Must be unique across the workspace.                                                           |
| `title`        | string   | yes      | Human-readable document title.                                                                                                          |
| `kind`         | string   | yes      | Semantic document type. Examples: `recipe`, `person`, `note`, `prd`, `experiment`. Drives extension selection.                          |
| `status`       | string   | yes      | Lifecycle stage. One of: `draft`, `review`, `published`, `canon`.                                                                       |
| `date_created` | ISO 8601 | yes      | Creation date. Format: `"2026-01-10"`.                                                                                                  |
| `tags`         | list     | yes      | Freeform tags for discovery.                                                                                                            |
| `summary`      | string   | no       | One sentence describing the document. Used to populate `index.md`. Intended to be written by an LLM during ingest.                      |
| `private`      | boolean  | no       | If `true`, the document is excluded from `index.md` and cannot be the target of relations from non-private documents. Default: `false`. |
| `relations`    | list     | no       | Typed directed edges to other documents. See below.                                                                                     |

###### Lifecycle statuses

| Status      | Meaning                              | Lint gate        |
| ----------- | ------------------------------------ | ---------------- |
| `draft`     | Raw capture, not yet categorised     | None             |
| `review`    | Categorised, awaiting assessment     | None             |
| `published` | Wiki-quality, active member          | Linter must pass |
| `canon`     | Settled, load-bearing, gravitational | Linter must pass |

Documents cannot be promoted to `published` or `canon` if the linter reports
hard violations.

###### Relations

```yaml
relations:
  - target: soffritto # slug of the target document
    type: derived_from # relation type
```

Available relation types:

| Type            | Meaning                                            | Symmetric?          |
| --------------- | -------------------------------------------------- | ------------------- |
| `derived_from`  | This document originates from the target           | No                  |
| `extends`       | This document builds upon the target               | No                  |
| `supports`      | This document provides evidence for the target     | No                  |
| `contradicts`   | This document conflicts with the target            | Yes — auto-injected |
| `inspired_by`   | Loose creative or conceptual influence             | No                  |
| `supersedes`    | This document replaces the target                  | Yes — auto-injected |
| `addresses_gap` | This document fills a gap identified in the target | No                  |

**Symmetric relations** (`contradicts`, `supersedes`) are automatically
reciprocated by `keep lint`. If document A supersedes document B, Keep injects a
`superseded_by` relation into B's frontmatter and marks it
`auto_injected:
true`. You should not write `superseded_by` manually.

###### Extensions

Extensions add required fields to documents of a specific `kind`. Two are built
in:

**`genealogy`** — applies when `kind: person`:

```yaml
birth_date: "1924-04-15" # required
family_name: Hazan # required
death_date: "2013-09-29" # optional
```

**`experiment`** — applies when `kind: experiment`:

```yaml
hypothesis: "..." # required
outcome: succeeded # required — one of: succeeded, failed, inconclusive
```

Define your own extensions in `keep.yml`. See [Configuration](#configuration).

---

##### Commands

All commands are run from the workspace root (the directory containing
`keep.yml`).

###### `keep graph`

Rebuilds `.keep/graph.json` from frontmatter.

```bash
keep graph
# graph written to .keep/graph.json (12 node(s), 8 edge(s))
```

Run after adding or modifying relations.

###### `keep state`

Updates `.keep/state.json` with the latest document hashes and timestamps.

```bash
keep state
# state written to .keep/state.json (12 document(s))
```

Run after any editing session. Keep distinguishes meaningful changes (status
promoted, kind assigned, relations added) from cosmetic ones (prose edits,
summary rewrites). Only meaningful changes reset the staleness clock.

###### `keep index`

Rebuilds `index.md` at the workspace root.

```bash
keep index
# index written to index.md (11 document(s))
```

Private documents are excluded. Run after adding or modifying documents.

###### `keep lint`

Validates all documents and writes `.keep/lint.json`.

```bash
keep lint
# lint: ✓ clean — 12 document(s), 0 hard violation(s), 2 warning(s), 0 injected
# report written to .keep/lint.json
```

Exits with code `0` if clean, `1` if hard violations are found. Hard violations
block graduation to `published` or `canon`. Warnings are advisory.

**Hard violations:**

- `dangling_slug` — a relation target does not exist
- `private_target_in_public_doc` — a public document relates to a private one
- `missing_reciprocal` — a symmetric relation has no backlink (rare after
  auto-injection)
- `invalid_promotion` — a `published` or `canon` document has outstanding
  violations

**Soft warnings:**

- `incomplete` — missing recommended fields or insufficient relations
- `stale` — no meaningful modification within the threshold for the document's
  status

###### Global flags

```bash
keep --verbose <command>   # enable debug logging
keep --help                # list all commands
```

---

##### Configuration

`keep.yml` lives at the workspace root. All keys are optional — omitting a
section falls back to the app defaults shown below.

```yaml
schema_version: 1 # required — must match the installed Keep version

staleness:
  draft: { days: 14 } # flag after 2 weeks of no meaningful change
  review: { days: 28 } # flag after 4 weeks
  published: { days: 180 } # flag after 6 months
  canon: { days: null } # never flag canon documents as stale

completeness:
  min_ratio: 0.6 # flag if fewer than 60% of recommended fields are set
  required_fields:
    - kind
    - tags
  required_relations: 1 # flag if document has no authored relations

extensions:
  genealogy:
    applies_when: { kind: person }
    additional_required:
      - birth_date
      - family_name
    fields:
      birth_date: { type: isodate }
      death_date: { type: isodate }
      family_name: { type: string }

  experiment:
    applies_when: { kind: experiment }
    additional_required:
      - hypothesis
      - outcome
    fields:
      hypothesis: { type: string }
      outcome: { type: string, enum: [ succeeded, failed, inconclusive ] }
```

You only need to include the sections you want to change. A minimal `keep.yml`
for a workspace that uses only the defaults:

```yaml
schema_version: 1
```

###### Adding a custom extension

Extensions add required fields to documents of a specific `kind`. The bar for
adding an extension is intentionally high — add one only when the absence of a
field would make a document of that kind structurally incomplete, not just less
useful.

```yaml
extensions:
  recipe:
    applies_when: { kind: recipe }
    additional_required:
      - source
    fields:
      source: { type: string }
      prep_time: { type: string }
      servings: { type: string }
```

---

##### Keep and LLMs

Keep is designed to work alongside an LLM in a persistent, compounding knowledge
base. The intended workflow:

**Ingest** — when you capture a new source (article, chat export, PDF), ask the
LLM to create a Keep document for it. The LLM writes the frontmatter (`slug`,
`title`, `kind`, `tags`, `summary`, `relations`) and the prose body. The
`summary` field is specifically for the LLM — one sentence that describes what
the document is, used to populate `index.md`.

**Orient** — at the start of every session, the LLM reads `index.md` first to
locate relevant documents before drilling into them. This replaces expensive
full-workspace scans.

**Maintain** — run `keep state`, `keep graph`, `keep index`, and `keep lint`
after each session to keep the derived artefacts current. The LLM can run these
commands itself as part of an ingest skill.

**Lint as gate** — `keep lint` exits non-zero on hard violations, making it
suitable as a quality gate before promoting documents to `published` or `canon`.

A minimal ingest skill prompt looks like:

```text
Read index.md to orient yourself.
Create a new document for the attached source.
Write frontmatter with slug, title, kind, status: draft, date_created (today),
tags, summary (one sentence), and any relations you can identify.
Run: keep state && keep graph && keep index && keep lint
Report the lint result.
```

---

##### Development

Keep is built with [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/your-username/keep
cd keep
uv sync --dev
```

Run the full check suite:

```bash
make check-all
```

Individual targets:

```bash
make py/check       # ruff format + lint check
make py/fix         # ruff format + lint auto-fix
make py/test        # pytest with coverage
make py/security    # bandit security analysis
make docs/yml-check # yamllint
make docs/md-check  # pymarkdownlnt
```

Tests require a minimum of 80% coverage. The test suite includes unit tests,
integration tests, and subprocess CLI tests.
