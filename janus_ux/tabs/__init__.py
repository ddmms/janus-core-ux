"""Janus Core UX calculation and configuration tabs."""

from __future__ import annotations

from janus_ux.tabs.tab_descriptors import DescriptorsTab
from janus_ux.tabs.tab_elasticity import ElasticityTab
from janus_ux.tabs.tab_environments import EnvironmentsTab
from janus_ux.tabs.tab_eos import EOSTab
from janus_ux.tabs.tab_geomopt import GeomOptTab
from janus_ux.tabs.tab_md import MDTab
from janus_ux.tabs.tab_neb import NEBTab
from janus_ux.tabs.tab_phonons import PhononsTab
from janus_ux.tabs.tab_singlepoint import SinglePointTab

__all__ = [
    "SinglePointTab",
    "GeomOptTab",
    "MDTab",
    "PhononsTab",
    "EOSTab",
    "ElasticityTab",
    "NEBTab",
    "DescriptorsTab",
    "EnvironmentsTab",
]
