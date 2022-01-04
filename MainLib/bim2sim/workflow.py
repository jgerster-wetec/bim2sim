﻿"""Module for defining workflows"""

from enum import Enum


class LOD(Enum):
    """Level of detail"""
    ignore = 0  # don't even read from ifc
    low = 1  # reduce to absolute minimum
    medium = 2  # aggregate
    full = 3  # keep full details


class Workflow:
    """Specification of Workflow"""

    def __init__(self,
                 ductwork: LOD,
                 hull: LOD,
                 consumer: LOD,
                 generator: LOD,
                 hvac: LOD,
                 spaces: LOD,
                 layers: LOD,
                 create_external_elements=False,
                 filters: list = None):

        self.ductwork = ductwork
        self.hull = hull
        self.consumer = consumer
        self.generator = generator
        self.hvac = hvac
        self.spaces = spaces
        self.layers = layers
        self.create_external_elements = create_external_elements

        self.filters = filters if filters else []
        self.ifc_units = {}  # dict to store project related units

        self.relevant_elements = []

        # default values
        self.pipes = LOD.medium
        self.underfloorheatings = LOD.medium
        self.pumps = LOD.medium

    def update_from_config(self, config):
        self.pipes = LOD(config['Aggregation'].getint('Pipes', 2))
        self.underfloorheatings = LOD(config['Aggregation'].getint('UnderfloorHeating', 2))
        self.pumps = LOD(config['Aggregation'].getint('Pumps', 2))


class PlantSimulation(Workflow):

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.ignore,
            consumer=LOD.low,
            generator=LOD.full,
            hvac=LOD.low,
            spaces=LOD.ignore,
            layers=LOD.full,
        )


class BPSMultiZoneSeparatedLayersFull(Workflow):
    """Building performance simulation with every space as single zone
    separated from each other - no aggregation.
    Detailed layer information required."""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.full,
            # layers=LOD.low,
            layers=LOD.full,
        )


class BPSMultiZoneSeparatedLayersLow(Workflow):
    """Building performance simulation with every space as single zone
    separated from each other - no aggregation.
    Not existing layer information is enriched by templates."""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.full,
            layers=LOD.low,
        )


class BPSMultiZoneCombinedLayersFull(Workflow):
    """Building performance simulation with aggregation based on zone
    aggregation algorithms.
    Detailed layer information required."""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.medium,
            layers=LOD.full,
        )


class BPSMultiZoneCombinedLayersLow(Workflow):
    """Building performance simulation with aggregation based on zone
    aggregation algorithms.
    Not existing layer information is enriched by templates."""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.medium,
            layers=LOD.low,
        )


class BPSMultiZoneAggregatedLayersLow(Workflow):
    """Building performance simulation with spaces aggregated.
     Not existing layer information is enriched by templates."""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.medium,
            layers=LOD.low,
        )


class BPSMultiZoneAggregatedLayersFull(Workflow):
    """Building performance simulation with spaces aggregated.
    Detailed layer information required."""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.medium,
            layers=LOD.full,
        )


class BPSOneZoneAggregatedLayersLow(Workflow):
    """Building performance simulation with all rooms aggregated to one thermal
    zone. Not existing layer information is enriched by templates."""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.low,
            layers=LOD.low,
            # layers=LOD.full,
        )


class BPSOneZoneAggregatedLayersFull(Workflow):
    """Building performance simulation with all rooms aggregated to one thermal
    zone. Detailed layer information required."""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.low,
            layers=LOD.full,
        )


class BPSMultiZoneSeparatedEP(Workflow):
    """Building performance simulation with every space as single zone
    separated from each other - no aggregation,
    used within the EnergyPlus Workflow"""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.full,
            layers=LOD.low,
            create_external_elements=True,  # consider IfcExternalSpatialElements
        )


class BPSMultiZoneSeparatedEPfull(Workflow):
    """Building performance simulation with every space as single zone
    separated from each other - no aggregation,
    used within the EnergyPlus Workflow"""

    def __init__(self):
        super().__init__(
            ductwork=LOD.low,
            hull=LOD.medium,
            consumer=LOD.low,
            generator=LOD.ignore,
            hvac=LOD.low,
            spaces=LOD.full,
            layers=LOD.full,
            create_external_elements=True,  # consider IfcExternalSpatialElements
        )
