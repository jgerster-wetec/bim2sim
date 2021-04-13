import os

from bim2sim.kernel import ifc2python
from bim2sim.task.base import ITask
from bim2sim.kernel.units import ifcunits, ureg, ifc_pint_unitmap, parse_ifc
from ifcopenshell.file import file
from PluginIFCparser.Schema2Python import Schema2Python


class Reset(ITask):
    """Reset all progress"""

    touches = '__reset__'
    single_use = False

    @classmethod
    def requirements_met(cls, state, history):
        return bool(state)

    def run(self, workflow):
        return {}


class Quit(ITask):
    """Quit interactive tasks"""

    final = True
    single_use = False


class LoadIFC(ITask):
    """Load IFC file from PROJECT.ifc path (file or dir)"""
    reads = ('paths', )
    touches = ('ifc', )

    def run(self, workflow, paths):
        # TODO: use multiple ifs files

        path = paths.ifc

        if os.path.isdir(path):
            ifc_path = self.get_ifc(path)
        elif os.path.isfile(path):
            ifc_path = path
        else:
            raise AssertionError("No ifc found. Check '%s'" % path)
        ifc = ifc2python.load_ifc(os.path.abspath(ifc_path))

        ifcunits.update(**self.get_ifcunits(ifc))

        # Schema2Python.get_ifc_structure(ifc)

        self.logger.info("The exporter version of the IFC file is '%s'",
                         ifc.wrapped_data.header.file_name.originating_system)
        return ifc,

    def get_ifc(self, path):
        """Returns first ifc from ifc folder"""
        lst = []
        for file in os.listdir(path):
            if file.lower().endswith(".ifc"):
                lst.append(file)

        if len(lst) == 1:
            return os.path.join(path, lst[0])
        if len(lst) > 1:
            self.logger.warning("Found multiple ifc files. Selected '%s'.", lst[0])
            return os.path.join(path, lst[0])

        self.logger.error("No ifc found in project folder.")
        return None

    @staticmethod
    def get_ifcunits(ifc: file):
        """Returns dict with units available on ifc file"""

        unit_assignment = ifc.by_type('IfcUnitAssignment')

        results = {}

        for unit_entity in unit_assignment[0].Units:
            try:
                key = 'Ifc{}'.format(unit_entity.UnitType.capitalize().replace('unit', 'Measure'))
                pos_key = 'IfcPositive{}'.format(unit_entity.UnitType.capitalize().replace('unit', 'Measure'))
                unit = parse_ifc(unit_entity)
                results[key] = unit
                results[pos_key] = unit

                # unit_type = unit_entity.is_a()
                # if unit_type == 'IfcDerivedUnit':
                #     pass  # TODO: Implement
                # elif unit_type == 'IfcSIUnit':
                #     key = 'Ifc{}'.format(unit_entity.UnitType.capitalize().replace('unit', 'Measure'))
                #     prefix_string = unit_entity.Prefix.lower() if unit_entity.Prefix else ''
                #     unit = ureg.parse_units('{}{}'.format(prefix_string, ifc_pint_unitmap[unit_entity.Name]))
                #     if unit_entity.Dimensions:
                #         unit = unit**unit_entity.Dimensions
                #     results[key] = unit
                # elif unit_type == 'IfcConversionBasedUnit':
                #     pass  # TODO: Implement
                # elif unit_type == 'IfcMonetaryUnit':
                #     pass  # TODO: Implement
                # else:
                #     pass  # TODO: Implement
            except:
                print("Failed to parse %s" % unit_entity)

        return results
