# Codex Credit Counter Changelog

## [Unreleased]

### Added
- feat: add session id and project name (parsed from session cwd) to SessionContext
- feat: various output handler output id and project name
- feat: Respect `CODEX_HOME` environment variable when calculating session path

### Changed
- refactor: rename core.`SessionState` to `SessionContext`
- refactor: rename core.`parse_token_counter` to `parse_session`
- refactor: rename io.text.`CreditsLogWriter` to `CreditsIncrementalOutputHandler`
- refactor: move incremental session parsing from watcher.`watch` to core.`parse_session_incremental`

### Fixed
- `CreditsTokenCountHandler` no longer crashes when no credit usage occured

### Removed
- remove core.`DATE_FORMAT` and `DATETIME_FORMAT` and handle date formats inline

## [0.2.1] - 2026-05-12

### Fixed
- correct credit calculation

    Credits have been calculated with input_tokens * rate + cached_tokens * rate + output_tokens * rate.
    This falsely counts cached_tokens both at cached rate and again at input rate.
    This has been corrected to calculate only the *actual uncached* input_tokens at input rate with
    (input_tokens - chached_tokens) * rate + cached_tokens * rate + output_tokens * rate.

## [0.2.0] - 2026-05-10

### Added
- cli parameter `--type` specifies output type
    - `compact` output only credit usage (default)
    - `ext` outputs extended credit usage
    - `json` outputs each `token_count` event as json
    - `jsonl` outputs each `token_count` event as jsonl
    - `xlsx` write each `token_count` event to excel file
        - uses `openpyxl` library
        - `xlsx` extra as optional dependency
- cli parameter `-follow` continously watches sessions for changes and updates output
    - uses `watchdog` library
    - `follow` extra as optional dependency
- cli parameter `-v` and `-vv` control logging level
- pyproject.toml: `codexcost` cli script
- pyproject.toml: `all` optional dependency
- added README.md with installation and usage information

### Changed
- single script broken into separate modules
- rename cli parameter `--full-history` to `--all-history`
    - rename shorthand `-f` to `-a` to make place for parameter for follow mode
- remove cli parameter `--csv`; use `--type csv` instead
- remove cli parameter `--csv-excel`; use `--type xlsx` for excel xlsx output

### Fixed
- correct handling of `token_count` duplicates
    - `token_count` events must increase `total_tokens` to be counted

## [0.1.0] - 2026-05-04

- first prototype

#### Added
- calculate credit count for current month
- parameter `--full-history`: calculate credit count for complete history
- parameter `--csv`: export token count as csv
- parameter `--csv-excel`: export token count as excel csv
