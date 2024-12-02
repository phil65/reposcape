# RepoScape

[![PyPI License](https://img.shields.io/pypi/l/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Package status](https://img.shields.io/pypi/status/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Daily downloads](https://img.shields.io/pypi/dd/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Weekly downloads](https://img.shields.io/pypi/dw/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Monthly downloads](https://img.shields.io/pypi/dm/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Distribution format](https://img.shields.io/pypi/format/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Wheel availability](https://img.shields.io/pypi/wheel/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Python version](https://img.shields.io/pypi/pyversions/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Implementation](https://img.shields.io/pypi/implementation/reposcape.svg)](https://pypi.org/project/reposcape/)
[![Releases](https://img.shields.io/github/downloads/phil65/reposcape/total.svg)](https://github.com/phil65/reposcape/releases)
[![Github Contributors](https://img.shields.io/github/contributors/phil65/reposcape)](https://github.com/phil65/reposcape/graphs/contributors)
[![Github Discussions](https://img.shields.io/github/discussions/phil65/reposcape)](https://github.com/phil65/reposcape/discussions)
[![Github Forks](https://img.shields.io/github/forks/phil65/reposcape)](https://github.com/phil65/reposcape/forks)
[![Github Issues](https://img.shields.io/github/issues/phil65/reposcape)](https://github.com/phil65/reposcape/issues)
[![Github Issues](https://img.shields.io/github/issues-pr/phil65/reposcape)](https://github.com/phil65/reposcape/pulls)
[![Github Watchers](https://img.shields.io/github/watchers/phil65/reposcape)](https://github.com/phil65/reposcape/watchers)
[![Github Stars](https://img.shields.io/github/stars/phil65/reposcape)](https://github.com/phil65/reposcape/stars)
[![Github Repository size](https://img.shields.io/github/repo-size/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github last commit](https://img.shields.io/github/last-commit/phil65/reposcape)](https://github.com/phil65/reposcape/commits)
[![Github release date](https://img.shields.io/github/release-date/phil65/reposcape)](https://github.com/phil65/reposcape/releases)
[![Github language count](https://img.shields.io/github/languages/count/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github commits this week](https://img.shields.io/github/commit-activity/w/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github commits this month](https://img.shields.io/github/commit-activity/m/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Github commits this year](https://img.shields.io/github/commit-activity/y/phil65/reposcape)](https://github.com/phil65/reposcape)
[![Package status](https://codecov.io/gh/phil65/reposcape/branch/main/graph/badge.svg)](https://codecov.io/gh/phil65/reposcape/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyUp](https://pyup.io/repos/github/phil65/reposcape/shield.svg)](https://pyup.io/repos/github/phil65/reposcape/)

[Read the documentation!](https://phil65.github.io/reposcape/)


Usage:

```python

from reposcape import RepoMapper, PageRankScorer

# Use PageRank scoring
mapper = RepoMapper(scorer=PageRankScorer())

# Create overview
result = mapper.create_overview(
    repo_path="./my_project",
    token_limit=2000,
)

# Or use reference-based scoring
from reposcape import ReferenceScorer

mapper = RepoMapper(
    scorer=ReferenceScorer(
        ref_weight=1.0,
        outref_weight=0.5,
        important_ref_boost=2.0,
        distance_decay=0.5,
    )
)
# Create focused view
result = mapper.create_focused_view(
    files=["src/main.py"],
    repo_path="./my_project",
    token_limit=1000,
)
```
