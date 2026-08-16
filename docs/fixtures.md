# Fixture Strategy

Do not commit private save files, ROMs, BIOS files, or copyrighted game assets.

## Allowed fixtures

Allowed:

- tiny synthetic binary records created by tests;
- redacted byte slices that contain no meaningful trainer/save identity;
- JSON reports generated from fake/synthetic data;
- metadata-only expected outputs.

Not allowed:

- `.sav`, `.dsv`, `.duc`, `.dst` full save files;
- `.nds`, `.gba`, `.gb`, `.gbc` ROMs;
- BIOS files;
- screenshots containing copyrighted assets unless explicitly needed and legally safe;
- personal save files from Alberto's machine.

## Local-only smoke tests

Tests may reference local paths such as:

```text
D:\Users\alroc\Downloads\rolplete\POKEMON W.sav
D:\alroc\codepup\POKEMON B2.sav
```

but must skip if missing. This lets Alberto test real saves locally without requiring those files in GitHub.

## Preferred fixture evolution

1. Keep local smoke tests for real saves.
2. Add synthetic PK5 records for parser unit tests.
3. Add tiny redacted PC/party slices if needed.
4. Add JSON golden outputs for synthetic saves.

If a fixture is bigger than necessary, it is probably wrong. Binary fixtures are like hot sauce: useful, but don't pour the whole bottle into the repo.
