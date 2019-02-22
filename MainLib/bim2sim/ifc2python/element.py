﻿"""Definition for basic representations of IFC elements"""

import logging
import numpy as np

from bim2sim.decorators import cached_property
from bim2sim.ifc2python import ifc2python

# TODO: Ports, Connections

class Port():
    """"""

    def __init__(self, parent, ifcport):
        self.ifc = ifcport
        self.name = ifcport.Name
        self.parent = parent
        self.connections = []

    def connect(self, other):
        """Connect this interface to another interface"""
        assert isinstance(other, self.__class__), "Can't connect interfaces" \
                                                  " of different classes."
        self.connections.append(other)

    @cached_property
    def flow_direction(self):
        """returns the flow direction"""
        return self.ifc.FlowDirection

    @cached_property
    def position(self):
        """returns absolute position"""
        try:
            relative_placement = \
                self.parent.ifc.ObjectPlacement.RelativePlacement
            x_direction = np.array([
                relative_placement.RefDirection.DirectionRatios[0],
                relative_placement.RefDirection.DirectionRatios[1],
                relative_placement.RefDirection.DirectionRatios[2]])
            z_direction = np.array([
                relative_placement.Axis.DirectionRatios[0],
                relative_placement.Axis.DirectionRatios[1],
                relative_placement.Axis.DirectionRatios[2]])
        except AttributeError as ae:
            self.parent.logger.info(str(ae) + ' - DirectionRatios not '
                                              'existing, assuming [1, 1, '
                                              '1] as direction of element ' +
                                    str(self.parent.ifc))
            x_direction = np.array([1, 0, 0])
            z_direction = np.array([0, 0, 1])
        y_direction = np.cross(z_direction, x_direction)
        port_coordinates_relative = \
            self.ifc.ObjectPlacement.RelativePlacement.Location.Coordinates
        coordinates = []
        for i in range(0, 3):
            coordinates.append(
                self.parent.position[i]
                + x_direction[i] * port_coordinates_relative[0]
                + y_direction[i] * port_coordinates_relative[1]
                + z_direction[i] * port_coordinates_relative[2])
        return coordinates

    def __repr__(self):
        return "<%s (%s)>"%(self.__class__.__name__, self.name)


class Element():
    """Base class for IFC model representation"""

    _ifc_type = None
    _ifc_classes = {}
    dummy = None

    def __init__(self, ifc):
        self.logger = logging.getLogger(__name__)
        self.ifc = ifc
        self.guid = ifc.GlobalId
        self.name = ifc.Name
        self.ports = [] #TODO
        self._add_ports()

    def _add_ports(self):
        element_port_connections = self.ifc.HasPorts
        for element_port_connection in element_port_connections:
            self.ports.append(Port(self, element_port_connection.RelatingPort))

    @staticmethod
    def _init_factory():
        """initialize lookup for factory"""
        logger = logging.getLogger(__name__)
        conflict = False
        for cls in Element.__subclasses__():
            if cls.ifc_type is None:
                conflict = True
                logger.error("Invalid ifc_type (%s) in '%s'", cls.ifc_type, cls.__name__)
            elif cls.ifc_type in Element._ifc_classes:
                conflict = True
                logger.error("Conflicting ifc_types (%s) in '%s' and '%s'", \
                    cls.ifc_type, cls.__name__, Element._ifc_classes[cls.ifc_type])
            elif cls.__name__ == "Dummy":
                Element.dummy = cls
            elif not cls.ifc_type.lower().startswith("ifc"):
                conflict = True
                logger.error("Invalid ifc_type (%s) in '%s'", cls.ifc_type, cls.__name__)
            else:
                Element._ifc_classes[cls.ifc_type] = cls

        if conflict:
            raise AssertionError("Conflict(s) in Models. (See log for details).")

        #Model.dummy = Model.ifc_classes['any']

        logger.debug("IFC model factory intitialized with %d models:", len(Element._ifc_classes))
        for model in Element._ifc_classes:
            logger.debug("- %s", model)

    @staticmethod
    def factory(ifc_element):
        """Create model depending on ifc_element"""

        if not Element._ifc_classes:
            Element._init_factory()

        ifc_type = ifc_element.is_a()
        cls = Element._ifc_classes.get(ifc_type, Element.dummy)
        #if cls is Model.dummy:
        #    logger = logging.getLogger(__name__)
        #    logger.warning("Did not found matching class for %s", ifc_type)

        return cls(ifc_element)

    @property
    def ifc_type(self):
        """Returns IFC type"""
        return self.__class__._ifc_type

    @cached_property
    def position(self):
        """returns absolute position"""
        pos = tuple(map(sum, zip(self.ifc.ObjectPlacement.
                    RelativePlacement.Location.Coordinates,
                                 self.ifc.ObjectPlacement.
                                 PlacementRelTo.RelativePlacement.
                                 Location.Coordinates)))
        return pos

    def get_ifc_attribute(self, attribute):
        """
        Fetches non-empty attributes (if they exist).
        """
        try:
            return getattr(self.ifc, attribute)
        except AttributeError:
            pass

    def get_propertysets(self, propertysetname):
        return ifc2python.get_Property_Sets(propertysetname, self.ifc)

    def get_hierarchical_parent(self):
        return ifc2python.getHierarchicalParent(self.ifc)

    def get_hierarchical_children(self):
        return ifc2python.getHierarchicalChildren(self.ifc)

    def get_spartial_parent(self):
        return ifc2python.getSpatialParent(self.ifc)

    def get_spartial_children(self):
        return ifc2python.getSpatialChildren(self.ifc)

    def get_space(self):
        return ifc2python.getSpace(self.ifc)

    def get_storey(self):
        return ifc2python.getStorey(self.ifc)

    def get_building(self):
        return ifc2python.getBuilding(self.ifc)

    def get_site(self):
        return ifc2python.getSite(self.ifc)

    def get_project(self):
        return ifc2python.getProject(self.ifc)

    def __repr__(self):
        return "<%s (%s)>"%(self.__class__.__name__, self.name)



class Dummy(Element):
    """Dummy for all unknown elements"""
    #ifc_type = 'any'

    def __init__(self, ifc):
        super().__init__(ifc)

        self._ifc_type = ifc.get_info()['type']

    @property
    def ifc_type(self):
        return self._ifc_type

