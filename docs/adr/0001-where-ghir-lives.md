# ADR 0001: GitHub repo search is an extension package on top of ir, not part of ir

Status: accepted, 2026-10-23. Tracking: i2mint/ir#118.

## Context

The need: find something that may live in one of the user's GitHub repos, across several organizations, whether or not it is cloned locally. It was first done by hand: `gh repo list` per org to a TSV, `rg` over the descriptions, README grep over local clones, then a check of which hits were cloned. The user named the generality layers: locations (orgs, or a search query yielding repos), extraction (what each repo contributes), measuring and ranking, and caching as an orthogonal concern; above all of them, the general pattern `corpus -> extraction -> measure/filter/order/present`. They asked for the GitHub dependency to stay out of ir.

## Decision

1. **ir already is the general pattern.** `CorpusSource` (scope, change signal, indexing strategy) followed by build, `search`/`discover` is `corpus -> extraction -> ranking`. Its `records` kind takes a fetcher by import reference (`fetcher="module:attr"`), so a corpus owned by another package persists in ir's registry and rebuilds in a fresh process. So nothing new was needed in ir core: ghir supplies the fetcher, ir does indexing and ranking.
2. **The GitHub-specific parts live in ghir**: the locations (`@me`, owner logins, `search:<query>`), the fetch (GraphQL through the `gh` CLI, one call per page of repos with README text, not one per repo), the cache, and the local-clone index. ir never imports ghir or `gh`.
3. **The cache is a `MutableMapping`** (dol JSON files by default) and is **merged** on refresh, never replaced; search is offline. ir's incremental build (content-hash change signal) then re-embeds only the repos whose text changed.
4. **Ranking is a seam with two real strategies**: ir (default, hybrid) and grep (the by-hand method, no index, no model). Extraction is a seam with two named extractors plus any callable.

## Alternatives considered

- **Inside ir, behind an optional extra.** Rejected: ir's charter is a GitHub-agnostic substrate, and the user asked for no GitHub dependency there. A shell-out to `gh` behind an extra would still put GitHub knowledge (GraphQL queries, the README lookup, owner expansion) into ir's code and tests.
- **In hubcap** (the dol interface to GitHub). It is the natural home for GitHub-as-a-mapping, but it goes through PyGithub and a token, one REST call per repo; the bulk GraphQL fetch and the ir glue would sit oddly beside it. If hubcap grows a bulk repo-records store, ghir's `fetch` seam can take it.
- **In projreg.** projreg's gh sync and doc cache are keyed by locally registered projects; this search is precisely about repos that may not be local.

## Consequences

- `ghir refresh` writes one entry to ir's corpus registry (`gh_repos`), so `ir discover gh_repos ...` and federated `ir discover gh_repos packages ...` work.
- A new location kind (GitLab, a list of URLs) is a new fetcher behind the same record shape; a new ranker or extractor is a function.
