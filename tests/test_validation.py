"""Checks of the input: every mistake gives a clear GanttError."""

import textwrap
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

from yml2gantt import Gantt, GanttError, from_dict, load_yaml  # noqa: E402
from yml2gantt.cli import main  # noqa: E402

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.yml"))
ABSTRACT = {"start": 0, "scale": "abstract"}
DATED = {"start": "2026-01-05"}


def errors(data):
    """Messages of the GanttError raised by ``from_dict(data)``."""
    with pytest.raises(GanttError) as info:
        from_dict(data)
    return [str(i) for i in info.value.issues]


def task_errors(*tasks, gantt=DATED):
    return errors({"gantt": gantt, "tasks": list(tasks)})


def write(tmp_path, text):
    path = tmp_path / "plan.yml"
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


# Examples ----------------------------------------------------------------

@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_load_draw_without_warning(path):
    gantt = load_yaml(path)
    assert gantt.check() == []
    gantt.draw()


# File structure -----------------------------------------------------------

def test_top_level_must_be_a_mapping():
    (msg,) = errors(["a", "b"])
    assert "expected a mapping" in msg and "'tasks' list" in msg


def test_unknown_section_suggests():
    msgs = errors({"gantt": ABSTRACT, "task": []})
    assert any("did you mean 'tasks'?" in m for m in msgs)


def test_missing_tasks():
    (msg,) = errors({"gantt": ABSTRACT})
    assert "no 'tasks' list" in msg


def test_task_must_be_a_mapping():
    (msg,) = task_errors("Write", gantt=ABSTRACT)
    assert "task #1" in msg and "{name: Write, duration: 3}" in msg


def test_list_keys_must_be_lists():
    (msg,) = task_errors({"name": "A", "duration": 1, "milestones": "Done"})
    assert "'milestones' must be a list" in msg


# Keys ---------------------------------------------------------------------

def test_unknown_key_suggests():
    (msg,) = task_errors({"name": "A", "durtion": 3})
    assert "task 'A'" in msg and "did you mean 'duration'?" in msg


def test_key_given_twice_case_insensitive():
    (msg,) = task_errors({"name": "A", "start": 1, "Start": 2, "duration": 1})
    assert "given twice" in msg


def test_task_key_means_name():
    msgs = task_errors({"name": "A", "task": "B", "duration": 1})
    assert "given twice" in msgs[0]


def test_empty_color_explains_hex_quotes():
    (msg,) = task_errors({"name": "A", "duration": 1, "color": None})
    assert "in quotes" in msg and "comment" in msg


def test_missing_name():
    (msg,) = task_errors({"duration": 1})
    assert "has no 'name'" in msg


def test_boolean_name_explains_yaml():
    (msg,) = task_errors({"name": False, "duration": 1})
    assert "booleans" in msg


def test_numeric_name_is_text():
    g = from_dict({"gantt": ABSTRACT,
                   "tasks": [{"name": 2026, "duration": 1}]})
    assert g.tasks[0].name == "2026"


def test_subtasks_one_level_deep():
    (msg,) = task_errors({"name": "A", "subtasks": [
        {"name": "B", "duration": 1, "subtasks": []}]})
    assert "task 'A' > subtask 'B'" in msg and "one level deep" in msg


# Gantt section ------------------------------------------------------------

@pytest.mark.parametrize("settings, expected", [
    ({"start": "2026-01-05", "scale": "wek"}, "did you mean 'week'?"),
    ({}, "'start' is missing"),
    ({"start": 0}, "needs a start date"),
    ({"start": "2026-13-01"}, "invalid 'start'"),
    ({"start": "2026-01-05", "label_every": 0}, "at least 1"),
    ({"start": "2026-01-05", "label_every": 1.5}, "whole number"),
    ({"start": 0, "scale": "abstract", "step": 0}, "greater than 0"),
    ({"start": 0, "scale": "abstract", "step": -1}, "greater than 0"),
    ({"start": "2026-01-05", "label_format": "{foo}"}, "unknown placeholder"),
    ({"start": "2026-01-05", "label_format": "{"}, "invalid 'label_format'"),
    ({"start": 0, "scale": "abstract", "label_format": "{date}"},
     "abstract scale does not have"),
    ({"start": "2026-01-05", "duration": "3m"}, "no month unit"),
    ({"start": "2026-01-05", "end": "2026-01-01"}, "must end after"),
    ({"start": "2026-01-05", "end": 3, "duration": 3}, "not both"),
    ({"start": "2026-01-05", "show_today": "yes"}, "true or false"),
    ({"start": "2026-01-05", "durration": 3}, "did you mean 'duration'?"),
])
def test_gantt_settings(settings, expected):
    msgs = errors({"gantt": settings, "tasks": [{"name": "A",
                                                   "duration": 1}]})
    assert any(expected in m for m in msgs), msgs
    assert all("'gantt' section" in m for m in msgs)


# Values -------------------------------------------------------------------

@pytest.mark.parametrize("task, expected", [
    ({"duration": "3x"}, "unknown unit 'x'"),
    ({"duration": "abc"}, "invalid 'duration'"),
    ({"duration": True}, "invalid 'duration'"),
    ({"duration": float("inf")}, "finite"),
    ({"start": "soon", "duration": 1}, "invalid 'start'"),
    ({"end": "2026-01-01"}, "ends (2026-01-01) before it starts"),
    ({"duration": 1, "end": 2}, "not both"),
    ({"duration": 1, "color": "blu"}, "did you mean 'blue'?"),
    ({"duration": 1, "milestone": 1}, "true or false"),
    ({"milestone": True, "duration": 3}, "point in time"),
    ({}, "has no length"),
])
def test_task_values(task, expected):
    msgs = task_errors({"name": "A", **task})
    assert any(expected in m for m in msgs), msgs


def test_abstract_scale_refuses_dates_and_units():
    msgs = task_errors({"name": "A", "duration": "2w"},
                       {"name": "B", "start": "2026-01-01", "duration": 1},
                       gantt=ABSTRACT)
    assert len(msgs) == 2
    assert all("only takes numbers" in m for m in msgs)


def test_all_field_errors_of_a_task_reported():
    msgs = task_errors({"name": "A", "duration": "3x", "color": "blu"})
    assert len(msgs) == 2


def test_misspelled_duration_gives_one_error():
    # Not a second "has no length" error caused by the first one.
    assert len(task_errors({"name": "A", "durtion": 3})) == 1


# Milestones and segments --------------------------------------------------

@pytest.mark.parametrize("marker, expected", [
    ({"name": "M", "at": "150%"}, "outside the bar"),
    ({"name": "M", "at": "x%"}, "invalid percentage"),
    ({"at": "50%"}, "has no 'name'"),
    ({"name": "M", "colour": "red"}, "did you mean 'color'?"),
])
def test_milestones(marker, expected):
    (msg,) = task_errors({"name": "A", "duration": 4, "milestones": [marker]})
    assert expected in msg and "task 'A' > milestone" in msg


@pytest.mark.parametrize("segments, expected", [
    ([{"start": 0, "duration": 3}, {"start": 2, "duration": 3}], "overlaps"),
    ([{"start": -1, "duration": 3}], "before its task"),
    ([{"start": 0}], "needs a 'duration' or an 'end'"),
    ([{"start": 0, "duration": 1, "end": 2}], "not both"),
    ([{"start": 3, "end": 1}], "ends"),
])
def test_segments(segments, expected):
    (msg,) = task_errors({"name": "A", "start": 2, "segments": segments},
                         gantt=ABSTRACT)
    assert expected in msg and "task 'A' > segment #" in msg


def test_milestone_row_cannot_have_children():
    (msg,) = task_errors({"name": "M", "milestone": True,
                          "subtasks": [{"name": "x"}]})
    assert "cannot have 'subtasks'" in msg


def test_several_errors_reported_together():
    msgs = task_errors({"name": "A", "durtion": 3},
                       {"name": "B", "duration": "3x"},
                       {"name": "C", "duration": 1, "color": "blu"})
    assert len(msgs) == 3


# YAML file ----------------------------------------------------------------

def test_errors_have_line_numbers(tmp_path):
    path = write(tmp_path, """\
        gantt:
          start: 2026-01-05
        tasks:
          - name: A
            duration: 3
          - name: B
            durtion: 3
        """)
    with pytest.raises(GanttError) as info:
        load_yaml(path)
    assert str(info.value).startswith("line 6, task 'B'")


def test_duplicate_yaml_key(tmp_path):
    import yaml
    path = write(tmp_path, """\
        gantt: {start: 0, scale: abstract}
        tasks:
          - name: A
            duration: 3
            duration: 4
        """)
    with pytest.raises(yaml.YAMLError, match="given twice"):
        load_yaml(path)


def test_empty_file(tmp_path):
    with pytest.raises(GanttError, match="empty"):
        load_yaml(write(tmp_path, ""))


# Warnings -----------------------------------------------------------------

def test_warnings():
    g = from_dict({"gantt": {**ABSTRACT, "duration": 5, "now": 9}, "tasks": [
        {"name": "A", "duration": 6, "milestones": [{"name": "m", "at": 7}]},
        {"name": "A", "start": 1, "duration": 1,
         "subtasks": [{"name": "s", "duration": 3}]},
    ]})
    text = "\n".join(g.check())
    for expected in ["ends (6) after the chart", "milestone 'm'",
                     "go outside their task", "'now' (9)", "same color"]:
        assert expected in text


# Python API ---------------------------------------------------------------

def test_api_errors_name_the_task():
    g = Gantt("2026-01-05")
    with pytest.raises(GanttError, match="^task 'B': invalid 'duration'"):
        g.add_task("B", duration="3x")
    t = g.add_task("A", start=2)
    with pytest.raises(GanttError, match="^task 'A' > segment #1"):
        t.add_segment(start=-1, duration=2)


def test_draw_task_without_length():
    g = Gantt(0, scale="abstract")
    g.add_task("Z")
    with pytest.raises(GanttError, match="has no length"):
        g.draw()


def test_gantt_error_is_a_value_error():
    assert issubclass(GanttError, ValueError)


# Command line -------------------------------------------------------------

def run(capsys, *argv):
    with pytest.raises(SystemExit) as info:
        main([*map(str, argv), "--no-show"])
    return info.value.code, capsys.readouterr().err


def test_cli_reports_errors(tmp_path, capsys):
    path = write(tmp_path, "gantt: {start: 2026-01-05}\n"
                           "tasks: [{name: A, durtion: 3}]\n")
    code, err = run(capsys, path, "-o", tmp_path / "out.png")
    assert code == 1
    assert "error in" in err and "did you mean 'duration'?" in err
    assert "Traceback" not in err


@pytest.mark.parametrize("output, expected", [
    ("out.pnj", "did you mean 'png'?"),
    ("out", "no extension"),
    ("missing/out.png", "does not exist"),
])
def test_cli_checks_output(tmp_path, capsys, output, expected):
    path = write(tmp_path, "gantt: {start: 0, scale: abstract}\n"
                           "tasks: [{name: A, duration: 3}]\n")
    code, err = run(capsys, path, "-o", tmp_path / output)
    assert code == 1 and expected in err


def test_cli_missing_file(tmp_path, capsys):
    code, err = run(capsys, tmp_path / "nope.yml", "-o", tmp_path / "a.png")
    assert code == 1 and "no file" in err


def test_cli_yaml_syntax_error(tmp_path, capsys):
    path = write(tmp_path, "gantt:\n\tstart: 2026-01-05\n")
    code, err = run(capsys, path, "-o", tmp_path / "a.png")
    assert code == 1 and "line 2" in err and "tabs" in err


def test_cli_prints_warnings(tmp_path, capsys):
    path = write(tmp_path, "gantt: {start: 0, scale: abstract, duration: 2}\n"
                           "tasks: [{name: A, duration: 3}]\n")
    out = tmp_path / "a.png"
    main([str(path), "-o", str(out), "--no-show"])
    assert out.exists()
    assert "warning: task 'A' ends (3) after the chart (2)" in \
        capsys.readouterr().err
