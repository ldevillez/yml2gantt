"""Gantt and task objects."""

import datetime as dt
from dataclasses import dataclass, field

import matplotlib.colors as mc

from .errors import (GanttError, check_bool, check_text, describe,
                     did_you_mean, located)
from .scale import Scale


def check_color(color, what="'color'"):
    """Check a matplotlib color (``None`` is accepted: default color)."""
    if color is None:
        return None
    if isinstance(color, str) and mc.is_color_like(color):
        return color
    if isinstance(color, (list, tuple)) and mc.is_color_like(tuple(color)):
        return tuple(color)
    hint = (did_you_mean(color, mc.get_named_colors_mapping())
            if isinstance(color, str) else "")
    raise GanttError(
        f"invalid {what} {describe(color)}{hint}: use a matplotlib color "
        f"name ('tab:red', 'lightgrey') or a hex code in quotes "
        f"(\"#3366cc\")")


@dataclass
class Marker:
    """A milestone drawn on the bar of a task.

    Parameters
    ----------
    name : str
        Label next to the diamond.
    task : Task
        Task whose bar holds the milestone.
    fraction : float, optional
        Position as a fraction of the bar (0 = start, 1 = end).
    x : float, optional
        Fixed position on the x axis. Used when ``fraction`` is ``None``.
    color : str, optional
        Matplotlib color. Default: black.
    """

    name: str
    task: "Task" = field(repr=False, compare=False)
    fraction: float = None
    x: float = None
    color: str = None

    @property
    def position(self):
        """float: Position on the x axis."""
        if self.fraction is not None:
            return self.task.start + self.fraction * self.task.length
        return self.x


@dataclass
class Segment:
    """A piece of the bar of a task, when a task has several.

    Parameters
    ----------
    start : float
        Start position on the x axis.
    duration : float
        Length on the x axis.
    color : str, optional
        Matplotlib color. Default: color of the task.
    label : str, optional
        Text written in the segment. Default: text of the task.
    """

    start: float
    duration: float
    color: str = None
    label: str = None

    @property
    def end(self):
        """float: End position of the segment."""
        return self.start + self.duration


def _parse_percent(value):
    """``"50%"`` -> ``0.5``, ``None`` for anything else."""
    if isinstance(value, str) and value.strip().endswith("%"):
        try:
            percent = float(value.strip()[:-1])
        except ValueError:
            raise GanttError(f"invalid percentage {value!r}: write it as "
                             f"\"50%\"") from None
        if not 0 <= percent <= 100:
            raise GanttError(f"percentage {value!r} is outside the bar: use "
                             f"0% to 100%, or a date or an offset")
        return percent / 100
    return None


@dataclass
class Task:
    """A bar of the gantt.

    Parameters
    ----------
    name : str
        Label of the task.
    start : float
        Start position on the x axis.
    duration : float, optional
        Length on the x axis. ``None`` spans the subtasks.
    color : str, optional
        Matplotlib color. Default: next color of the cycle.
    subtasks : list of Task
        Children of the task.
    milestone : bool, optional
        Draw a point in time (a diamond) at ``start`` instead of a bar.
    milestones : list of Marker
        Milestones drawn on the bar, see `add_milestone`.
    label : str, optional
        Text written in the bar (next to the diamond for a milestone).
        Default: ``name``. ``""`` leaves the bar empty.
    segments : list of Segment
        Pieces of bar on the row of the task, see `add_segment`.
    """

    name: str
    start: float
    duration: float = None
    color: str = None
    subtasks: list = field(default_factory=list)
    milestone: bool = False
    milestones: list = field(default_factory=list)
    label: str = None
    segments: list = field(default_factory=list)
    _gantt: "Gantt" = field(default=None, repr=False, compare=False)

    @property
    def end(self):
        """float: End position of the task."""
        if self.milestone:
            return self.start
        if self.duration is not None:
            return self.start + self.duration
        if self.segments:
            return max(s.end for s in self.segments)
        if not self.subtasks:
            raise GanttError(
                f"task {self.name!r} has no length: give 'duration' or "
                f"'end', or add 'subtasks' or 'segments' (or "
                f"'milestone: true' for a single point in time)")
        return max(st.end for st in self.subtasks)

    @property
    def text(self):
        """str: Text drawn on the chart: ``label``, or ``name``."""
        return self.name if self.label is None else str(self.label)

    @property
    def length(self):
        """float: Drawn length of the task."""
        return self.end - self.start

    def add_milestone(self, name, at="100%", color=None):
        """Add a milestone on the bar of the task.

        Parameters
        ----------
        name : str
            Label next to the diamond.
        at : str, float or date, optional
            Percentage of the bar (``"50%"``, default ``"100%"``: the end),
            or offset from the task start (``4``, ``"2w"``), or date.
        color : str, optional
            Matplotlib color. Default: black.

        Returns
        -------
        Marker
            The new milestone.
        """
        with located(f"task {self.name!r} > milestone {name!r}"):
            return self._add_milestone(name, at, color)

    def _add_milestone(self, name, at, color):
        if self.milestone:
            raise GanttError("a milestone row cannot have 'milestones' on it")
        name = check_text(name, "the milestone 'name'", required=True)
        color = check_color(color)
        fraction = _parse_percent(at)
        x = None if fraction is not None else self._gantt.scale.to_x(
            at, self.start, what="'at'")
        marker = Marker(name, self, fraction, x, color)
        self.milestones.append(marker)
        return marker

    def add_segment(self, start=0, duration=None, end=None, color=None,
                    label=None):
        """Add a piece of bar on the row of the task.

        The task then spans from its start to the end of its last segment
        (for its parent and for percentage milestones).

        Parameters
        ----------
        start : float, date or str, optional
            Date, or offset from the task start.
        duration : float or str, optional
            Length (``3``, ``"3d"``, ``"2w"``).
        end : float, date or str, optional
            Date, or offset from the task start. Replaces ``duration``.
        color : str, optional
            Matplotlib color. Default: color of the task.
        label : str, optional
            Text written in the segment. Default: text of the task.

        Returns
        -------
        Segment
            The new segment.
        """
        with located(f"task {self.name!r} > segment "
                     f"#{len(self.segments) + 1}"):
            return self._add_segment(start, duration, end, color, label)

    def _add_segment(self, start, duration, end, color, label):
        if self.milestone:
            raise GanttError("a milestone row cannot have 'segments'")
        if self.duration is not None:
            raise GanttError(
                "the task has 'duration'/'end' and 'segments': give one or "
                "the other (with segments, the task ends with its last "
                "segment)")
        if self.subtasks:
            raise GanttError(
                "a task cannot have both 'segments' and 'subtasks'")
        if duration is None and end is None:
            raise GanttError("a segment needs a 'duration' or an 'end'")
        if duration is not None and end is not None:
            raise GanttError("give the segment a 'duration' or an 'end', "
                             "not both")
        color = check_color(color)
        label = check_text(label, "'label'")
        scale = self._gantt.scale
        x0 = scale.to_x(start, self.start, what="'start'")
        length = (scale.to_span(duration, what="'duration'") if end is None
                  else scale.to_x(end, self.start, what="'end'") - x0)
        if length < 0:
            raise GanttError(
                f"the segment ends ({scale.format_x(x0 + length)}) before it "
                f"starts ({scale.format_x(x0)})")
        if x0 < self.start:
            raise GanttError(
                f"the segment starts ({scale.format_x(x0)}) before its task "
                f"({scale.format_x(self.start)}): segment starts are offsets "
                f"from the task start, or dates")
        for other in self.segments:
            if x0 < other.end and other.start < x0 + length:
                raise GanttError(
                    f"the segment {scale.format_x(x0)} → "
                    f"{scale.format_x(x0 + length)} overlaps the segment "
                    f"{scale.format_x(other.start)} → "
                    f"{scale.format_x(other.end)}")
        seg = Segment(x0, length, color, label)
        self.segments.append(seg)
        return seg

    def add_subtask(self, name, start=0, duration=None, end=None, color=None,
                    milestone=False, label=None):
        """Add a subtask.

        Parameters
        ----------
        name : str
            Label of the subtask.
        start : float, date or str, optional
            Date, or offset from the parent start.
        duration : float or str, optional
            Length (``3``, ``"3d"``, ``"2w"``).
        end : float, date or str, optional
            Date, or offset from the parent start. Replaces ``duration``.
        color : str, optional
            Matplotlib color. Default: lighter parent color (parent color
            for a milestone).
        milestone : bool, optional
            Make it a milestone at ``start``.
        label : str, optional
            Text written in the bar instead of ``name``.

        Returns
        -------
        Task
            The new subtask.
        """
        with located(f"task {self.name!r} > subtask {name!r}"):
            if self.milestone:
                raise GanttError("a milestone row cannot have 'subtasks'")
            if self.segments:
                raise GanttError(
                    "a task cannot have both 'segments' and 'subtasks'")
            st = self._gantt._make_task(name, start, duration, end, color,
                                        origin=self.start,
                                        milestone=milestone, label=label)
        self.subtasks.append(st)
        return st


class Gantt:
    """A gantt chart: a time scale and a list of tasks.

    Parameters
    ----------
    start : date, str or float
        Start of the gantt: a date, required on dated scales, or a number
        for ``"abstract"`` (default ``0``).
    end : date, str or float, optional
        End of the gantt (exclusive). Give ``end`` or ``duration``, or
        neither: the gantt then ends after its last task, at the end of
        that period (computed when drawing).
    duration : float or str, optional
        Length of the gantt (``90``, ``"13w"``).
    scale : {"day", "week", "month", "trimester", "abstract"}
        Decomposition of the time axis.
    title : str, optional
        Title of the chart.
    show_today : bool, optional
        Draw a line at today's date (dated scales only). Ignored when
        ``now`` is given.

    Raises
    ------
    GanttError
        On invalid settings. Tasks are checked when they are added.
    now : float, date or str, optional
        Current position in the project (date, or offset from the start):
        draws the "we are here" line there instead of at today's date.
        Works on every scale.
    now_label : str, optional
        Text above the line. Default: ``"Now"`` with ``now``, else
        ``"Today"``. ``""`` for no text.
    label_format : str, optional
        Period label, see `Scale`.
    label_every : int, optional
        Label one period out of ``label_every``.
    step : float, optional
        Period size for ``"abstract"``.

    Examples
    --------
    >>> g = Gantt("2025-09-21", duration="13w", scale="week")
    >>> t = g.add_task("Writing", start=7)
    >>> t.add_subtask("Draft", duration="2w")
    >>> t.add_milestone("Draft sent", at="50%")
    >>> g.add_task("Submission", start="2025-11-30", milestone=True)
    """

    def __init__(self, start=None, end=None, duration=None, scale="week",
                 title=None, show_today=True, label_format=None,
                 label_every=1, step=1, now=None, now_label=None):
        self.scale = Scale(scale, start, end=end, duration=duration,
                           label_format=label_format,
                           label_every=label_every, step=step)
        self.title = check_text(title, "'title'")
        self.show_today = check_bool(show_today, "'show_today'")
        self.now = None if now is None else self.scale.to_x(now, what="'now'")
        self.now_label = check_text(now_label, "'now_label'")
        self.tasks = []

    def now_line(self):
        """Position and text of the "we are here" line.

        Returns
        -------
        tuple or None
            ``(x, label)``, or ``None`` when no line is drawn (no ``now``,
            and today is hidden, abstract or outside the gantt).
        """
        self.fit_scale()
        if self.now is not None:
            x, default = self.now, "Now"
        elif self.show_today and not self.scale.abstract:
            x, default = self.scale.to_x(dt.date.today()), "Today"
        else:
            return None
        if not 0 <= x <= self.scale.length:
            return None
        return x, default if self.now_label is None else str(self.now_label)

    def _make_task(self, name, start, duration, end, color, origin=0.0,
                   milestone=False, label=None):
        # Check every field, to report all the problems of the task at once.
        issues = []

        def attempt(check, *args, **kwargs):
            try:
                return check(*args, **kwargs)
            except GanttError as err:
                issues.extend(err.issues)
                return None

        scale = self.scale
        name = attempt(check_text, name, "'name'", required=True)
        label = attempt(check_text, label, "'label'")
        color = attempt(check_color, color)
        milestone = attempt(check_bool, milestone, "'milestone'")
        if milestone and (duration is not None or end is not None):
            raise GanttError("a milestone row is a point in time: it only "
                             "takes a 'start', not a 'duration' or 'end'")
        if duration is not None and end is not None:
            raise GanttError("give 'duration' or 'end', not both")
        x0 = attempt(scale.to_x, start, origin, what="'start'")
        if end is not None:
            x1 = attempt(scale.to_x, end, origin, what="'end'")
            duration = None if None in (x0, x1) else x1 - x0
        elif duration is not None:
            duration = attempt(scale.to_span, duration, what="'duration'")
        if issues:
            raise GanttError(issues)
        if duration is not None and duration < 0:
            raise GanttError(
                f"the task ends ({scale.format_x(x0 + duration)}) "
                f"before it starts ({scale.format_x(x0)})")
        return Task(name, x0, duration, color, milestone=bool(milestone),
                    label=label, _gantt=self)

    def add_task(self, name, start=0, duration=None, end=None, color=None,
                 milestone=False, label=None):
        """Add a top-level task.

        Parameters
        ----------
        name : str
            Label of the task.
        start : float, date or str, optional
            Date, or offset from the gantt start.
        duration : float or str, optional
            Length. Leave empty to span the subtasks.
        end : float, date or str, optional
            End of the task. Replaces ``duration``.
        color : str, optional
            Matplotlib color.
        milestone : bool, optional
            Make it a milestone at ``start`` (no duration, no subtasks).
        label : str, optional
            Text written in the bar instead of ``name`` (``""``: none).

        Returns
        -------
        Task
            The new task, use `Task.add_subtask` to fill it.
        """
        with located(f"task {name!r}"):
            task = self._make_task(name, start, duration, end, color,
                                   milestone=milestone, label=label)
        self.tasks.append(task)
        return task

    def fit_scale(self):
        """Set the end of the gantt from its tasks.

        Only when neither ``end`` nor ``duration`` was given. Bars and
        milestones on bars count up to their end; milestone rows get
        room after them. Called by `draw`.
        """
        if not self.scale.auto:
            return
        ends, points = [], []
        for task in self.tasks:
            for t in (task, *task.subtasks):
                if t.milestone:
                    points.append(t.start)
                else:
                    ends.append(t.end)
                    ends.extend(m.position for m in t.milestones)
        if not ends and not points:
            raise GanttError("the chart has no task to compute its end")
        self.scale.fit(max(ends, default=None), max(points, default=None))

    def check(self):
        """Look for likely mistakes that do not stop the drawing.

        Returns
        -------
        list of str
            Warnings, e.g. a task cut by the chart end.
        """
        self.fit_scale()
        scale, out = self.scale, []
        length = scale.length
        fmt = scale.format_x
        for task in self.tasks:
            for t in (task, *task.subtasks):
                kind = "subtask" if t is not task else "task"
                if t.start < 0:
                    out.append(f"{kind} {t.name!r} starts ({fmt(t.start)}) "
                               f"before the chart ({fmt(0)}): it is cut")
                if t.end > length:
                    out.append(f"{kind} {t.name!r} ends ({fmt(t.end)}) after "
                               f"the chart ({fmt(length)}): it is cut")
                for m in t.milestones:
                    if not 0 <= m.position <= length:
                        out.append(f"milestone {m.name!r} of {t.name!r} "
                                   f"({fmt(m.position)}) is outside the "
                                   f"chart: it is not drawn")
            if task.subtasks and task.duration is not None:
                late = [st.name for st in task.subtasks
                        if st.end > task.end or st.start < task.start]
                if late:
                    out.append(f"subtasks {late} go outside their task "
                               f"{task.name!r} ({fmt(task.start)} → "
                               f"{fmt(task.end)})")
        if self.now is not None and not 0 <= self.now <= length:
            out.append(f"'now' ({fmt(self.now)}) is outside the chart: the "
                       f"line is not drawn")
        names = [t.name for t in self.tasks if t.color is None]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            out.append(f"several tasks are named {dup}: they get the same "
                       f"color")
        return out

    def draw(self, ax=None, **kwargs):
        """Draw the gantt with matplotlib.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes to draw on. Default: a new figure.
        **kwargs
            ``figsize`` and ``lighten``, see `yml2gantt.plot.draw`.

        Returns
        -------
        fig : matplotlib.figure.Figure
        ax : matplotlib.axes.Axes
        """
        from .plot import draw
        return draw(self, ax=ax, **kwargs)

    @classmethod
    def from_dict(cls, data):
        """Build a gantt from a dict, see `yml2gantt.io.from_dict`."""
        from .io import from_dict
        return from_dict(data)

    @classmethod
    def from_yaml(cls, path):
        """Build a gantt from a ``.yml`` file, see `yml2gantt.io.load_yaml`."""
        from .io import load_yaml
        return load_yaml(path)
