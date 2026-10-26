"""Drawing of a gantt with matplotlib."""

import matplotlib.pyplot as plt

from .colors import get_color_cycler, lighten_color

TASK_GAP = 1.4  # Vertical step before a top-level task
SUBTASK_GAP = 1.0  # Vertical step before a subtask


def _piece(ax, y, x0, length, text, color, text_color, fontsize, **kw):
    ax.barh(y, length, left=x0, height=1.0, align="center", color=color,
            **kw)
    if text:
        ax.text(x0 + length / 2, y, text, va="center", ha="center",
                color=text_color, fontsize=fontsize, clip_on=True)


def _bar(ax, y, task, color, text_color, fontsize):
    if not task.segments:
        _piece(ax, y, task.start, task.length, task.text, color, text_color,
               fontsize)
        return
    # One bar per segment; a thin white edge separates touching segments.
    for seg in task.segments:
        text = task.text if seg.label is None else str(seg.label)
        _piece(ax, y, seg.start, seg.duration, text, seg.color or color,
               text_color, fontsize, edgecolor="white", linewidth=1)


def _diamond(ax, x, y, name, color, fontsize, size, length):
    ax.plot(x, y, marker="D", markersize=size, color=color,
            markeredgecolor="black", markeredgewidth=0.5, zorder=3,
            clip_on=False)
    # Label on the right, or on the left near the end of the axis.
    if not name:
        return
    # Small background so the label stays readable over a bar.
    left = x > 0.8 * length
    offset = -1 if left else 1
    ax.annotate(name, (x, y), xytext=(offset * (size / 2 + 3), 0),
                textcoords="offset points", va="center",
                ha="right" if left else "left", color=color,
                fontsize=fontsize, zorder=4, annotation_clip=True,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                          alpha=0.8))


def _milestone(ax, y, task, color, fontsize, size, length):
    _diamond(ax, task.start, y, task.text, color, fontsize, size, length)


def _markers(ax, y, task, fontsize, size, length):
    for m in task.milestones:
        _diamond(ax, m.position, y, m.name, m.color or "black", fontsize,
                 size, length)


def _draw_grid(ax, scale):
    for x in scale.minor_ticks():
        ax.axvline(x, color="lightgrey", linestyle="--", alpha=0.3, zorder=-1)

    periods = scale.periods()
    bounds = [p[0] for p in periods] + [periods[-1][1]]
    for x in bounds[1:-1]:
        ax.axvline(x, color="lightgrey", alpha=0.5, zorder=-1)

    # Ticks on the boundaries, labels centered in each period.
    ax.set_xticks(bounds, labels=[""] * len(bounds))
    ax.set_xticks([(a + b) / 2 for a, b, _ in periods],
                  labels=[p[2] for p in periods], minor=True)
    ax.tick_params(axis="x", which="minor", length=0)


def draw(gantt, ax=None, figsize=None, lighten=0.3):
    """Draw a gantt.

    Parameters
    ----------
    gantt : Gantt
        Gantt to draw.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on. Default: a new figure.
    figsize : tuple of float, optional
        Figure size. Default: adapted to the number of rows.
    lighten : float, optional
        Lightening of the subtask color (0 = white, 1 = same).

    Returns
    -------
    fig : matplotlib.figure.Figure
    ax : matplotlib.axes.Axes
    """
    if not gantt.tasks:
        raise ValueError("The gantt has no task")
    rows = sum(1 + len(t.subtasks) for t in gantt.tasks)
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize or (11, max(3, 0.35 * rows + 1.5)))
    else:
        fig = ax.figure

    scale = gantt.scale
    colors = get_color_cycler()
    _draw_grid(ax, scale)

    y, positions, labels = 0.0, [], []
    for task in gantt.tasks:
        color = task.color or colors[task.name]["color"]
        light = lighten_color(color, lighten)
        y += TASK_GAP
        if task.milestone:
            _milestone(ax, y, task, color, 8, 9, scale.length)
        else:
            _bar(ax, y, task, color, light, 8)
            _markers(ax, y, task, 8, 9, scale.length)
        positions.append(y)
        labels.append(task.name)

        for st in task.subtasks:
            y += SUBTASK_GAP
            if st.milestone:
                _milestone(ax, y, st, st.color or color, 7, 7,
                           scale.length)
            else:
                _bar(ax, y, st, st.color or light, color, 7)
                _markers(ax, y, st, 7, 8, scale.length)
            positions.append(y)
            labels.append(st.name)

    now = gantt.now_line()
    if now is not None:
        x, text = now
        ax.axvline(x, color="red", linestyle="--", linewidth=1.2, zorder=5,
                   label=text or None)
        if text:
            # Above the axes, x in data units.
            ax.text(x, 1.0, text, transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", color="red", fontsize=8)

    ax.set_yticks(positions, labels=labels)
    ax.set_ylim(positions[0] - 0.5, positions[-1] + 0.5)
    ax.invert_yaxis()
    ax.set_xlim(0, scale.length)
    if gantt.title:
        # Leave room for the label of the "now" line.
        ax.set_title(gantt.title, pad=16 if now and now[1] else 6)
    fig.tight_layout()
    return fig, ax
