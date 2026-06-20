# Testing Data Loop Contract

This repository is a downstream formal runner route.

Formal runner inputs reach this repository after the corrected testing data loop has produced receipt-bound artifacts.

## Required Upstream Loop

```text
User
→ StegVerse-org/StegVerse-SDK or LLM Adapter
→ StegVerse-org ingestion
→ StegGhost/entity-sandbox-runner ingestion/CGE
→ ephemeral sandbox batch
→ StegGhost/entity-sandbox-runner ingestion/CGE return validation
→ StegVerse-org ingestion
→ demo-suite-runner
```

## Required Input Evidence

Formal runner inputs preserve:

```text
sdk_or_llm_adapter_intake receipt
stegverse_org_ingestion_outbound receipt
stegghost_ingestion_cge_admission receipt
ephemeral_sandbox_batch receipt
stegghost_ingestion_cge_return_validation receipt
stegverse_org_ingestion_return receipt
master-records action receipt references
```

## Runner Responsibility

The formal runner probes GCAT/BCAT formalism behavior and deterministic runner scenarios using receipt-bound artifacts.

SDK contract reference:

```text
StegVerse-org/StegVerse-SDK/docs/TESTING_DATA_LOOP_CONTRACT.md
```

Route result schema:

```text
StegVerse-org/StegVerse-SDK/schemas/formal-testing-route-result.schema.json
```
