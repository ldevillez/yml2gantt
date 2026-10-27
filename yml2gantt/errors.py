"""Errors raised on invalid gantt input, and helpers to write them."""

import datetime as dt
import difflib
import math
from contextlib import contextmanager
from dataclasses import dataclass
from numbers import Real


@dataclass
class Issue:
    """One problem in a gantt description.

    Parameters
    ----------
    message : str
        What is wrong, and how to fix it.
    where : str, optional
        Element concerned, e.g. ``"task 'Permits' > subtask 'Forms'"``.
    line : int, optional
        Line of the element in the ``.yml`` file.
    """

    message: str
    where: str = None
    line: int = None

    def __str__(self):
        place = [f"line {self.line}"] if self.line else []
        if self.where:
            place.append(self.where)
        return f"{', '.join(place)}: {self.message}" if place else self.message


class GanttError(ValueError):
    """Invalid gantt description.

    A subclass of `ValueError`. When loading a file, every problem found
    is listed in ``issues``, not only the first one.

    Parameters
    ----------
    issues : str, Issue or list of Issue
        The problems found.
    """

    def __init__(self, issues):
        if isinstance(issues, (str, Issue)):
            issues = [issues]
        self.issues = [Issue(i) if isinstance(i, str) else i for i in issues]
        super().__init__(self._text())

    def _text(self):
        if len(self.issues) == 1:
            return str(self.issues[0])
        return f"{len(self.issues)} errors:\n" + "\n".join(
            f"  - {issue}" for issue in self.issues)


@contextmanager
def located(where):
    """Add ``where`` to the issues of a `GanttError` raised in the block."""
    try:
        yield
    except GanttError as err:
        for issue in err.issues:
            issue.where = issue.where or where
        raise GanttError(err.issues) from None


def did_you_mean(word, choices):
    """``" (did you mean 'x'?)"`` for a close match of ``word``, else ``""``."""
    match = difflib.get_close_matches(str(word).lower(), list(choices), n=1,
                                      cutoff=0.6)
    return f" (did you mean {match[0]!r}?)" if match else ""


def describe(value):
    """Short description of a value, for error messages."""
    if value is None:
        return "an empty value"
    if isinstance(value, bool):
        return f"the boolean {str(value).lower()}"
    if isinstance(value, dict):
        return "a mapping"
    if isinstance(value, (list, tuple)):
        return "a list"
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, dt.date):
        return f"the date {value.isoformat()}"
    if isinstance(value, Real):
        return f"the number {value}"
    return repr(value)


_BOOL_HINT = (" (in YAML, unquoted yes/no/on/off/true/false are booleans: "
              "put the text in quotes)")


def check_text(value, what, required=False):
    """Check a text value (a number is turned into text).

    Returns
    -------
    str or None
    """
    if value is None:
        if required:
            raise GanttError(f"{what} is missing")
        return None
    if isinstance(value, bool):
        raise GanttError(f"{what} must be text, got {describe(value)}"
                         + _BOOL_HINT)
    if isinstance(value, Real):
        return str(value)
    if not isinstance(value, str):
        raise GanttError(f"{what} must be text, got {describe(value)}")
    if required and not value.strip():
        raise GanttError(f"{what} is empty")
    return value


def check_bool(value, what):
    """Check a ``true``/``false`` value."""
    if not isinstance(value, bool):
        raise GanttError(f"{what} must be true or false, got {describe(value)}")
    return value


def check_number(value, what, minimum=None, integer=False):
    """Check a finite number, optionally ``>= minimum`` (or ``> 0`` for 0).

    Returns
    -------
    float or int
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        raise GanttError(f"{what} must be a number, got {describe(value)}")
    if not math.isfinite(value):
        raise GanttError(f"{what} must be a finite number, got {value}")
    if integer:
        if value != int(value):
            raise GanttError(f"{what} must be a whole number, got {value}")
        value = int(value)
    if minimum == 0 and value <= 0:
        raise GanttError(f"{what} must be greater than 0, got {value}")
    if minimum is not None and value < minimum:
        raise GanttError(f"{what} must be at least {minimum}, got {value}")
    return value
