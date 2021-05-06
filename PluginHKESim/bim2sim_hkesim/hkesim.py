﻿from bim2sim.plugin import Plugin
from bim2sim.workflow import PlantSimulation
from bim2sim.kernel.elements import hvac as hvac_elements
from bim2sim.task import base
from bim2sim.task import common
from bim2sim.task import hvac
from bim2sim.export.modelica import standardlibrary
from bim2sim_hkesim.models import HKESim


class LoadLibrariesHKESim(base.ITask):
    """Load HKESim library for export"""
    touches = ('libraries', )

    def run(self, workflow, **kwargs):
        return (standardlibrary.StandardLibrary, HKESim),


class PluginHKESim(Plugin):
    name = 'HKESim'
    default_workflow = PlantSimulation
    tasks = {LoadLibrariesHKESim}
    elements = {*hvac_elements.items}
    default_tasks = [
        hvac.SetIFCTypesHVAC,
        common.LoadIFC,
        common.CreateElements,
        hvac.ConnectElements,
        hvac.MakeGraph,
        hvac.Reduce,
        hvac.DeadEnds,
        LoadLibrariesHKESim,
        hvac.Export,
    ]

    def run(self, playground):
        playground.run_task(hvac.SetIFCTypesHVAC())
        playground.run_task(common.LoadIFC())
        playground.run_task(common.CreateElements())
        playground.run_task(hvac.ConnectElements())
        playground.run_task(hvac.MakeGraph())
        playground.run_task(hvac.Reduce())
        playground.run_task(hvac.DeadEnds())
        playground.run_task(LoadLibrariesHKESim())
        playground.run_task(hvac.Export())
