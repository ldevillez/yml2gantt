"""Time scales: map dates to x positions and build the grid."""

import datetime as dt
import math
from numbers import Real

#: Supported decompositions.
SCALES = ("day", "week", "month", "trimester", "abstract")

DEFAULT_LABELS = {
    "day": "{date:%b %d}",
    "week": "W{date:%V}",
    "month": "{date:%b %Y}",
    "trimester": "Q{q} {date:%Y}",
    "abstract": "{n}",
}

# Finer decomposition used for the light grid lines.
_MINOR = {"day": None, "week": "day", "month": "week", "trimester": "month"}

_UNITS = {"d": 1, "w": 7}


def to_date(value):
    """Parse a date.

    Parameters
    ----------
    value : datetime.date, datetime.datetime or str
        Date, or ISO string such as ``"2025-09-21"`` or ``"2025-W38-7"``.

    Returns
    -------
    datetime.date
    """
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    raise TypeError(f"Cannot convert {value!r} to a date")


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
        if kind not in SCALES:
            raise ValueError(f"Unknown scale {kind!r}, use one of {SCALES}")
        if end is not None and duration is not None:
            raise ValueError("Give 'end' or 'duration', not both")
        self.kind = kind
        self.label_format = label_format or DEFAULT_LABELS[kind]
        self.label_every = int(label_every)
        self.step = step

        if self.abstract:
            self.start = float(start)
        else:
            self.start = to_date(start)
        #: True when the length comes from the tasks (see `fit`).
        self.auto = end is None and duration is None
        self.length = None
        if not self.auto:
            self.length = (self.to_x(end) if duration is None
                           else self.to_span(duration))
            if self.length <= 0:
                raise ValueError("The gantt must end after its start")

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
            raise ValueError("The gantt must end after its start: "
                             "all tasks are before the start")
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

    def to_x(self, value, origin=0.0):
        """Convert a time to an x position.

        Parameters
        ----------
        value : float, date or str
            Offset from ``origin`` (``3``, ``"2w"``) or date.
        origin : float, optional
            Position that offsets are relative to.

        Returns
        -------
        float
            Days (or units) since the gantt start.
        """
        if isinstance(value, Real) or _is_span(value):
            return origin + self.to_span(value)
        if self.abstract:
            raise TypeError(f"Abstract scale only accepts numbers, got {value!r}")
        return float((to_date(value) - self.start).days)

    def to_span(self, value):
        """Convert a duration to a length on the x axis.

        Parameters
        ----------
        value : float or str
            Number, or string such as ``"3d"`` or ``"2w"`` (dated scales).

        Returns
        -------
        float
        """
        if isinstance(value, Real):
            return float(value)
        if isinstance(value, str) and not self.abstract:
            text = value.strip().lower()
            if text and text[-1] in _UNITS:
                return float(text[:-1]) * _UNITS[text[-1]]
        raise ValueError(f"Invalid duration {value!r}")

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
