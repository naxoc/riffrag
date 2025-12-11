# RiffRag Roadmap

This document outlines completed features and planned improvements for RiffRag.

## ✅ Completed

### v1.0 - Line-Based Chunking
**Status:** ✅ Complete

- ✅ Automatic chunking of large files by line count
- ✅ Preserves context with line number tracking
- ✅ Handles files of any size intelligently
- ✅ Returns specific line ranges in query results
- ✅ Maintains metadata (file path, start/end lines, chunk index)

**Impact:** WordPress Core and large codebases now index successfully with precise line-level results.

---

## Planned Features

## v1.1 - Function-Level Chunking (AST-Based) 📋

**Goal:** Extract individual functions and classes for even more precise results

**Why:** Line-based chunking works well, but AST parsing can provide function-level granularity.

**Implementation:**
- [ ] Integrate tree-sitter for AST parsing
- [ ] Extract PHP functions and classes with context
- [ ] Store function signatures and docblocks
- [ ] Improve query results to show specific function names
- [ ] Handle parse errors gracefully (fall back to line chunking)

**Impact:**
- Return specific functions, not just line ranges
- Better understanding of code structure
- More semantic search results

## v1.2 - JavaScript/TypeScript Support 📋

**Goal:** Extend function-level chunking to JavaScript

- [ ] JavaScript/TypeScript support (tree-sitter-javascript)
- [ ] Extract functions and classes
- [ ] Handle mixed-content files (PHP + inline JS)

## v2.0 - Web Page Indexing 💡

**Goal:** Index documentation sites alongside code

**Use Cases:**
- Index React docs, WordPress Codex, internal wikis
- Reduce hallucinations about API details
- Keep up with fast-moving frameworks
- Query docs + code together

**Implementation:**
- [ ] HTML → Markdown conversion (trafilatura, html2text)
- [ ] Sitemap-based crawling for doc sites
- [ ] Domain whitelisting and depth limiting
- [ ] Separate databases for web content
- [ ] Refresh strategy (detect when docs update)
- [ ] Create web indexing command: `just index-web <url>`

**Example:**
```bash
just index-web https://reactjs.org/docs react-docs
@react-docs-rag What's the new useEffect API?
```

## Future Ideas 💭

### Multi-Model Support
**Status:** Research needed

Currently only `mxbai-embed-large` works reliably. Testing showed:
- ❌ `nomic-embed-text` - Context length issues (2048 tokens despite claiming 8192)
- ❌ `manutic/nomic-embed-code` - Produces degenerate embeddings (all zeros/underflow)

**Needed:**
- Investigate official code-specific embedding models
- Test newer models as they become available in Ollama
- Improve model compatibility detection and validation
- Better error handling for problematic models

### Other Ideas
- Hybrid search (semantic + keyword)
- Incremental indexing (only changed files)
- Performance optimizations for very large codebases
- Better visualization of search results

---

## Contributing

Interested in working on roadmap items? Check the [issues labeled `roadmap`](../../issues?q=is%3Aissue+is%3Aopen+label%3Aroadmap) or open a new issue to discuss your idea!

## Feedback

Have ideas for the roadmap? [Open an issue](../../issues/new) or reach out!
