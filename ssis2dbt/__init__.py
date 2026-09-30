"""SSIS-to-dbt Migration Engine.

Parse SSIS .dtsx packages into deployable dbt projects.
"""
from . import dialects  # noqa: F401  (register dialects)
from .dialects import impls  # noqa: F401
from .engine import convert_file, convert_package, ConversionRun  # noqa: F401

__version__ = "0.1.0"
