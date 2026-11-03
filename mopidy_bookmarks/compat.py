"""Mopidy version compatibility helpers."""

import mopidy

MOPIDY_V4 = int(mopidy.__version__.split(".")[0]) >= 4
