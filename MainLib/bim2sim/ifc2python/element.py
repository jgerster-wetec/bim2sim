﻿"""Definition for basic representations of IFC elements"""

import logging
from json import JSONEncoder
import itertools
import re

import numpy as np

from bim2sim.decorators import cached_property
from bim2sim.ifc2python import ifc2python
from bim2sim.decision import Decision, BoolDecision, RealDecision, ListDecision, DictDecision, PendingDecisionError


class ElementError(Exception):
    """Error in Element"""
class NoValueError(ElementError):
    """Value is not available"""


class ElementEncoder(JSONEncoder):
    """Encoder class for Element"""
    #TODO: make Elements serializable and deserializable.
    # Ideas: guid to identify, (factory) method to (re)init by guid
    # mayby weakref to other elements (Ports, connections, ...)

    def default(self, o):
        if isinstance(o, Element):
            return "<Element(%s)>"%(o.guid)
        return JSONEncoder.default()


class Root:
    """Most basic class

    keeps track of created instances and guids"""
    objects = {}
    _id_counter = 0

    def __init__(self, guid=None):
        self.guid = guid or self.get_id()
        Root.objects[self.guid] = self
        self._requests = []
        self.properties = {}

    def __hash__(self):
        return hash(self.guid)

    def calc_position(self):
        """Returns position (calculation may be expensive)"""
        return None

    @cached_property
    def position(self):
        """Position

        calculated only once by calling calc_position"""
        return self.calc_position()

    @staticmethod
    def get_id(prefix=""):
        prefix_length = len(prefix)
        if prefix_length > 8:
            raise AttributeError("Max prefix legth is 8!")
        Root._id_counter += 1
        return "{0:0<8s}{1:0>14d}".format(prefix, Root._id_counter)

    @staticmethod
    def get_object(guid):
        """Get Root object instance with given guid

        :returns: None if object with guid was not instanciated"""
        return Root.objects.get(guid)

    def request(self, name):
        if not name in self._requests:
            self._requests.append(name)

    @classmethod
    def solve_requests(cls):
        """trys to obtain all requested attributes.

        First step is to collect neccesary Decisions
        Secend step is to solve them"""

        # First step
        pending = []
        for ele in Root.objects.values():
            while ele._requests:
                request = ele._requests.pop()
                try:
                    value = ele.find(request, collect_decisions=True)
                except PendingDecisionError:
                    pending.append((ele, request))
                except NoValueError:
                    # Value for attribute does not exist
                    pass
                else:
                    ele.properties[request] = value

        Decision.decide_collected()

        for ele, request in pending:
            value = ele.find(request, collect_decisions=False)
            ele.properties[request] = value

    def search(self, name, collect_decisions=False):
        """Search all potential sources for property (potentially time consuming)"""
        raise NoValueError("'%s' is not available"%name)

    def find(self, name, collect_decisions=False):
        """Check for known property value. Calls search() if unknown"""
        # check if property is known
        if name in self.properties:
            return self.properties[name]
        if collect_decisions:
            if name in self._requests:
                raise PendingDecisionError
            #self.request(name)
        #elif name in self._requests:
        #    self._requests.remove(name)

        # search for property
        value = self.search(name, collect_decisions)

        # store value
        self.properties[name] = value
        return value

    def __del__(self):
        del Root.objects[self.guid]


class IFCBased(Root):
    """Mixin for all IFC representating classes"""
    ifc_type = None
    _ifc_classes = {}

    def __init__(self, ifc, *args, **kwargs):
        super().__init__(*args, guid=ifc.GlobalId, **kwargs)
        self.ifc = ifc
        self.name = ifc.Name

        self._propertysets = None
        self._type_propertysets = None

        self._decision_results = {}

    @property
    def ifc_type(self):
        """Returns IFC type"""
        return self.__class__.ifc_type

    def calc_position(self):
        """returns absolute position"""
        rel = np.array(self.ifc.ObjectPlacement.
                       RelativePlacement.Location.Coordinates)
        relto = np.array(self.ifc.ObjectPlacement.
                         PlacementRelTo.RelativePlacement.Location.Coordinates)
        return rel + relto

    def get_ifc_attribute(self, attribute):
        """
        Fetches non-empty attributes (if they exist).
        """
        return getattr(self.ifc, attribute, None)

    def get_propertyset(self, propertysetname):
        return ifc2python.get_Property_Set(propertysetname, self.ifc)

    def get_propertysets(self):
        if self._propertysets is None:
            self._propertysets = ifc2python.get_property_sets(self.ifc)
        return self._propertysets

    def get_type_propertysets(self):
        if self._type_propertysets is None:
            self._type_propertysets = ifc2python.get_type_property_sets(self.ifc)
        return self._type_propertysets

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

    def search_property_hierarchy(self, propertyset_name):
        """Search for property in all related properties in hierarchical order.

        1. element's propertysets
        2. element type's propertysets"""

        p_set = None
        p_sets = self.get_propertysets()
        try:
            p_set = p_sets[propertyset_name]
        except KeyError:
            pass
        else:
            return p_set

        pt_sets = self.get_type_propertysets()
        try:
            p_set = pt_sets[propertyset_name]
        except KeyError:
            pass
        else:
            return p_set
        return p_set

    def inverse_properties(self):
        """Generator yielding tuples of PropertySet name and Property name"""
        for p_set_name, p_set in self.get_propertysets().items():
            for p_name in p_set.keys():
                yield (p_set_name, p_name)

    def filter_properties(self, patterns):
        """filter all properties by re pattern

        :returns: list of tuple(propertyset_name, property_name, match)"""
        matches = []
        for propertyset_name, property_name in self.inverse_properties():
            for pattern in patterns:
                match = re.match(pattern, property_name)
                if match:
                    matches.append((propertyset_name, property_name, match))
        return matches

    def get_exact_property(self, propertyset_name, property_name):
        """Returns value of property specified by propertyset name and property name

        :Raises: AttriebuteError if property does not exist"""
        try:
            p_set = self.search_property_hierarchy(propertyset_name)
            value = p_set[property_name]
        except (AttributeError, KeyError, TypeError):
            raise NoValueError("Property '%s.%s' does not exist"%(
                propertyset_name, property_name))
        return value

    def select_from_potential_properties(self, patterns, name, collect_decisions):
        """Ask user to select from all properties matching patterns"""

        matches = self.filter_properties(patterns)
        selected = None
        if matches:
            values = []
            choices = []
            for propertyset_name, property_name, match in matches:
                value = self.get_exact_property(propertyset_name, property_name)
                values.append(value)
                choices.append((propertyset_name, property_name))
                #print("%s.%s = %s"%(propertyset_name, property_name, value))

            # TODO: Decision: save for all following elements of same class (dont ask again?)
            # selected = (propertyset_name, property_name, value)

            # TODO: Decision with id, key, value
            decision = DictDecision("Multiple possibilities found",
                choices=dict(zip(choices, values)),
                output=self.properties, 
                output_key=name,
                global_key="%s_%s.%s"%(self.ifc_type, self.guid, name),
                allow_skip=True, allow_load=True, allow_save=True,
                collect=collect_decisions, quick_decide=not collect_decisions)

            if collect_decisions:
                raise PendingDecisionError()

            return decision.value
        raise NoValueError("No matching property for %s"%(patterns))

    def search(self, name, collect_decisions = False):
        """Search all potential sources for property (potentially time consuming)"""

        try:
            propertyset_name, property_name = getattr(
                self.__class__, 'default_%s'%name, (None, None))
            if not (propertyset_name and property_name):
                raise NoValueError
            value = self.get_exact_property(propertyset_name, property_name)
        except NoValueError:
            pass
        else:
            return value

        try:
            value = self.finder.find(self, name)
        except AttributeError:
            pass
        else:
            if not value is None:
                return value

        try:
            patterns = getattr(self.__class__, 'pattern_%s'%name, None)
            if not patterns:
                raise NoValueError("No patterns")
            value = self.select_from_potential_properties(patterns, name, collect_decisions)
        except NoValueError:
            pass
        else:
            return value

        final_decision = RealDecision("Enter value for %s of %s"%(name, self.name),
            validate_func=lambda x:isinstance(x, float), # TODO
            output=self.properties, 
            output_key=name,
            global_key="%s_%s.%s"%(self.ifc_type, self.guid, name),
            allow_skip=True, allow_load=True, allow_save=True,
            collect=collect_decisions, quick_decide=not collect_decisions)

        if collect_decisions:
            raise PendingDecisionError()
        value = final_decision.value
        return value

    def __repr__(self):
        return "<%s (%s)>"%(self.__class__.__name__, self.name)


class BaseElement(Root):
    """Base class for all elements with ports"""
    objects = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BaseElement.objects[self.guid] = self
        self.logger = logging.getLogger(__name__)
        self.ports = []
        self.aggregation = None

    def get_inner_connections(self):
        """Returns inner connections of Element

        by default each port is connected to each other port.
        Overwrite for other connections"""

        connections = []
        for port0, port1 in itertools.combinations(self.ports, 2):
            connections.append((port0, port1))
        return connections

    @staticmethod
    def get_element(guid):
        """Get element instance with given guid

        :returns: None if element with guid was not instanciated"""
        return BaseElement.objects.get(guid)

    def __repr__(self):
        return "<%s (ports: %d)>"%(self.__class__.__name__, len(self.ports))


class BasePort(Root):
    """Basic port"""
    objects = {}

    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.connection = None
        BasePort.objects[self.guid] = self

        self._flow_master = False
        self._flow_direction = None

    @staticmethod
    def get_port(guid):
        """Get port instance with given guid

        :returns: None if port with guid was not instanciated"""
        return BasePort.objects.get(guid)

    def connect(self, other):
        """Connect this interface bidirectional to another interface"""
        assert isinstance(other, BasePort), "Can't connect interfaces" \
                                                  " of different classes."
        # if self.flow_direction == 'SOURCE' or \
        #         self.flow_direction == 'SOURCEANDSINK':
        if self.connection and self.connection is not other:
            raise AttributeError("Port is already connected!")
        if other.connection and other.connection is not self:
            raise AttributeError("Other port is already connected!")
        self.connection = other
        other.connection = self

    def is_connected(self):
        """Returns truth value of port's connection"""
        return bool(self.connection)

    @property
    def flow_master(self):
        """Lock flow direction for port"""
        return self._flow_master

    @flow_master.setter
    def flow_master(self, value: bool):
        self._flow_master = value

    @property
    def flow_direction(self):
        """Flow direction of port

        -1 = medium flows into port
        1 = medium flows out of port
        0 = medium flow undirected
        None = flow direction unknown"""
        return self._flow_direction

    @flow_direction.setter
    def flow_direction(self, value):
        if self._flow_master:
            raise AttributeError("Can't set flow direction for flow master.")
        if value not in (-1, 0, 1, None):
            raise AttributeError("Invalid value. Use one of (-1, 0, 1, None).")
        self._flow_direction = value

    @property
    def verbose_flow_direction(self):
        """Flow direction of port"""
        if self.flow_direction == -1:
            return 'SINK'
        if self.flow_direction == 0:
            return 'SINKANDSOURCE'
        if self.flow_direction == 1:
            return 'SOURCE'
        return 'UNKNOWN'

    def __del__(self):
        del BasePort.objects[self.guid]

    def __repr__(self):
        if self.parent:
            try:
                idx = self.parent.ports.index(self)
                return "<%s (#%d, parent: %s)>"%(
                    self.__class__.__name__, idx, self.parent)
            except ValueError:
                return "<%s (broken parent: %s)>"%(
                    self.__class__.__name__, self.parent)
        return "<%s (*abandoned*)>"%(self.__class__.__name__)


class Port(BasePort, IFCBased):
    """Port of Element"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.groups = {assg.RelatingGroup.ObjectType
                       for assg in self.ifc.HasAssignments}

        if self.ifc.FlowDirection == 'SOURCE':
            self.flow_direction = 1
        elif self.ifc.FlowDirection == 'SINK':
            self.flow_direction = -1
        elif self.ifc.FlowDirection == 'SINKANDSOURCE':
            self.flow_direction = 0

    def calc_position(self):
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

        if all(coordinates == np.array([0, 0, 0])):
            logger = logging.getLogger('IFCQualityReport')
            logger.info("Suspect position [0, 0, 0] for %s", self)
        return coordinates


class Element(BaseElement, IFCBased):
    """Base class for IFC model representation

    WARNING: getting an not defined attribute from instances of Element will
    return None (from finder) instead of rasing an AttributeError"""

    dummy = None
    finder = None

    def __init__(self, *args, tool=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._tool = tool
        self._add_ports()

    def _add_ports(self):
        if hasattr(self.ifc, "HasPorts"):
            element_port_connections = self.ifc.HasPorts
            for element_port_connection in element_port_connections:
                self.ports.append(Port(parent=self, ifc=element_port_connection.RelatingPort))


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
                logger.error("Conflicting ifc_types (%s) in '%s' and '%s'",
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
        logger.debug("IFC model factory initialized with %d ifc classes:\n%s",
                     len(Element._ifc_classes), model_txt)

    @staticmethod
    def factory(ifc_element, tool=None):
        """Create model depending on ifc_element"""

        if not Element._ifc_classes:
            Element._init_factory()

        ifc_type = ifc_element.is_a()
        cls = Element._ifc_classes.get(ifc_type, Element.dummy)
        if cls is Element.dummy:
            logger = logging.getLogger(__name__)
            logger.warning("Did not found matching class for %s", ifc_type)

        return cls(ifc=ifc_element, tool=tool)

    @property
    def source_tool(self):
        """Name of tool the ifc has been created with"""
        if not self._tool:
            self._tool = self.get_project().OwnerHistory.OwningApplication.ApplicationFullName
        return self._tool

    @property
    def neighbors(self):
        """Directly connected elements"""
        neighbors = []
        for port in self.ports:
            neighbors.append(port.connection.parent)
        return neighbors

    def __repr__(self):
        return "<%s (ports: %d, guid=%s)>"%(
            self.__class__.__name__, len(self.ports), self.guid)


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
