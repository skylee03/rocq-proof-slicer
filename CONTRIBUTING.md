# Contributing

This repository is a small research prototype. Contributions that improve
clarity, portability, or the quality of the slice are welcome.

## Before you start

- Read `README.md` and `docs/DESIGN.md`.
- Keep the scope honest: this is **not** a sound slicer for dependent type
  theory. Do not describe it as one in code comments, docs, or PRs.
- If you change slicing behavior, add a regression test.

## Development

Requirements:

- Rocq 9.x with `rocq` on `PATH` (`rocq compile`)
- Python 3.10+

Run the unit tests (no Rocq required):

```bash
make unit
```

Run the full integration demo (requires Rocq):

```bash
make test
make demo
```

## Pull requests

- Keep changes focused.
- Update `README.md` or `docs/DESIGN.md` when behavior or scope changes.
- Add a short note to `CHANGELOG.md` for user-visible changes.
- If you add a demo file, make sure `rocq compile -q <file>` succeeds before relying on it.

## Code style

- Python 3.10+, standard library only.
- Prefer small, explicit functions over clever abstractions.
- Keep the generated `.vo`, `.glob`, and sliced `.v` files out of commits.

## Reporting issues

Please include:

- Rocq version (`rocq --version`),
- the input `.v` file or a minimal reproduction,
- the command you ran,
- the expected and actual output.
