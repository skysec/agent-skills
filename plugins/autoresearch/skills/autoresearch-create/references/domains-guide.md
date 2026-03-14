# Domain Templates Guide

Domain templates encode accumulated knowledge about how to run experiments in specific research domains. They prevent the agent from reinventing benchmarks, ignoring established metrics, or repeating known dead ends.

## Folder Structure

```
domains/
  <domain-name>/
    DOMAIN.md                 # Guidance, pitfalls, proven approaches
    autoresearch-template.md  # Pre-filled autoresearch.md starter
    benchmark-template.sh     # Starter benchmark script
```

## How to Pick the Best Domain Match

1. List the subdirectories in `domains/`.
2. For each candidate, skim the first 10 lines of `DOMAIN.md` to see what it covers.
3. Read the full `DOMAIN.md` of the 1–2 best candidates.
4. Choose the one where the user's goal and file types overlap most clearly.
5. If confidence < 60%, proceed without a template and note "no domain match".

## Available Domains

| Domain | Best for |
|--------|---------|
| `ml-training` | Training neural networks, minimizing val loss / perplexity |
| `code-optimization` | Making code faster, reducing memory, improving throughput |
| `security-research` | Testing attack/defense mechanisms, detection rates, evasion |

## Adding a New Domain

Create `domains/<name>/` with `DOMAIN.md`, `autoresearch-template.md`, and `benchmark-template.sh`. Follow the schemas of an existing domain.
