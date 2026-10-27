"""Time scales: map dates to x positions and build the grid."""

import datetime as dt
import math
import string
from numbers import Real

from .errors import GanttError, check_number, check_text, describe, did_you_mean

#: Supported decompositions.
SCALES = ("day", "week", "month", "trimester", "abstract")

DEFAULT_LABELS = {
    "day": "{date:%b %d}",
    "week": "W{date:%V}",
    "month": "{date:%b %Y}",
    "trimester": "Q{q} {date:%Y}",
    "abstract": "{n}",
}

# Placeholders that label_format can use.
_PLACEHOLDERS = {"date", "q", "n"}

_DATE_HINT = ("dates are written YYYY-MM-DD (2026-01-05), or as ISO week "
              "dates YYYY-Www-D in quotes (\"2026-W02-1\")")
_SPAN_HINT = ("use a number of days (3, 2.5), or text such as \"3d\" or "
              "\"2w\"")

# Finer decomposition used for the light grid lines.
_MINOR = {"day": None, "week": "day", "month": "week", "trimester": "month"}

_UNITS = {"d": 1, "w": 7}


def to_date(value, what="date"):
    """Parse a date.

    Parameters
    ----------
    value : datetime.date, datetime.datetime or str
        Date, or ISO string such as ``"2025-09-21"`` or ``"2025-W38-7"``.
    what : str, optional
        Name of the value, for error messages.

    Returns
    -------
    datetime.date
    """
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value.strip())
        except ValueError as err:
            reason = "" if "Invalid isoformat" in str(err) else f" ({err})"
            raise GanttError(f"invalid {what} {value!r}{reason}: "
                             f"{_DATE_HINT}") from None
    raise GanttError(f"{what} must be a date, got {describe(value)}: "
                     f"{_DATE_HINT}")


def _is_span(value):
    """True for strings such as ``"3d"`` or ``"2w"``."""
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip().lower()
    try:
        float(text[:-1])
    except ValueError:
        return False
    return text[-1] in _UNITS


def _period_start(kind, d):
    if kind == "week":
        return d - dt.timedelta(days=d.weekday())
    if kind == "month":
        return d.replace(day=1)
    if kind == "trimester":
        return d.replace(month=3 * ((d.month - 1) // 3) + 1, day=1)
    return d


def _next_period(kind, d):
    if kind == "day":
        return d + dt.timedelta(days=1)
    if kind == "week":
        return d + dt.timedelta(days=7)
    months = 1 if kind == "month" else 3
    m = d.month - 1 + months
    return d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1)


class Scale:
    """Time axis of a gantt.

    Parameters
    ----------
    kind : str
        One of ``SCALES``.
    start : date, str or float
        Start of the gantt (a number for ``"abstract"``).
    end : date, str or float, optional
        End of the gantt (exclusive). Give ``end``, ``duration`` or
        neither: the length is then set later by `fit`.
    duration : float or str, optional
        Length of the gantt, in days (``"abstract"``: in units).
    label_format : str, optional
        Period label, formatted with ``date``, ``q`` (quarter) and ``n``
        (period index, from 1).
    label_every : int, optional
        Label only one period out of ``label_every``.
    step : float, optional
        Period size for ``"abstract"``.
    """

    def __init__(self, kind, start, end=None, duration=None,
                 label_format=None, label_every=1, step=1):
        if not isinstance(kind, str) or kind.strip().lower() not in SCALES:
            hint = did_you_mean(kind, SCALES) if isinstance(kind, str) else ""
            raise GanttError(f"unknown scale {kind!r}{hint}: use one of "
                             f"{', '.join(SCALES)}")
        if end is not None and duration is not None:
            raise GanttError("give 'end' or 'duration' for the chart, not both")
        self.kind = kind.strip().lower()
        self.step = check_number(step, "'step'", minimum=0)
        self.label_every = check_number(label_every, "'label_every'",
                                        minimum=1, integer=True)
        self.label_format = (DEFAULT_LABELS[self.kind] if label_format is None
                             else check_text(label_format, "'label_format'"))
        self._check_label_format()

        if self.abstract:
            if start is None:
                start = 0
            if isinstance(start, (dt.date, str)):
                raise GanttError(
                    f"the abstract scale starts at a number, got "
                    f"{describe(start)}: use 'start: 0', or a dated scale "
                    f"(day, week, month, trimester) for calendar dates")
            self.start = float(check_number(start, "'start'"))
        else:
            if start is None:
                raise GanttError(
                    f"'start' is missing: the {self.kind} scale needs a start "
                    f"date such as 2026-01-05 (or use 'scale: abstract' for "
                    f"numbered periods 1, 2, 3…)")
            if isinstance(start, Real) and not isinstance(start, bool):
                raise GanttError(
                    f"the {self.kind} scale needs a start date such as "
                    f"2026-01-05, got {describe(start)} (use 'scale: "
                    f"abstract' for numbered periods 1, 2, 3…)")
            self.start = to_date(start, "'start'")
        #: True when the length comes from the tasks (see `fit`).
        self.auto = end is None and duration is None
        self.length = None
        if not self.auto:
            self.length = (self.to_x(end, what="'end'") if duration is None
                           else self.to_span(duration, what="'duration'"))
            if self.length <= 0:
                given = (f"'end' {self.format_x(self.length)}"
                         if duration is None else f"'duration' {duration!r}")
                raise GanttError(f"the chart must end after its start, but "
                                 f"{given} is not after the start "
                                 f"{self.format_x(0)}")

    def _check_label_format(self):
        allowed = {"n"} if self.abstract else _PLACEHOLDERS
        try:
            fields = [f for _, f, _, _ in string.Formatter().parse(
                self.label_format) if f is not None]
        except ValueError as err:
            raise GanttError(f"invalid 'label_format' {self.label_format!r}: "
                             f"{err} (write a literal brace as {{{{ or }}}})"
                             ) from None
        for f in fields:
            root = f.split(".")[0].split("[")[0]
            if root not in allowed:
                if root in _PLACEHOLDERS:
                    raise GanttError(
                        f"'label_format' uses {{{root}}}, which the abstract "
                        f"scale does not have: use {{n}} (period number)")
                shown = "{}" if not root else f"{{{root}}}"
                raise GanttError(
                    f"unknown placeholder {shown} in 'label_format' "
                    f"{self.label_format!r}{did_you_mean(root, allowed)}: use "
                    + ", ".join(f"{{{p}}}" for p in sorted(allowed)))
        try:
            self._label(1, None if self.abstract else dt.date(2026, 1, 5))
        except (ValueError, TypeError, AttributeError) as err:
            raise GanttError(f"invalid 'label_format' {self.label_format!r}: "
                             f"{err}") from None

    def fit(self, last_end=None, last_point=None):
        """Set the length so that the axis covers the content.

        The axis stops at the first period boundary at or after
        ``last_end``, and strictly after ``last_point`` (so a milestone
        is not drawn on the border).

        Parameters
        ----------
        last_end : float, optional
            End of the last bar.
        last_point : float, optional
            Position of the last milestone row.
        """
        length = 0.0
        if last_end is not None:
            length = self._boundary(last_end, strict=False)
        if last_point is not None:
            length = max(length, self._boundary(last_point, strict=True))
        if length <= 0:
            raise GanttError(
                f"every task is before the chart start {self.format_x(0)}: "
                f"move the start earlier, or the tasks later")
        self.length = length

    def _boundary(self, x, strict):
        """First period boundary at or after ``x`` (after, if strict)."""
        x = round(x, 9)  # ignore float noise such as 7.000000001
        if self.abstract:
            k = x / self.step
            k = math.floor(k) + 1 if strict else math.ceil(k)
            return float(k * self.step)
        p = _period_start(self.kind, self.start)
        while self.to_x(p) < x or (strict and self.to_x(p) == x):
            p = _next_period(self.kind, p)
        return self.to_x(p)

    @property
    def abstract(self):
        """bool: True if the scale has no calendar dates."""
        return self.kind == "abstract"

    @property
    def end(self):
        """date or float: End of the gantt (exclusive)."""
        if self.abstract:
            return self.start + self.length
        return self.start + dt.timedelta(days=self.length)

    def to_x(self, value, origin=0.0, what="position"):
        """Convert a time to an x position.

        Parameters
        ----------
        value : float, date or str
            Offset from ``origin`` (``3``, ``"2w"``) or date.
        origin : float, optional
            Position that offsets are relative to.
        what : str, optional
            Name of the value, for error messages.

        Returns
        -------
        float
            Days (or units) since the gantt start.
        """
        if value is None:
            raise GanttError(f"{what} is empty")
        if isinstance(value, bool):
            raise GanttError(f"{what} must be a date or an offset, got "
                             f"{describe(value)}")
        if isinstance(value, Real) or _is_span(value):
            return origin + self.to_span(value, what)
        if self.abstract:
            raise GanttError(f"{what}: the abstract scale only takes numbers, "
                             f"got {describe(value)}")
        if isinstance(value, str):
            try:
                date = dt.date.fromisoformat(value.strip())
            except ValueError:
                raise GanttError(
                    f"invalid {what} {value!r}: give a date (YYYY-MM-DD, or "
                    f"\"YYYY-Www-D\" in quotes) or an offset (3, \"3d\", "
                    f"\"2w\")") from None
            return float((date - self.start).days)
        return float((to_date(value, what) - self.start).days)

    def to_span(self, value, what="duration"):
        """Convert a duration to a length on the x axis.

        Parameters
        ----------
        value : float or str
            Number, or string such as ``"3d"`` or ``"2w"`` (dated scales).
        what : str, optional
            Name of the value, for error messages.

        Returns
        -------
        float
        """
        if value is None:
            raise GanttError(f"{what} is empty")
        if isinstance(value, Real) and not isinstance(value, bool):
            return float(check_number(value, what))
        if isinstance(value, str):
            if self.abstract:
                raise GanttError(f"{what}: the abstract scale only takes "
                                 f"numbers, got {describe(value)}")
            text = value.strip().lower()
            if _is_span(text):
                return float(check_number(float(text[:-1]), what)
                             * _UNITS[text[-1]])
            if text[-1:].isalpha() and text[-1] not in _UNITS:
                raise GanttError(
                    f"invalid {what} {value!r}: unknown unit {text[-1]!r}, "
                    f"use 'd' (days) or 'w' (weeks). There is no month unit, "
                    f"as months have different lengths: use dates instead")
            raise GanttError(f"invalid {what} {value!r}: {_SPAN_HINT}")
        raise GanttError(f"invalid {what}: expected a duration, got "
                         f"{describe(value)}: {_SPAN_HINT}")

    def format_x(self, x):
        """Readable text for position ``x``: a date, or a number."""
        if self.abstract:
            return f"{self.start + x:g}"
        return (self.start + dt.timedelta(days=x)).isoformat()

    def date_at(self, x):
        """Date at position ``x`` (``None`` for abstract scales)."""
        if self.abstract:
            return None
        return self.start + dt.timedelta(days=x)

    def _date_periods(self, kind):
        p = _period_start(kind, self.start)
        while p < self.end:
            nxt = _next_period(kind, p)
            yield p, max(p, self.start), min(nxt, self.end)
            p = nxt

    def periods(self):
        """Major periods of the axis.

        Returns
        -------
        list of tuple
            ``(x0, x1, label)`` for each period.
        """
        out = []
        if self.abstract:
            n, x = 1, 0.0
            while x < self.length:
                x1 = min(x + self.step, self.length)
                label = self._label(n, None) if x1 - x >= self.step / 2 else ""
                out.append((x, x1, label))
                n, x = n + 1, x1
            return out
        for n, (p, a, b) in enumerate(self._date_periods(self.kind), start=1):
            # Periods cut to less than half are left unlabelled.
            full = (_next_period(self.kind, p) - p).days
            label = self._label(n, p) if (b - a).days >= full / 2 else ""
            out.append((self.to_x(a), self.to_x(b), label))
        return out

    def minor_ticks(self):
        """Positions of the light grid lines.

        Returns
        -------
        list of float
        """
        kind = None if self.abstract else _MINOR[self.kind]
        if kind is None:
            return []
        return [self.to_x(a) for _, a, _ in self._date_periods(kind)
                if self.start < a]

    def _label(self, n, date):
        if (n - 1) % self.label_every:
            return ""
        q = (date.month - 1) // 3 + 1 if date else None
        return self.label_format.format(date=date, q=q, n=n)
