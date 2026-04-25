# Optional Reconstruction Pattern Patch

If reconstruction reports unexplained variance for the new mutation wrapper output, add these known patterns to `scripts/reconstruct.py` in `detect_unexplained_variance()`:

```text
^Mutation fail_closed:
^Mutation denied:
^mapped_action:
^admissibility:
```

If the reconstruction report still shows `Expected: None` for matrix rows, update the report table generation to read:

```python
expected = case.get("formal_expected") or case.get("expected")
```

instead of relying only on `expected`.
