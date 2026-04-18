---
slug: malformed
title: Malformed YAML
kind: note
status: draft
date_created: "2026-03-01"
tags: [test
  this is not valid yaml: [
    unclosed bracket
---

This file contains a YAML syntax error in its frontmatter. The parser should
raise a FrontmatterError wrapping the underlying YAML parse error.
