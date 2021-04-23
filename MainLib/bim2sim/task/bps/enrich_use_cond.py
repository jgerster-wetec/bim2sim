from bim2sim.task.base import Task, ITask
from bim2sim.task.common.common_functions import get_usage_dict, get_pattern_usage
from bim2sim.decision import ListDecision
from bim2sim.workflow import Workflow
from bim2sim.kernel.elements import ThermalZone
from bim2sim.kernel.units import ureg

UseConditions = get_usage_dict()


class EnrichUseConditions(ITask):
    """Enriches Use Conditions of thermal zones
    based on decisions and translation of zone names"""

    reads = ('tz_instances',)
    touches = ('enriched_tz',)

    def __init__(self):
        super().__init__()
        self.enriched_tz = []

    @Task.log
    def run(self, workflow: Workflow, tz_instances: dict):
        self.logger.info("enriches thermal zones usage")
        # case no thermal zones found
        if len(tz_instances) == 0:
            self.logger.warning("Found no spaces to bind")
        else:
            self.multi_zone_usage(tz_instances)
            self.logger.info("obtained %d thermal zones", len(self.enriched_tz))

        return self.enriched_tz,

    def multi_zone_usage(self, thermal_zones: dict):
        """defines an usage to a determined thermal zone"""
        pattern_usage = get_pattern_usage()
        for tz in list(thermal_zones.values()):
            if tz.usage not in pattern_usage:
                matches = []
                list_org = tz.usage.replace(' (', ' ').replace(')', ' '). \
                    replace(' -', ' ').replace(', ', ' ').split()
                for usage, patterns in pattern_usage.items():  # optimize this
                    for i in patterns:
                        for i_name in list_org:
                            if i.match(i_name):
                                if usage not in matches:
                                    matches.append(usage)
                # if just a match given
                if len(matches) == 1:
                    # case its an office
                    if 'office_function' == matches[0]:
                        tz.usage = self.office_usage(tz)
                    # other zone usage
                    else:
                        tz.usage = matches[0]
                    self.load_usage(tz)
                    self.enriched_tz.append(tz)
                    continue
                # if no matches given
                elif len(matches) == 0:
                    matches = list(pattern_usage.keys())
                tz.usage = self.list_decision_usage(tz, matches)
                self.load_usage(tz)
                self.enriched_tz.append(tz)

    # def one_zone_usage(self, thermal_zones: dict):
    #     """defines an usage to all the building - since its a singular zone"""
    #     usage_decision = ListDecision("Which usage does the one_zone_building %s have?",
    #                                   choices=list(UseConditions.keys()),
    #                                   global_key="one_zone_usage",
    #                                   allow_skip=False,
    #                                   allow_load=True,
    #                                   allow_save=True,
    #                                   quick_decide=not True)
    #     usage_decision.decide()
    #     for tz in list(thermal_zones.values()):
    #         tz.usage = usage_decision.value
    #         self.enriched_tz.append(tz)

    def office_usage(self, tz: ThermalZone):
        """function to determine which office corresponds based on the area of the thermal zone and the table on:
        https://skepp.com/en/blog/office-tips/this-is-how-many-square-meters-of-office-space-you-need-per-person"""

        default_matches = ["Single office", "Group Office (between 2 and 6 employees)",
                           "Open-plan Office (7 or more employees)"]
        area = tz.area.m
        # case area its available
        if area is not None:
            if area <= 7:
                return default_matches[0]
            elif 7 < area <= 42:
                return default_matches[1]
            else:
                return default_matches[2]
        # case area not available
        else:
            self.list_decision_usage(tz, default_matches)

    @staticmethod
    def list_decision_usage(tz: ThermalZone, matches: list):
        """decision to select an usage that matches the zone name"""
        usage_decision = ListDecision("Which usage does the Space %s have?" %
                                      (str(tz.usage)),
                                      choices=matches,
                                      global_key="%s_%s.BpsUsage" % (type(tz).__name__, tz.guid),
                                      allow_skip=False,
                                      allow_load=True,
                                      allow_save=True,
                                      quick_decide=not True)
        usage_decision.decide()
        return usage_decision.value

    def load_usage(self, tz: ThermalZone):
        bool_overwriter = ['with_cooling', 'with_heating', 'with_ahu']
        list_overwriter = {'heating_profile': [25, 't_set_heat'], 'cooling_profile': [25, 't_set_cool']}
        # heating, cooling profile
        use_condition = UseConditions[tz.usage]
        for attr in bool_overwriter:
            overwrite_attr = getattr(tz, attr)
            if overwrite_attr is not None:
                use_condition[attr] = overwrite_attr

        for attr, value in list_overwriter.items():
            overwrite_attr = getattr(tz, value[1]).to(ureg.kelvin).m
            if overwrite_attr is not None:
                use_condition[attr] = [overwrite_attr] * value[0]

        self.check_use_condition(use_condition)
        setattr(tz, 'use_condition', use_condition)

    @staticmethod
    def check_use_condition(use_condition: dict):
        # check if dict, because it can be division dict like
        # {"/":[1,15]}, or float value
        for attr, value in use_condition.items():
            if isinstance(value, dict):
                values = next(iter(value.values()))
                division_res = values[0]/values[1]
                use_condition[attr] = division_res

