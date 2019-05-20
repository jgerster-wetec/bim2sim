﻿"""Definition for basic representations of IFC elements"""

import logging
from json import JSONEncoder
import itertools

import numpy as np

from bim2sim.decorators import cached_property
from bim2sim.ifc2python import ifc2python

class ElementError(Exception):
    """Error in Element"""

class ElementEncoder(JSONEncoder):
    """Encoder class for Element"""
    #TODO: make Elements serializable and deserializable.
    # Ideas: guid to identify, (factory) method to (re)init by guid
    # mayby weakref to other elements (Ports, connections, ...)

    def default(self, o):
        if isinstance(o, Element):
            return "<Element(%s)>"%(o.guid)
        return JSONEncoder.default()

class Port():
    """Port of Element"""

    def __init__(self, parent, ifcport):
        self.ifc = ifcport
        #self.name = ifcport.Name
        self.natural_parent = parent
        self.aggregated_parent = None
        self.connection = None

    def connect(self, other):
        """Connect this interface to another interface"""
        assert isinstance(other, self.__class__), "Can't connect interfaces" \
                                                  " of different classes."
        # if self.flow_direction == 'SOURCE' or \
        #         self.flow_direction == 'SOURCEANDSINK':
        if self.connection:
            raise AttributeError("Port is already connected!")
        self.connection = other

    @property
    def parent(self):
        """Parent of port

        Returns aggregated_parent if set else natural_parent"""

        if self.aggregated_parent:
            return self.aggregated_parent
        return self.natural_parent

    @property
    def ifc_type(self):
        """Returns IFC type"""
        return self.ifc.is_a()

    @cached_property
    def flow_direction(self):
        """returns the flow direction"""
        return self.ifc.FlowDirection

    @cached_property
    def position(self):
        """returns absolute position as np.array"""
        try:
            relative_placement = \
                self.parent.ifc.ObjectPlacement.RelativePlacement
            x_direction = np.array(relative_placement.RefDirection.DirectionRatios)
            z_direction = np.array(relative_placement.Axis.DirectionRatios)
        except AttributeError:
            x_direction = np.array([1, 0, 0])
            z_direction = np.array([0, 0, 1])
        y_direction = np.cross(z_direction, x_direction)
        directions = np.array((x_direction, y_direction, z_direction)).T
        port_coordinates_relative = \
            np.array(self.ifc.ObjectPlacement.RelativePlacement.Location.Coordinates)
        coordinates = self.parent.position + np.matmul(directions, port_coordinates_relative)

        return coordinates

    def __repr__(self):
        return "<%s (from %s)>"%(self.__class__.__name__, self.parent.name)


class ElementMeta(type):
    """Metaclass or Element

    catches class creation and lists all properties (and subclasses) as findables
    for Element.finder. Class can use custom findables by providung the
    attribute 'findables'."""

    def __new__(cls, clsname, superclasses, attributedict):
        sc_element = [sc for sc in superclasses if sc is Element]
        if sc_element:
            findables = []
            overwrite = True
            for name, value in attributedict.items():
                if name == 'findables':
                    overwrite = False
                    break
                if isinstance(value, property):
                    findables.append(name)
            if overwrite:
                attributedict['findables'] = tuple(findables)
        return type.__new__(cls, clsname, superclasses, attributedict)

class Element(metaclass=ElementMeta):
    """Base class for IFC model representation

    WARNING: getting an not defined attribute from instances of Element will
    return None (from finder) instead of rasing an AttributeError"""

    _ifc_type = None
    _ifc_classes = {}
    dummy = None
    finder = None
    findables = ()

    def __init__(self, guid, name, ifc, tool=None):
        self.logger = logging.getLogger(__name__)
        self.ifc = ifc
        self.guid = guid
        self.name = name
        self._tool = tool
        self.ports = []
        self._add_ports()
        self.aggregation = None

    def __getattr__(self, name):
        # user finder to get attribute
        if self.__class__.finder:
            return self.__class__.finder.find(self, name)
        return super().__getattr__(name)

    def __getattribute__(self, name):
        found = object.__getattribute__(self, name)
        if found is None:
            findables = object.__getattribute__(self, '__class__').findables
            if name in findables:
                # if None is returned ask finder for value 
                # (on AttributeError __getattr__ is called anyway)
                try:
                    found = object.__getattribute__(self, '__getattr__')(name)
                except AttributeError:
                    pass
        return found

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
                logger.error("Invalid ifc_type (%s) in '%s'", cls.ifc_type,
                             cls.__name__)
            else:
                Element._ifc_classes[cls.ifc_type] = cls

        if conflict:
            raise AssertionError("Conflict(s) in Models. (See log for details).")

        #Model.dummy = Model.ifc_classes['any']
        if not Element._ifc_classes:
            raise ElementError("Faild to initialize Element factory. No elements found!")

        model_txt = "\n".join(" - %s"%(model) for model in Element._ifc_classes)
        logger.debug("IFC model factory intitialized with %d ifc classes:\n%s",
                     len(Element._ifc_classes), model_txt)

    @staticmethod
    def factory(ifc_element, tool=None):
        """Create model depending on ifc_element"""

        if not Element._ifc_classes:
            Element._init_factory()

        ifc_type = ifc_element.is_a()
        cls = Element._ifc_classes.get(ifc_type, Element.dummy)
        #if cls is Model.dummy:
        #    logger = logging.getLogger(__name__)
        #    logger.warning("Did not found matching class for %s", ifc_type)

        return cls(ifc_element.GlobalId, ifc_element.Name, ifc_element, tool)

    @property
    def ifc_type(self):
        """Returns IFC type"""
        return self.__class__._ifc_type

    @property
    def source_tool(self):
        """Name of tool the ifc has been created with"""
        if not self._tool:
            self._tool = self.get_project().OwnerHistory.OwningApplication.ApplicationFullName
        return self._tool

    @cached_property
    def position(self):
        """returns absolute position"""
        rel = np.array(self.ifc.ObjectPlacement.
                       RelativePlacement.Location.Coordinates)
        relto = np.array(self.ifc.ObjectPlacement.
                         PlacementRelTo.RelativePlacement.Location.Coordinates)
        return rel + relto

    @property
    def neighbors(self):
        """Directly connected elements"""
        neighbors = []
        for port in self.ports:
            neighbors.append(port.connection.parent)
        return neighbors

    def get_inner_connections(self):
        """Returns inner connections of Element

        by default each port is connected to each other port.
        Overwrite for other connections"""

        connections = []
        for port0, port1 in itertools.combinations(self.ports, 2):
            connections.append((port0, port1))
        return connections

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

    def summary(self):
        return ifc2python.summary(self.ifc)

    def __repr__(self):
        return "<%s (%s)>"%(self.__class__.__name__, self.name)


class Dummy(Element):
    """Dummy for all unknown elements"""
    #ifc_type = 'any'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._ifc_type = self.ifc.get_info()['type']

    @property
    def ifc_type(self):
        return self._ifc_type

# import Element classes for Element.factory
import bim2sim.ifc2python.elements
