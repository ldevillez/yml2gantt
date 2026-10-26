# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions
follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

