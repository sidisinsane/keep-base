# A Plain Markdown File

This file has no frontmatter block whatsoever. It is valid Markdown but invalid
as a Keep document. The parser should raise a FrontmatterError when it
encounters this file.
