# Test fixtures

`ogd_envelope_shape.json` reproduces the **envelope shape** of a data.gov.in resource response
(`status`, `total`, `count`, `limit`, `offset`, `field`, `records`). Every record value is a
labelled placeholder (`TEST-…`). It is **not market data** and must never be shown on the site
or used to train a model.

To replace it with a recorded genuine response (spec §12), run:

```bash
python -m scripts.fetch_official_data probe --resource current --limit 3
```

then copy one stored page from `data/raw/agmarknet/<run>/page_0001.json` here and update the
expected values in `tests/test_provider.py`.
