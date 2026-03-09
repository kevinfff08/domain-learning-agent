---
name: resource-curator
description: |
  Multi-source external resource recommendation for research concepts.
  Trigger: "find resources", "recommend papers", "curate materials",
    "find tutorials", "learning resources", "related papers"
  DO NOT USE: for generating original content (use deep-researcher),
    for building the knowledge graph (use domain-mapper),
    for exporting materials (use material-integrator)
---

# Resource Curator

Searches and ranks external learning resources across multiple source types:
academic papers, code repositories, technical blogs, video lectures, and
online courses. Applies quality filters (citation counts, GitHub stars,
whitelist domains) and returns structured recommendations per concept.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 2 - Knowledge Construction & Verification |
| CLI command | (invoked as part of `newlearner learn` or standalone) |
| Python module | `src/skills/resource_curator.py` |
| Key class | `ResourceCurator` |
| Input | `ConceptNode` + `AssessmentProfile` |
| Output | `data/content/{concept_id}/resources.json` |
| Data models | `src/models/content.py` (resource-related types) |
| External APIs | SemanticScholarClient, GitHub API (via httpx) |

## Step-by-Step Instructions

### Curate Resources for a Concept

1. Load the target `ConceptNode` and learner's `AssessmentProfile`.
2. Call `ResourceCurator.curate(concept, profile)`.
3. The curator searches five resource categories:

   **a. Papers**
   - Queries Semantic Scholar for papers related to the concept.
   - Filters: citation count > 50 OR published within last 2 years.
   - Returns title, authors, year, abstract snippet, citation count, URL.

   **b. Code Repositories**
   - Searches GitHub for repositories matching the concept name.
   - Filters: stars > 100 OR actively maintained (commits in last 6 months).
   - Returns repo name, description, stars, language, URL.

   **c. Blog Posts**
   - LLM suggests relevant posts from whitelisted domains:
     `lilianweng.github.io`, `distill.pub`, `thegradient.pub`,
     `jalammar.github.io`, `colah.github.io`, `karpathy.github.io`,
     `sebastianraschka.com`, `newsletter.mlengineer.io`.
   - Returns title, author, URL, relevance note.

   **d. Videos**
   - LLM suggests relevant lectures and conference talks.
   - Returns title, channel/speaker, platform, URL, duration estimate.

   **e. Courses**
   - LLM suggests relevant course modules (not full courses).
   - Returns course name, institution, platform, specific module URL.

4. Results ranked by relevance to the concept and learner's skill level.
5. Output saved to `data/content/{concept_id}/resources.json`.

### Filtering by Learner Level

- NOVICE/BEGINNER: prioritize blog posts, videos, introductory course modules.
- INTERMEDIATE: prioritize papers with good exposition, code repositories.
- ADVANCED/EXPERT: prioritize seminal papers, cutting-edge repos, advanced lectures.

## Key Implementation Details

- Paper search uses Semantic Scholar's relevance API with field-of-study filters.
- GitHub search uses the REST search API with `GITHUB_TOKEN` for higher rate limits.
- Blog recommendations rely on LLM knowledge of the whitelisted sites; URLs
  are not verified for existence (the learner should confirm accessibility).
- Resource deduplication: if the same paper appears in both the knowledge
  graph's `key_papers` and curated results, it is merged not duplicated.

## Anti-Patterns

- **Do not curate resources before synthesizing content.** The Deep Researcher
  synthesis identifies what the learner actually needs. Curating first leads
  to an unfocused resource list.

- **Do not include resources from non-whitelisted blog domains without
  review.** The whitelist ensures quality; random blog posts may contain
  inaccuracies that conflict with the verified synthesis.

- **Do not present all resources to the learner at once.** Rank by relevance
  and present the top 3-5 per category. Information overload is
  counterproductive for learning.
