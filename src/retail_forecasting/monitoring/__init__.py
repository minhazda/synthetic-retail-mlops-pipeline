"""Monitoring utilities (offline data-drift reporting).

Kept separate from the serving package so its heavy, optional dependency
(Evidently) is not required by the inference image or the core test suite.
"""
