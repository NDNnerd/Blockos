"""
Blockos — Off-Brand Building Blocks for Basic Python Projects

A lightweight toolkit of reusable base classes and helpers for scaffolding
web-scraping and data-cleaning projects.

Typical usage::

    from blockos.scraping import BaseScraper
    from blockos.cleaning import DataCleaner
"""

from blockos.scraping import BaseScraper
from blockos.cleaning import DataCleaner

__all__ = ["BaseScraper", "DataCleaner"]
__version__ = "0.1.0"
