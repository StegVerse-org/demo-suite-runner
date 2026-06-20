# Formal Testing Route Reference

This repository is the formal demo runner route.

It should consume formal testing datasets only after `StegVerse-org/StegVerse-SDK` has bound the dataset to a manifest and intake receipt.

## Required Flow

```text
Dataset / fixture / governance artifact
→ StegVerse-org/StegVerse-SDK ingestion
→ manifest binding
→ receipt binding
→ formal demo runner route
→ deterministic runner result receipt
```

## Route Responsibility

The demo-suite runner probes GCAT/BCAT formalism behavior and deterministic runner scenarios.

It should not replace:

- `StegVerse-org/stegverse-demo-suite` for public explainable demos;
- `StegGhost/entity-sandbox-runner` for adversarial or entity sandbox testing;
- `StegVerse-Labs/Standing-Proof-Engine` for commit-time standing proof;
- `StegVerse-Labs/Boundary-Test` for GLM-style boundary declaration and manifest composability cases.

## Receipt Rule

Every runner result must preserve the SDK intake manifest reference and SDK intake receipt reference.
