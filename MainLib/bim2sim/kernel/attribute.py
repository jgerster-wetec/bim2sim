import logging
from contextlib import contextmanager

import pint
import re

from bim2sim.decision import RealDecision, BoolDecision, ListDecision
from bim2sim.task.bps_f.bps_functions import get_matches_list

from bim2sim.kernel.units import ureg

logger = logging.getLogger(__name__)
quality_logger = logging.getLogger('bim2sim.QualityReport')


class AutoAttributeNameMeta(type):
    """Detect setting on Attributes on class level and set name as given"""
    def __init__(cls, name, bases, namespace):
        super(AutoAttributeNameMeta, cls).__init__(name, bases, namespace)
        for name, obj in namespace.items():
            if isinstance(obj, Attribute):
                obj.name = name

    # def __setattr__(cls, name, value):
    #     if isinstance(value, Attribute):
    #         value.name = name
    #         print(name)
    #     return super().__setattr__(name, value)


class Attribute:
    """Descriptor of element attribute

    value and status of attribute are stored in __dict__ of bound instance"""
    # https://rszalski.github.io/magicmethods/
    STATUS_UNKNOWN = 'UNKNOWN'
    STATUS_REQUESTED = 'REQUESTED'
    STATUS_AVAILABLE = 'AVAILABLE'
    STATUS_NOT_AVAILABLE = 'NOT_AVAILABLE'
    _force = False

    def __init__(self, name=None,
                 description="",
                 unit=None,
                 default_ps=None,
                 default_association=None,
                 patterns=None,
                 ifc_postprocessing=None,
                 functions=None,
                 default=None):
        if name:
            logger.warning("'name' is obsolete. Remove name '%s'" % name)
        self.name = None  # auto set by AutoAttributeNameMeta
        self.description = description
        self.unit = unit

        self.default_ps = default_ps
        self.default_association = default_association
        self.patterns = patterns
        self.functions = functions
        self.default_value = default

        if ifc_postprocessing:
            self.ifc_post_processing = ifc_postprocessing

        # TODO argument for validation function

    def _get_value(self, bind):
        value = None
        # default property set
        if value is None and self.default_ps:
            raw_value = self.get_from_default_propertyset(bind, self.name)
            value = self.ifc_post_processing(raw_value)
            if value is None:
                quality_logger.warning("Attribute '%s' of %s %s was not found in default PropertySet",
                                       self.name, bind.ifc_type, bind.guid)

        if value is None and (self.default_association):
            raw_value = self.get_from_default_assocation(bind, self.default_association)
            value = self.ifc_post_processing(raw_value)
            if value is None:
                quality_logger.warning("Attribute '%s' of %s %s was not found in default Association",
                                       self.name, bind.ifc_type, bind.guid)
        # tool specific properties (finder)
        if value is None:
            raw_value = self.get_from_finder(bind, self.name)
            value = self.ifc_post_processing(raw_value)

        # custom properties by patterns
        if value is None and self.patterns:
            raw_value = self.get_from_patterns(bind, self.patterns, self.name)
            value = self.ifc_post_processing(raw_value)

        # custom functions
        if value is None and self.functions:
            value = self.get_from_functions(bind, self.functions, self.name)

        # # enrichment
        # if value is None:
        #     value = self.get_from_enrichment(bind, self.name)

        # default value
        if value is None and self.default_value:
            value = self.default_value
            if value and self.unit:
                value = value * self.unit

        # check unit
        if self.unit is not None and value is not None and not isinstance(value, pint.Quantity):
            logger.warning("Unit not set!")
            value = value * self.unit

        return value

    @staticmethod
    def get_from_default_propertyset(bind, name):
        source_tools = bind.finder.templates
        if bind.source_tool in source_tools:
            source_tool = bind.source_tool
        else:
            possible_source_tools = get_matches_list(bind.source_tool, source_tools.keys(), False)
            if possible_source_tools:
                decision_source_tool = ListDecision("Multiple templates found for source tool %s" % bind.source_tool,
                                                    choices=list(possible_source_tools),
                                                    allow_skip=True, allow_load=True, allow_save=True,
                                                    collect=False, quick_decide=not True)
                decision_source_tool.decide()
                source_tool = decision_source_tool.value
            else:
                source_tool = 'base'
            bind._tool = source_tool
            bind.get_project().OwnerHistory.OwningApplication.ApplicationFullName = source_tool
        try:
            default = source_tools[source_tool][type(bind).__name__]['default_ps'][name]
        except KeyError:
            return None
        try:
            value = bind.get_exact_property(default[0], default[1])
        except Exception:
            value = None
        return value

    @staticmethod
    def get_from_default_assocation(bind, default):
        try:
            value = bind.get_exact_association(default[0], default[1])
        except Exception:
            value = None
        return value

    @staticmethod
    def get_from_finder(bind, name):
        finder = getattr(bind, 'finder', None)
        if finder:  # Aggregations have no finder
            try:
                return bind.finder.find(bind, name)
            except (AttributeError, TypeError):
                pass
        return None

    @staticmethod
    def get_from_patterns(bind, patterns, name):
        # TODO: prevent decision on call by get()
        value = bind.select_from_potential_properties(patterns, name, False)
        return value

    @staticmethod
    def get_from_functions(bind, functions, name):
        value = None
        for i, func in enumerate(functions):
            try:
                value = func(bind, name)
            except Exception as ex:
                logger.error("Function %d of %s.%s raised %s", i, bind, name, ex)
                pass
            else:
                break
        return value

    @staticmethod
    def get_from_enrichment(bind, name):
        value = None
        if hasattr(bind, 'enrichment') and bind.enrichment:
            attrs_enrich = bind.enrichment["enrichment_data"]
            if "enrich_decision" not in bind.enrichment:
                # check if want to enrich instance
                enrichment_decision = BoolDecision(
                    question="Do you want for %s_%s to be enriched" % (bind.ifc_type, bind.guid),
                    collect=False)
                enrichment_decision.decide()
                enrichment_decision.stored_decisions.clear()
                bind.enrichment["enrich_decision"] = enrichment_decision.value

            if bind.enrichment["enrich_decision"]:
                # enrichment via incomplete data (has enrich parameter value)
                if name in attrs_enrich:
                    value = attrs_enrich[name]
                    if value is not None:
                        return value
                if "selected_enrichment_data" not in bind.enrichment:
                    options_enrich_parameter = list(attrs_enrich.keys())
                    decision1 = ListDecision("Multiple possibilities found",
                                             choices=options_enrich_parameter,
                                             global_key="%s_%s.Enrich_Parameter" % (bind.ifc_type, bind.guid),
                                             allow_skip=True, allow_load=True, allow_save=True,
                                             collect=False, quick_decide=not True)
                    decision1.decide()
                    decision1.stored_decisions.clear()

                    if decision1.value == 'statistical_year':
                        # 3. check if general enrichment - construction year
                        bind.enrichment["selected_enrichment_data"] = bind.enrichment["year_enrichment"]
                    else:
                        # specific enrichment (enrichment parameter and values)
                        decision2 = RealDecision("Enter value for the parameter %s" % decision1.value,
                                                 validate_func=lambda x: isinstance(x, float),  # TODO
                                                 global_key="%s" % decision1.value,
                                                 allow_skip=False, allow_load=True, allow_save=True,
                                                 collect=False, quick_decide=False)
                        decision2.decide()
                        delta = float("inf")
                        decision2_selected = None
                        for ele in attrs_enrich[decision1.value]:
                            if abs(int(ele) - decision2.value) < delta:
                                delta = abs(int(ele) - decision2.value)
                                decision2_selected = int(ele)

                        bind.enrichment["selected_enrichment_data"] = attrs_enrich[str(decision1.value)][
                            str(decision2_selected)]
                value = bind.enrichment["selected_enrichment_data"][name]
        return value

    @staticmethod
    def get_from_decision(bind, name):
        # TODO: decision
        decision = RealDecision(
            "Enter value for %s of %s" % (name, bind.name),
            # output=self,
            # output_key=name,
            global_key="%s_%s.%s" % (bind.ifc_type, bind.guid, name),
            allow_skip=False, allow_load=True, allow_save=True,
            validate_func=lambda x: True,  # TODO meaningful validation
            collect=False,
            quick_decide=True
        )
        value = decision.value
        return value

    def create_decision(self, bind, collect=True):
        """Created Decision for this Attribute"""
        # TODO: set state in output dict -> attributemanager
        decision = RealDecision(
            "Enter value for %s of %s" % (self.name, bind.name),
            # validate_func=lambda x: isinstance(x, float),
            output=bind.attributes,
            output_key=self.name,
            global_key="%s_%s.%s" % (bind.ifc_type, bind.guid, self.name),
            allow_skip=False, allow_load=True, allow_save=True,
            validate_func=lambda x: True,  # TODO meaningful validation
            collect=collect,
            unit=self.unit,
        )
        return decision

    @staticmethod
    @contextmanager
    def force_get():
        """Contextmanager to get missing attributes immediately"""
        Attribute._force = True
        yield
        Attribute._force = False

    @staticmethod
    def ifc_post_processing(value):
        """Function for post processing of ifc property values (e.g. diameter list -> diameter)
        by default this function does nothing"""
        return value

    def request(self, bind):
        """Request attribute"""

        # read current value and status
        value, status = self._inner_get(bind)

        if value is None:
            if status == Attribute.STATUS_NOT_AVAILABLE:
                # actual request
                decision = self.create_decision(bind)
                bind.related_decisions.append(decision)
                status = Attribute.STATUS_REQUESTED
                self._inner_set(bind, value, status)
                return decision
        else:
            # already requested or available
            return

    def initialize(self, manager):
        if not self.name:
            print(self)
            raise AttributeError("Attribute.name not set!")

        manager[self.name] = (None, self.STATUS_UNKNOWN)

    def _inner_get(self, bind):
        return bind.attributes[self.name]

    def _inner_set(self, bind, value, status):
        # TODO: validate
        bind.attributes[self.name] = (value, status)

    def __get__(self, bind, owner):
        if bind is None:
            return self

        # read current value and status
        value, status = self._inner_get(bind)
        changed = False

        if value is None and status == self.STATUS_UNKNOWN:
            value = self._get_value(bind)
            status = self.STATUS_AVAILABLE if value else self.STATUS_NOT_AVAILABLE
            changed = True

        if self._force and value is None:
            value = self.get_from_decision(bind, self.name)
            status = Attribute.STATUS_AVAILABLE
            changed = True

        if changed:
            # write back new value and status
            self._inner_set(bind, value, status)

        return value

    def __set__(self, bind, value):
        if self.unit:
            if isinstance(value, ureg.Quantity):
                _value = value.to(self.unit)
            else:
                _value = value * self.unit
        else:
            _value = value
        self._inner_set(bind, _value, self.STATUS_AVAILABLE)

    def __str__(self):
        return "Attribute %s" % self.name


class AttributeManager(dict):
    """Attribute Manager class"""

    def __init__(self, bind):
        super().__init__()
        self.bind = bind

        for name in self.names:
            attr = self.get_attribute(name)
            attr.initialize(self)

    def __setitem__(self, name, value):
        if name not in self.names:
            raise AttributeError("Invalid Attribute '%s'. Choices are %s" % (name, list(self.names)))

        if isinstance(value, tuple) and len(value) == 2:
            super().__setitem__(name, value)
        else:
            super().__setitem__(name, (value, Attribute.STATUS_AVAILABLE))

    def update(self, other):
        # dict.update does not invoke __setitem__
        for k, v in other.items():
            self.__setitem__(k, v)

    def request(self, name=None):
        """Request attribute by name. (name=None -> all)"""
        if name:
            names = [name]
        else:
            names = self.names

        for n in names:
            try:
                attr = self.get_attribute(n)
            except KeyError:
                raise KeyError("%s has no Attribute '%s'" % (self.bind, n))

            value, status = self[n]
            if value is None:
                if status == Attribute.STATUS_NOT_AVAILABLE:
                    decision = attr.request(self.bind)
                    # self.bind.related_decisions.append(decision)
        else:
            # already requested or available
            return

    def get_attribute(self, name):
        return getattr(type(self.bind), name)

    def get_unit(self, name):
        attr = self.get_attribute(name)
        return attr.unit

    @property
    def names(self):
        return (name for name in dir(type(self.bind)) if isinstance(getattr(type(self.bind), name), Attribute))


def multi_calc(func):
    """Decorator for calculation of multiple Attribute values"""

    def wrapper(bind, name):
        # inner function call
        result = func(bind)
        value = result.pop(name)
        # send all other result values to AttributeManager instance
        bind.attributes.update(result)
        return value

    return wrapper
