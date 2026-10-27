# yml2gantt

[![PyPI](https://img.shields.io/pypi/v/yml2gantt)](https://pypi.org/project/yml2gantt/)
[![Python](https://img.shields.io/pypi/pyversions/yml2gantt)](https://pypi.org/project/yml2gantt/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/ldevillez/yml2gantt/blob/main/LICENSE)

Write your project plan in a small YAML file, get a clean gantt chart
(PDF, PNG, SVG, …) drawn with matplotlib.

```yaml
gantt:
  start: 2026-01-05     # the chart ends after the last task

tasks:
  - {name: Write, duration: 2w}
  - {name: Review, start: 2w, duration: 1w}
  - {name: Ship, start: 3w, milestone: true}
```

```sh
yml2gantt plan.yml -o plan.png
```

![Gantt chart of the roadmap example](https://raw.githubusercontent.com/ldevillez/yml2gantt/main/docs/images/roadmap.png)

## Features

- Plain YAML input: easy to write by hand, to diff and to keep in git
- Tasks with subtasks (a task without duration spans its subtasks)
- Milestones, on their own row or placed on a task's bar
- Interrupted tasks: several bar segments on one row
- Custom text in the bars (`label`), e.g. who works on the task
- Day, week, month, trimester or abstract (numbered) time scales
- Positions as dates or as offsets (`3`, `"2w"`), lengths as durations or end dates
- A "we are here" line at today's date or at any position
- Export to any format matplotlib supports (PDF, PNG, SVG, …)
- A Python API to build charts from code, or to draw into your own figures

## Installation

Requires Python 3.11 or newer.

```sh
pip install yml2gantt
```

To use only the command line tool, `pipx install yml2gantt` or
`uv tool install yml2gantt` install it in its own environment.

## Command line

```sh
yml2gantt examples/project.yml
```

This draws the chart, saves it as `examples/project.pdf` and opens a
window with it.

| Option            | Effect |
|-------------------|--------|
| `-o, --output F`  | Output file (default: `<file>.pdf`). The extension sets the format: `.pdf`, `.png`, `.svg`, … |
| `--no-show`       | Do not open a window (for scripts, CI, servers). |
| `--version`       | Print the version and exit. |
| `-h, --help`      | Show the help. |

```sh
yml2gantt examples/workpackages.yml -o plan.png --no-show
python -m yml2gantt examples/sprint.yml     # same thing
```

### Errors and warnings

The file is checked before drawing, and every problem is listed at once,
with its line and a hint on how to fix it. The tool then exits with
status 1:

```text
yml2gantt: error in plan.yml: 3 errors:
  - line 6, task 'Permits': unknown key 'durtion' (did you mean 'duration'?). Allowed keys: color, duration, end, label, milestone, milestones, name, segments, start, subtasks
  - line 12, task 'Shop' > subtask 'Paint': invalid 'duration' '3m': unknown unit 'm', use 'd' (days) or 'w' (weeks). There is no month unit, as months have different lengths: use dates instead
  - line 20, task 'Launch': 'color' has no value: a hex color must be in quotes, color: "#3366cc" (an unquoted # starts a comment in YAML)
```

Among the checks: misspelled keys, sections or scale names (with a
suggestion), keys given twice, invalid dates (`2026-02-30`), durations,
percentages and colors, unquoted `yes`/`no` read as booleans by YAML,
tasks without a length, overlapping segments, YAML syntax errors (such
as tabs), and an output file with an unknown format or folder (checked
before drawing).

Things that do not stop the drawing are printed as warnings: a task or
milestone cut by the chart end, subtasks going out of their task, a
`now` line outside the chart, top-level tasks with the same name (they
get the same color).

## The YAML format

A file has two sections: `gantt` (the time axis) and `tasks` (the rows).

```yaml
gantt:
  start: 2026-01-05
  duration: 12w
  scale: week
  title: My project

tasks:
  - name: Kick-off
    start: 0
    duration: 3d
    label: Team A                 # text in the bar (default: the name)
    milestones: [Go]              # diamond at the end of the bar

  - name: Development             # no duration: spans its subtasks
    start: 2026-01-12
    subtasks:
      - {name: Backend, start: 0, duration: 4w}
      - {name: Frontend, start: 2w, duration: 5w,
         milestones: [{name: Demo, at: 50%}]}

  - {name: Release, start: 2026-03-20, milestone: true}
```

Keys are case-insensitive, and `task` is accepted instead of `name`.
Unknown keys are reported as errors, so typos do not go unnoticed. A key
written with no value (`color:`) is an error too, except for the lists
(`tasks`, `subtasks`, `milestones`, `segments`).

### Dates, offsets and durations

| You write        | Meaning |
|------------------|---------|
| `2026-01-05`     | A date (ISO format). |
| `"2026-W02-1"`   | An ISO week date: Monday of week 2 of 2026 (quote it). |
| `3` or `2.5`     | A number of days (on the `abstract` scale: a number of units). |
| `"3d"`, `"2w"`   | 3 days, 2 weeks. Decimals work: `"1.5w"`. |

A position (`start`, `end`, a milestone's `at`) is either a date or an
**offset**. Offsets count from the chart start for tasks, from the
parent start for subtasks, and from the task start for segments and
milestones. There is no month unit, because months have different
lengths: use dates for that.

On the `abstract` scale, all positions and lengths are plain numbers.

### `gantt` section

| Key            | Description |
|----------------|-------------|
| `start`        | Start date (`2026-01-05`, `"2025-W38-7"`), required on dated scales; a number on the `abstract` scale (default `0`). |
| `end`          | End of the chart (exclusive). Give `end`, `duration` or neither. |
| `duration`     | Length of the chart: days (`90`) or `"3d"`, `"13w"`. |
| `scale`        | `day`, `week` (default), `month`, `trimester` or `abstract`. |
| `title`        | Chart title. |
| `show_today`   | Draw a red line at today's date (default `true`, dated scales only, ignored when `now` is set). Nothing is drawn if today is outside the chart. |
| `now`          | Draw the "we are here" line at this position instead of today: a date or an offset (e.g. `5.5` on an abstract scale). Works on every scale. |
| `now_label`    | Text above that line. Default: `Now` (with `now`) or `Today`. `""` for no text. |
| `label_format` | Period label, see below. |
| `label_every`  | Label only one period out of N: a whole number, default `1`. |
| `step`         | Period size for the `abstract` scale: a number above 0, default `1`. |

Without `end` and `duration`, the chart ends after the last task, at
the end of its period (week, month, …, or `step` on the abstract
scale), so the grid ends cleanly. A milestone row gets one more period,
so its diamond is not drawn on the border.

### Time scales and labels

| Scale       | One period is | Default label | Light grid lines |
|-------------|---------------|---------------|------------------|
| `day`       | a day         | `Jan 05`      | none |
| `week`      | a week (Monday to Sunday) | `W02` | days |
| `month`     | a month       | `Jan 2026`    | weeks |
| `trimester` | a quarter     | `Q1 2026`     | months |
| `abstract`  | `step` units  | `1, 2, 3…`    | none |

`label_format` is a Python format string with these placeholders:

| Placeholder | Value |
|-------------|-------|
| `{date}`    | First day of the period. Takes [strftime codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes): `{date:%b}` → `Jan`, `{date:%d/%m}` → `05/01`. |
| `{q}`       | Quarter number (1 to 4). |
| `{n}`       | Period number, from 1. The only placeholder on the `abstract` scale. |

Use `\n` (in a double-quoted string) for two-line labels, e.g.
`"{date:%a}\n{date:%d}"` or `"Q{q}\n{date:%Y}"`. A period cut to less
than half by the chart start or end is left unlabelled.

### Tasks and subtasks

| Key          | Description |
|--------------|-------------|
| `name`       | Shown on the y axis, and inside the bar unless `label` is set. Required. |
| `label`      | Text written inside the bar instead of `name` (next to the diamond for a milestone row). `""` leaves the bar empty. |
| `start`      | A date or an offset (see above). Default `0`. |
| `duration`   | Length: a number, `"3d"` or `"2w"`. |
| `end`        | End date or offset, instead of `duration`. |
| `color`      | Any [matplotlib color](https://matplotlib.org/stable/users/explain/colors/colors.html) (`tab:red`, `"#3366cc"`, `lightgrey`, …). |
| `subtasks`   | List of subtasks (same keys, one level deep). |
| `milestone`  | `true` turns the entry into a milestone row (see below). |
| `milestones` | Milestones drawn on the bar (see below). |
| `segments`   | Several pieces of bar on the same row (see below). |

- A task without `duration`/`end` spans its subtasks (or its segments).
- Tasks take the next color of the matplotlib color cycle. Subtasks use
  a lighter version of their parent's color, and write their text in the
  parent's color.
- Subtasks can be milestones too (`milestone: true`), and get the
  parent's color.

### Milestones

There are two kinds of milestone.

**On a task's bar**, with `milestones` (tasks and subtasks):

```yaml
milestones:
  - Done                    # at the end of the bar
  - {name: Review, at: 40%} # 40% of the bar length
  - {name: Demo, at: 4}     # 4 units after the task start
  - {name: Freeze, at: 2026-02-01, color: tab:red}   # a date
```

`at` defaults to `100%`. Percentages go from `0%` to `100%` and use the drawn bar, so they also
work on a task that spans its subtasks. Milestones are black unless
`color` is given. The label goes to the right of the diamond, or to its
left in the last 20% of the chart.

**On their own row**, with `milestone: true`: the entry takes only a
`start` (no `duration`, `end`, `subtasks`, `segments` or `milestones`)
and is drawn as a diamond.

```yaml
- {name: Grand opening, start: 89, milestone: true, color: tab:red}
```

### Segments

A task interrupted in the middle, or split into phases, can have
several pieces of bar on its row:

```yaml
- name: Field trials
  label: "Team B"           # written in each segment
  start: 2
  segments:
    - {start: 0, duration: 3}               # offsets from the task start
    - {start: 5, end: 8, label: "Retest"}   # own label
  milestones: [Report]      # end of the last segment
```

| Key          | Description |
|--------------|-------------|
| `start`      | A date, or an offset from the task start. Default `0`. |
| `duration` / `end` | Length, or end date/offset (one of them is required). |
| `color`      | Default: color of the task. |
| `label`      | Text in the segment. Default: the task `label` (or its name). `""` leaves it empty. |

The task spans from its `start` to the end of its last segment: this is
what its parent and its percentage milestones use. Segments cannot start
before their task or overlap each other; touching segments are
separated by a thin white line. A task with segments takes no
`duration`/`end` and no `subtasks`.

### Abstract scale

Use `scale: abstract` when the chart has no calendar dates, e.g. a
project plan in quarters or a course in weeks. All positions and
lengths are plain numbers.

```yaml
gantt:
  start: 0
  duration: 16
  scale: abstract
  step: 1               # one column per unit
  label_format: "Q{n}"  # Q1, Q2, …
  title: Work plan
  now: 5.5              # "we are here": middle of Q6
```

## Examples

Each example in [`examples/`](https://github.com/ldevillez/yml2gantt/tree/main/examples)
is commented and shows a different part of the format.

| File | Shows |
|------|-------|
| [`minimal.yml`](https://github.com/ldevillez/yml2gantt/blob/main/examples/minimal.yml) | The smallest useful file |
| [`project.yml`](https://github.com/ldevillez/yml2gantt/blob/main/examples/project.yml) | Week scale, ISO week date, subtasks, milestone rows, offsets in days, short bar labels |
| [`sprint.yml`](https://github.com/ldevillez/yml2gantt/blob/main/examples/sprint.yml) | Day scale, two-line labels, `end` dates, people in the bars, `now` at a date, an interrupted task |
| [`roadmap.yml`](https://github.com/ldevillez/yml2gantt/blob/main/examples/roadmap.yml) | Month scale, dates only, colored milestones on bars, a paused task, no "today" line |
| [`house.yml`](https://github.com/ldevillez/yml2gantt/blob/main/examples/house.yml) | Trimester scale with `{q}`, percentage milestones, a seasonal task as segments |
| [`course.yml`](https://github.com/ldevillez/yml2gantt/blob/main/examples/course.yml) | Abstract scale in weeks, `label_every`, fractional positions |
| [`workpackages.yml`](https://github.com/ldevillez/yml2gantt/blob/main/examples/workpackages.yml) | Abstract scale in quarters, a research project in work packages, partners in the bars, many milestones and segments |
| [`from_python.py`](https://github.com/ldevillez/yml2gantt/blob/main/examples/from_python.py) | Building a chart from Python |

**sprint.yml**: day scale

![Sprint example](https://raw.githubusercontent.com/ldevillez/yml2gantt/main/docs/images/sprint.png)

**house.yml**: trimester scale

![House building example](https://raw.githubusercontent.com/ldevillez/yml2gantt/main/docs/images/house.png)

**course.yml**: abstract scale

![Course example](https://raw.githubusercontent.com/ldevillez/yml2gantt/main/docs/images/course.png)

**workpackages.yml**: abstract scale, work packages

![Work packages example](https://raw.githubusercontent.com/ldevillez/yml2gantt/main/docs/images/workpackages.png)

## Python API

### Building a chart

```python
from yml2gantt import Gantt

g = Gantt(start="2026-01-01", end="2027-01-01", scale="trimester",
          title="Board game launch")

g.add_task("Market research", start=0, duration="6w", label="Alice")

design = g.add_task("Game design", start="2026-02-15")
design.add_subtask("Rules", duration="3w")
proto = design.add_subtask("Prototype", start="3w", duration=60)
proto.add_milestone("Demo", at="50%")

tests = g.add_task("Playtests", start="2026-06-01")
tests.add_segment(duration="3w")
tests.add_segment(start="8w", duration="2w", label="Retest")

g.add_task("Shipping", start="2026-12-15", milestone=True)

fig, ax = g.draw()
fig.savefig("plan.pdf")
```

| Call | Description |
|------|-------------|
| `Gantt(start=None, end=None, duration=None, scale="week", title=None, show_today=True, label_format=None, label_every=1, step=1, now=None, now_label=None)` | Same keys as the `gantt` section. |
| `g.add_task(name, start=0, duration=None, end=None, color=None, milestone=False, label=None)` | Adds a top-level task and returns it. |
| `task.add_subtask(...)` | Same arguments as `add_task`; `start` is relative to the parent. |
| `task.add_milestone(name, at="100%", color=None)` | Adds a milestone on the bar. |
| `task.add_segment(start=0, duration=None, end=None, color=None, label=None)` | Adds a piece of bar on the task's row. |
| `g.draw(ax=None, figsize=None, lighten=0.3)` | Draws and returns `(fig, ax)`. `lighten` sets how light the subtask colors are (0 = white, 1 = parent color). |
| `g.check()` | Returns the warnings (list of text), see [Errors and warnings](#errors-and-warnings). |

Wrong input raises `GanttError` (a subclass of `ValueError`) with a
message naming the task. `load_yaml` and `from_dict` list every problem
of the description in `err.issues`, each with its `message`, `where`
(e.g. `task 'A' > subtask 'B'`) and `line` in the file:

```python
from yml2gantt import GanttError, load_yaml

try:
    g = load_yaml("plan.yml")
except GanttError as err:
    for issue in err.issues:
        print(issue.line, issue.where, issue.message)
```

### Loading YAML from Python

```python
from yml2gantt import Gantt, load_yaml, from_dict

g = load_yaml("examples/project.yml")       # or Gantt.from_yaml(...)
g = from_dict({"gantt": {"start": 0, "duration": 10, "scale": "abstract"},
               "tasks": [{"name": "A", "duration": 4}]})   # or Gantt.from_dict(...)

# Edit it before drawing
g.add_task("Extra task", start=5, duration=2)
```

### Customizing the figure

`draw` returns plain matplotlib objects, so anything matplotlib can do
works afterwards:

```python
import matplotlib.pyplot as plt
from yml2gantt import load_yaml

plt.style.use("seaborn-v0_8-whitegrid")     # styles and the color cycle apply

fig, ax = load_yaml("examples/roadmap.yml").draw(figsize=(14, 6))
ax.set_xlabel("2026 - 2027")
ax.tick_params(axis="y", labelsize=11)
fig.savefig("roadmap.svg", bbox_inches="tight")
```

To place a gantt inside a larger figure, pass your own axes:

```python
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 10))
load_yaml("examples/sprint.yml").draw(ax=ax1)
load_yaml("examples/roadmap.yml").draw(ax=ax2)
```

## Limitations

- Subtasks go one level deep (a subtask cannot have subtasks).
- Text in a bar is not shortened: on a short bar, use a short `label`
  or `label: ""`.
- Milestone labels can cover the text of their bar: move the milestone
  (`at`) or shorten the bar `label`.
- Dated scales work with whole days (no hours).

## Development

```sh
git clone https://github.com/ldevillez/yml2gantt
cd yml2gantt
poetry install          # or: pip install -e . pytest
poetry run yml2gantt examples/minimal.yml
poetry run pytest       # tests in tests/
```

Project layout:

```
yml2gantt/
  cli.py          command line (yml2gantt, python -m yml2gantt)
  model.py        Gantt, Task, segment and milestone objects
  scale.py        time scales: dates → x positions, grid and labels
  io.py           loading from a dict or a .yml file
  plot.py         drawing with matplotlib
  colors.py       color helpers
  errors.py       GanttError and the checks of the values
tests/            tests (pytest)
examples/         example charts
docs/images/      pictures used in this README
```

### Releasing a new version

Releases are made by GitHub Actions
([`release.yml`](https://github.com/ldevillez/yml2gantt/blob/main/.github/workflows/release.yml))
when a version tag is pushed. It builds the package, publishes it on
PyPI and creates the GitHub release, with the changelog entry as notes.

```sh
poetry version minor        # or patch / major: updates pyproject.toml
# move the "Unreleased" notes of CHANGELOG.md under the new version
git commit -am "Release v$(poetry version -s)"
git tag "v$(poetry version -s)"
git push origin main --tags
```

The release stops if the tag does not match the version in
`pyproject.toml`.

## License

[MIT](https://github.com/ldevillez/yml2gantt/blob/main/LICENSE)
