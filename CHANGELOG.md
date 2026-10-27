# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions
follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Automatic chart end: without `end` or `duration`, the chart stops
  after the last task, at the end of its period.
- Checks of the input, with every problem of the file listed at once,
  its line and a hint ("did you mean 'duration'?"). New checks: keys
  given twice, empty values (e.g. an unquoted hex color), invalid dates,
  durations, percentages, colors, `step`, `label_every`,
  `label_format`, booleans where text is expected, tasks without a
  length, segments before their task or overlapping, the output file
  format and folder.
- Warnings for tasks or milestones cut by the chart, subtasks out of
  their task, a `now` line outside the chart, tasks sharing a color.
- `GanttError` (a `ValueError`) with the list of `issues`, and
  `Gantt.check()` for the warnings.
- Tests (pytest), run by the CI.

### Changed

- Invalid input raises `GanttError` instead of `TypeError`.
- `Gantt.start` has no default on dated scales: a missing start date is
  reported instead of failing on `0`.
- Errors no longer end with a Python traceback: an invalid
  `label_format`, `step: 0` (which hung), `label_every: 0`, a file that
  is a list or an output format matplotlib does not know are reported
  as errors.

## [0.1.0] - 2026-10-26

First public release.

### Added

- `yml2gantt` command (and `python -m yml2gantt`): draw a gantt from a
  `.yml` file to PDF, PNG, SVG or any matplotlib format.
- Day, week, month, trimester and abstract time scales, with custom
  period labels (`label_format`, `label_every`).
- Tasks with subtasks, `label` text in the bars, and colors.
- Milestones on their own row or placed on a bar (end, percentage,
  offset or date).
- Segments: several pieces of bar on one row.
- "We are here" line at today's date or at any position (`now`).
- Python API: `Gantt`, `load_yaml`, `from_dict`, drawing into existing
  matplotlib axes.

