---

slug: unclosed title: Unclosed Frontmatter kind: note status: draft
date_created: "2026-03-01" tags: [test]

This file opens a frontmatter block but never closes it with a second ---. The
parser should raise a FrontmatterError when it encounters this file.
