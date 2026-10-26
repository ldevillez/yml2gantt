"""Build a gantt from Python: set it up, then add tasks."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing
from yml2gantt import Gantt  # noqa: E402

# 1. Setup
g = Gantt(start="2026-01-01", end="2027-01-01", scale="trimester",
          title="Board game launch")

# 2. Tasks
g.add_task("Market research", start=0, duration="6w")
design = g.add_task("Game design", start="2026-02-15")
design.add_subtask("Rules", duration="3w")
design.add_subtask("Prototype", start="3w", duration=60)
design.add_subtask("Playtest day", start="2026-06-01", milestone=True)
g.add_task("Crowdfunding", start="2026-09-01", end="2026-12-15", color="tab:red")
g.add_task("Shipping", start="2026-12-15", milestone=True)

fig, ax = g.draw()
fig.savefig(Path(__file__).with_suffix(".pdf"))
plt.show()
