"""Module for disaggregation"""

import math
import numpy as np
import pint
import re

from bim2sim.kernel.element import BaseElement, SubElement
from bim2sim.task.bps.bps_functions import get_disaggregations_instance


vertical_instances = ['Wall', 'InnerWall', 'OuterWall']
horizontal_instances = ['Roof', 'Floor', 'GroundFloor']


class Disaggregation(BaseElement):
    """Base disaggregation of models"""

    def __init__(self, name, element, *args, **kwargs):
        if 'guid' not in kwargs:
            kwargs['guid'] = self.get_id("Disagg")
        super().__init__(*args, **kwargs)
        self.parent = element
        self.name = name
        self.ifc_type = element.ifc_type
        self.guid = None
        self.get_disaggregation_properties()

    def get_disaggregation_properties(self):
        """properties getter -> that way no sub instances has to be defined"""
        for prop in self.parent.attributes:
            value = getattr(self.parent, prop)
            setattr(self, prop, value)

    def calc_position(self):
        try:
            return self._pos
        except:
            return None

    def calc_orientation(self):
        try:
            return self.parent.orientation
        except:
            return None

    @classmethod
    def based_on_thermal_zone(cls, parent, thermal_zone):
        """creates a disaggregation based on a thermal zone and an instance parent
        based on area slice (thermal zone - area)"""

        new_bound_instances = []
        disaggregations = get_disaggregations_instance(parent, thermal_zone)

        # no disaggregation possible
        if disaggregations is None:
            return [parent]

        parent_area = parent.area.magnitude if isinstance(parent.area, pint.Quantity) else parent.area

        # for vertical instances: if just one disaggregation is possible, check if disaggregation is parent
        # disaggregation is parent if has the same area
        if parent.__class__.__name__ in vertical_instances:
            if len(disaggregations) == 1:
                disaggregation_area = disaggregations[next(iter(disaggregations))][0]
                # here was a tolerance of 0.1 necessary in order to get no false positives
                if abs(disaggregation_area - parent_area) <= 0.1:
                    return [parent]

        name = 'Sub' + parent.__class__.__name__ + '_' + parent.name
        if not hasattr(parent, "sub_instances"):
            parent.sub_instances = []

        i = len(parent.sub_instances)
        for ins in disaggregations:

            scontinue = False
            for dis in parent.sub_instances:
                #  check if disaggregation exists on subinstances, compares disaggregation and existing sub_instances
                # here was a tolerance of 0.1 necessary in order to get no false positives
                if abs(disaggregations[ins][0] - dis.area) <= 0.1:
                    new_bound_instances.append(dis)
                    scontinue = True
                    break
            if scontinue:
                continue

            type_parent = type(parent).__name__
            re_search = re.compile('Sub%s' % type_parent)
            instance = cls(name + '_%d' % i, parent)

            # class assignment for subinstances -> based on re and factory
            for sub_cls in SubElement.get_all_subclasses(cls):
                type_search = sub_cls.__name__
                if re_search.match(type_search):
                    instance = sub_cls(name + '_%d' % i, parent)
                    break

            instance.area = disaggregations[ins][0]

            # position calc
            if parent.__class__.__name__ in vertical_instances:
                instance._pos = get_new_position_vertical_instance(parent, disaggregations[ins][1])
            if parent.__class__.__name__ in horizontal_instances:
                instance._pos = thermal_zone.position

            parent.sub_instances.append(instance)
            new_bound_instances.append(instance)

            if thermal_zone not in parent.thermal_zones:
                parent.thermal_zones.append(thermal_zone)

            i += 1

        return new_bound_instances

    def __repr__(self):
        return "<%s '%s' (disaggregation of the element %d)>" % (
            self.__class__.__name__, self.name, len(self.parent))

    def __str__(self):
        return "%s" % self.__class__.__name__


class SubFloor(Disaggregation):
    disaggregatable_elements = ['IfcSlab']


class SubGroundFloor(Disaggregation):
    disaggregatable_elements = ['IfcSlab']


class SubSlab(Disaggregation):
    disaggregatable_elements = ['IfcSlab']


class SubRoof(Disaggregation):
    disaggregatable_elements = ['IfcRoof', 'IfcSlab']


class SubWall(Disaggregation):
    disaggregatable_elements = ['IfcWall']


class SubInnerWall(Disaggregation):
    disaggregatable_elements = ['IfcWall']


class SubOuterWall(Disaggregation):
    disaggregatable_elements = ['IfcWall']


def get_new_position_vertical_instance(parent, sub_position):
    """get new position based on parent position, orientation and relative disaggregation position"""
    rel_orientation_wall = math.floor(parent.orientation + parent.get_true_north())
    x1, y1, z1 = sub_position
    x, y, z = parent.position
    if 45 <= rel_orientation_wall < 135 or 225 <= rel_orientation_wall < 315:
        y1, z1, z1 = sub_position

    x = x - x1 * math.cos(math.radians(rel_orientation_wall))
    y = y - y1 * math.sin(math.radians(rel_orientation_wall))

    position = np.array([x, y, z])

    return position
