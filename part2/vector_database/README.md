# Local Chroma knowledge base

This folder indexes trusted **guidance documents**, never the phishing emails in `part2_handoff.csv`. The current command is a dense-retrieval smoke test only. Automated query construction from every handoff row, reranking, LLM generation, and writing the CSV `output` column are later stages.

## Set up, build, and test a search

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-part2.txt
.\.venv\Scripts\python.exe -m part2.vector_database build
.\.venv\Scripts\python.exe -m part2.vector_database search "What should I do with a suspicious account verification link?"
```

The first build downloads the configured BGE-M3 embedding model. `build` validates, chunks, and embeds the complete corpus before replacing the dedicated Chroma collection under `.chroma/`. Repeating it is safe: each successful build contains exactly the current supported files, with no stale or duplicate chunks. An empty or whitespace-only corpus is rejected before the prior collection is touched.

Search accepts one natural-language question as a quoted command-line argument. It returns ranked chunk text, stable chunk ID, filename/source metadata, optional provenance, and cosine distance (lower is closer). This manual command only verifies retrieval; future end-to-end processing will construct queries automatically from each handoff row.

## Add or change guidance

Drop any UTF-8 `.txt` or `.md` file directly into `documents/`, then run the same `build` command. No manifest edit is required. Only top-level files are discovered; other extensions and nested files are ignored. Removing or editing a document takes effect on the next successful build.

`config.json` is the ordinary edit point for the embedding model, collection name, token chunk size and overlap, embedding batch size, and search `top_k`. Changing the embedding model or chunk settings requires a rebuild; changing only `top_k` does not.

`sources.json` contains optional provenance for the seven target guidance files. It does not control discovery and does not need an entry for files you add. Metadata distinguishes `source_extract`, `adapted_source_extract`, and `original_summary` content. In particular, the NIST Phish Scale summary does not reproduce the method or worksheets: NIST currently requires organizations to establish a research license agreement for academic use and a commercialization license for commercial applications. The APWG and Google files are concise original summaries. The OWASP adaptation is attributed and distributed under CC BY-SA 4.0. CISA's joint PDF is TLP:CLEAR, subject to standard copyright rules. All sources were retrieved and checked on 2026-10-08.

The NIST MFA extract is preserved under `documents/extras/` for reference, but nested files are not discovered or indexed. This keeps the authoritative collection aligned with the requested seven-source corpus.

Generated `.chroma/` data is Git-ignored. Arbitrary files under `documents/` are also ignored so locally supplied guidance is not accidentally committed; the seven reviewed target files, the preserved nested MFA extra, and `.gitkeep` are explicit exceptions.
