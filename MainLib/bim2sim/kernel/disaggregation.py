"""Module for disaggregation"""

import math
import numpy as np

from bim2sim.kernel import attribute
from bim2sim.kernel.element import BaseElement
from bim2sim.task.bps_f.bps_functions import get_boundaries, get_disaggregations_instance, get_position_instance

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
        switcher = {'SubFloor': SubFloor,
                    'SubGroundFloor': SubGroundFloor,
                    'SubSlab': SubSlab,
                    'SubRoof': SubRoof,
                    'SubWall': SubWall,
                    'SubInnerWall': SubInnerWall,
                    'SubOuterWall': SubOuterWall}
        sub_module = 'Sub' + self.parent.__class__.__name__
        func = switcher.get(sub_module)
        if func is not None:
            self.__class__ = func
            self.__init__(self.name, self.parent)

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
        disaggregations = get_disaggregations_instance(parent, thermal_zone)
        length, width = get_boundaries(parent.ifc)

        if disaggregations is None:
            return False

        if parent.__class__.__name__ in vertical_instances:
            if len(disaggregations) == 1:
                if length == disaggregations[next(iter(disaggregations))][0] or \
                        length - width == disaggregations[next(iter(disaggregations))][0]:
                    return False

        name = 'Sub' + parent.__class__.__name__ + '_' + parent.name
        if not hasattr(parent, "sub_instances"):
            parent.sub_instances = []
        i = len(parent.sub_instances)
        ii = 0
        for ins in disaggregations:
            scontinue = False

            instance_area = disaggregations[ins][0] * disaggregations[ins][1]

            for dis in parent.sub_instances:
                if instance_area == dis.area:
                    if dis not in thermal_zone.bound_elements:
                        thermal_zone.bound_elements.append(dis)
                    if thermal_zone not in dis.thermal_zones:
                        dis.thermal_zones.append(thermal_zone)
                    scontinue = True

            if scontinue:
                continue

            instance = cls(name + '_%d' % i, parent)
            instance.area = instance_area

            # position calc
            if parent.__class__.__name__ in vertical_instances:
                instance._pos = get_new_position_vertical_instance(parent,
                                                                   get_position_instance(parent, thermal_zone)[ii])
            if parent.__class__.__name__ in horizontal_instances:
                instance._pos = thermal_zone.position
            ii += 1

            parent.sub_instances.append(instance)
            if instance not in thermal_zone.bound_elements:
                thermal_zone.bound_elements.append(instance)
            if thermal_zone not in instance.thermal_zones:
                instance.thermal_zones.append(thermal_zone)

            i += 1

        return True

    def __repr__(self):
        return "<%s '%s' (disaggregation of the element %d)>" % (
            self.__class__.__name__, self.name, len(self.parent))


class SubFloor(Disaggregation):
    disaggregatable_elements = ['IfcSlab']

    def __init__(self, *args, **kwargs):
        pass

    @attribute.multi_calc
    def _get_properties(self):
        result = dict(
            area=self.parent.area,
            thickness=self.parent.thickness,
            thermal_transmittance=self.parent.thermal_transmittance,
            is_external=self.parent.is_external
        )
        return result

    area = attribute.Attribute(
        name='area',
        functions=[_get_properties]
    )

    thickness = attribute.Attribute(
        name='thickness',
        functions=[_get_properties]
    )

    thermal_transmittance = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )

    is_external = attribute.Attribute(
        name='is_external',
        functions=[_get_properties]
    )


class SubGroundFloor(Disaggregation):
    disaggregatable_elements = ['IfcSlab']

    def __init__(self, *args, **kwargs):
        pass

    @attribute.multi_calc
    def _get_properties(self):
        result = dict(
            area=self.parent.area,
            thickness=self.parent.thickness,
            thermal_transmittance=self.parent.thermal_transmittance,
            is_external=self.parent.is_external
        )
        return result

    area = attribute.Attribute(
        name='area',
        functions=[_get_properties]
    )

    thickness = attribute.Attribute(
        name='thickness',
        functions=[_get_properties]
    )

    thermal_transmittance = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )

    is_external = attribute.Attribute(
        name='is_external',
        functions=[_get_properties]
    )


class SubSlab(Disaggregation):
    disaggregatable_elements = ['IfcSlab']

    def __init__(self, *args, **kwargs):
        pass

    @attribute.multi_calc
    def _get_properties(self):
        result = dict(
            area=self.parent.area,
            thickness=self.parent.thickness,
            thermal_transmittance=self.parent.thermal_transmittance,
            is_external=self.parent.is_external
        )
        return result

    area = attribute.Attribute(
        name='area',
        functions=[_get_properties]
    )

    thickness = attribute.Attribute(
        name='thickness',
        functions=[_get_properties]
    )

    thermal_transmittance = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )

    is_external = attribute.Attribute(
        name='is_external',
        functions=[_get_properties]
    )


class SubRoof(Disaggregation):
    disaggregatable_elements = ['IfcRoof', 'IfcSlab']

    def __init__(self, *args, **kwargs):
        pass

    @attribute.multi_calc
    def _get_properties(self):
        result = dict(
            area=self.parent.area,
            thickness=self.parent.thickness,
            thermal_transmittance=self.parent.thermal_transmittance,
            is_external=self.parent.is_external
        )
        return result

    area = attribute.Attribute(
        name='area',
        functions=[_get_properties]
    )

    thickness = attribute.Attribute(
        name='thickness',
        functions=[_get_properties]
    )

    thermal_transmittance = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )

    is_external = attribute.Attribute(
        name='is_external',
        functions=[_get_properties]
    )


class SubWall(Disaggregation):
    disaggregatable_elements = ['IfcWall']

    def __init__(self, *args, **kwargs):
        pass

    @attribute.multi_calc
    def _get_properties(self):
        result = dict(
            area=self.parent.area,
            is_external=self.parent.is_external,
            thermal_transmittance=self.parent.thermal_transmittance,
            material=self.parent.material,
            thickness=self.parent.thickness,
            heat_capacity=self.parent.heat_capacity,
            density=self.parent.density

        )
        return result

    area = attribute.Attribute(
        name='area',
        functions=[_get_properties]
    )

    is_external = attribute.Attribute(
        name='is_external',
        functions=[_get_properties]
    )

    thermal_transmittance = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )

    material = attribute.Attribute(
        name='material',
        functions=[_get_properties]
    )

    thickness = attribute.Attribute(
        name='thickness',
        functions=[_get_properties]
    )

    heat_capacity = attribute.Attribute(
        name='heat_capacity',
        functions=[_get_properties]
    )

    density = attribute.Attribute(
        name='density',
        functions=[_get_properties]
    )

    tilt = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )


class SubInnerWall(Disaggregation):
    disaggregatable_elements = ['IfcWall']

    def __init__(self, *args, **kwargs):
        pass

    @attribute.multi_calc
    def _get_properties(self):
        result = dict(
            area=self.parent.area,
            is_external=self.parent.is_external,
            thermal_transmittance=self.parent.thermal_transmittance,
            material=self.parent.material,
            thickness=self.parent.thickness,
            heat_capacity=self.parent.heat_capacity,
            density=self.parent.density

        )
        return result

    area = attribute.Attribute(
        name='area',
        functions=[_get_properties]
    )

    is_external = attribute.Attribute(
        name='is_external',
        functions=[_get_properties]
    )

    thermal_transmittance = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )

    material = attribute.Attribute(
        name='material',
        functions=[_get_properties]
    )

    thickness = attribute.Attribute(
        name='thickness',
        functions=[_get_properties]
    )

    heat_capacity = attribute.Attribute(
        name='heat_capacity',
        functions=[_get_properties]
    )

    density = attribute.Attribute(
        name='density',
        functions=[_get_properties]
    )

    tilt = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )


class SubOuterWall(Disaggregation):
    disaggregatable_elements = ['IfcWall']

    def __init__(self, *args, **kwargs):
        pass

    @attribute.multi_calc
    def _get_properties(self):
        result = dict(
            area=self.parent.area,
            is_external=self.parent.is_external,
            thermal_transmittance=self.parent.thermal_transmittance,
            material=self.parent.material,
            thickness=self.parent.thickness,
            heat_capacity=self.parent.heat_capacity,
            density=self.parent.density

        )
        return result

    area = attribute.Attribute(
        name='area',
        functions=[_get_properties]
    )

    is_external = attribute.Attribute(
        name='is_external',
        functions=[_get_properties]
    )

    thermal_transmittance = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )

    material = attribute.Attribute(
        name='material',
        functions=[_get_properties]
    )

    thickness = attribute.Attribute(
        name='thickness',
        functions=[_get_properties]
    )

    heat_capacity = attribute.Attribute(
        name='heat_capacity',
        functions=[_get_properties]
    )

    density = attribute.Attribute(
        name='density',
        functions=[_get_properties]
    )

    tilt = attribute.Attribute(
        name='thermal_transmittance',
        functions=[_get_properties]
    )


def get_new_position_vertical_instance(parent, sub_position):
    rel_orientation_wall = math.floor(parent.orientation + parent.get_true_north())
    x1, y1, z1 = sub_position
    x, y, z = parent.position
    if 45 <= rel_orientation_wall < 135 or 225 <= rel_orientation_wall < 315:
        y1, z1, z1 = sub_position

    x = x - x1 * math.cos(math.radians(rel_orientation_wall))
    y = y - y1 * math.sin(math.radians(rel_orientation_wall))

    position = np.array([x, y, z])

    return position
