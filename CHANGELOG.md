# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2026-09-16

### Added

- Excel (`.xlsx`) export via `export_to_xlsx`, mirroring the CSV export API.
  Dates become real Excel date cells, strings become text cells, and `None`
  becomes an empty cell.
- CLI `--export xlsx` support. `--output-file` is required for xlsx output;
  binary data is never written to stdout.
- Lifecycle date highlighting in xlsx exports: past dates render as solid
  black with white text (product is dead), today renders red, dates 365+ days
  out render green, and dates in between render a red-to-yellow-to-green
  gradient. Only the seven lifecycle date columns are highlighted.
- `openpyxl` dependency for xlsx generation.

### Security

- Formula-injection defense for xlsx: string values starting with `=`, `+`,
  `-`, or `@` are written as literal text, never as formulas.
- Excel error-code strings (e.g. `#REF!`) are forced to text cells.
- Illegal control characters are stripped from cell values so untrusted API
  data cannot crash the export.

### Changed

- `--output-file` now requires `--export csv` or `--export xlsx` (previously
  CSV only).