## Receipt ID Determinism

All receipt IDs in the StegVerse runtime are **content-addressable and deterministic**.
This ensures cross-run reproducibility and enables reliable StegDB canonical monitoring.

### Algorithm

```python
receipt_id = SHA256(salt:action:previous_id:decision:state_snapshot)[:16].upper()
```

Where:
- `salt`: Optional per-deployment secret (`STEGVERSE_SALT` env var)
- `action`: The governed action or mutation name
- `previous_id`: Previous receipt ID in the chain, or `"GENESIS"`
- `decision`: `"ALLOWED"`, `"DENIED"`, or `"FAIL_CLOSED"`
- `state_snapshot`: Current runtime state (e.g., `"state4"`)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STEGVERSE_DETERMINISTIC_IDS` | `true` | Enable deterministic receipt IDs |
| `STEGVERSE_SALT` | `""` | Per-deployment salt for ID unpredictability |

### Files Using This

- `scripts/receipt_id.py` — Shared generator module
- `scripts/governed_action.py` — Action receipt generation
- `scripts/governed_mutation.py` — Mutation receipt generation
- `stegverse` CLI — Mutation listing receipt generation

### Verification

Run the suite multiple times with `hard` reset:
```bash
./run.sh full hard
./run.sh full hard
./run.sh full hard
```

All receipt IDs should be identical across runs. Check:
```bash
diff run_1/reconstruction.json run_2/reconstruction.json
```

### Backward Compatibility

Set `STEGVERSE_DETERMINISTIC_IDS=false` to use legacy UUID-based IDs.
Not recommended for production StegDB integration.
