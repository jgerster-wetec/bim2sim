"""
Decision system.

This package contains:
    - class Decision (and child classes) for representing decisions
    - class DecisionBunch for handling collections of Decision instances
    - class DecisionHandler to handle decisions
    - functions save() and load() to save to file system
    """

import logging
import enum
import json
import hashlib
from collections import Counter
from typing import Iterable, Callable, List, Dict, Any

import pint

from bim2sim.kernel.units import ureg


__VERSION__ = '0.1'
logger = logging.getLogger(__name__)


class DecisionException(Exception):
    """Base Exception for Decisions"""


class DecisionSkip(DecisionException):
    """Exception raised on skipping Decision"""


class DecisionSkipAll(DecisionException):
    """Exception raised on skipping all Decisions"""


class DecisionCancel(DecisionException):
    """Exception raised on canceling Decisions"""


class PendingDecisionError(DecisionException):
    """Exception for unsolved Decisions"""


class Status(enum.Enum):
    """Enum for status of Decision"""
    open = 1  # decision not yet made
    ok = 2  # decision made
    skipped = 5  # decision was skipped
    error = 6  # invalid answer


def convert_0_to_0_1(data):
    converted_data = {
        'version': '0.1',
        'checksum_ifc': None,
        'decisions': {decision: {'value': value} for decision, value in data.items()}
    }
    return converted_data


def convert(from_version, to_version, data):
    """convert stored decisions to new version"""
    if from_version == '0' and to_version == '0.1':
        return convert_0_to_0_1(data)


class Decision:
    """A question and a value which should be set to answer the question.

    Example:
        decision = Decision("How much is the fish?", allow_skip=True)
        decision.value  # will raise ValueError
        decision.value = 10  # ok
        decision.value = 12  # value cant be changed, will raise ValueError
        decision.reset()  # reset to initial state
        decision.skip()  # set value to None, only works if allow_skip flag set
    """

    SKIP = "skip"
    SKIPALL = "skip all"
    CANCEL = "cancel"
    options = [SKIP, SKIPALL, CANCEL]

    def __init__(self, question: str, validate_func: Callable = None,
                 key: str = None, global_key: str = None,
                 allow_skip=False, validate_checksum=None,
                 related: List[str] = None, context: List[str] = None,
                 default=None, group: str = None):

        """
        :param question: The question asked to the user
        :param validate_func: callable to validate the users input
        :param key: key is used by DecisionBunch to create answer dict
        :param global_key: unique key to identify decision. Required for saving
        :param allow_skip: set to True to allow skipping the decision and user None as value
        :param validate_checksum: if provided, loaded decisions are only valid if checksum matches
        :param related: iterable of GUIDs this decision is related to (frontend)
        :param context: iterable of GUIDs for additional context to this decision (frontend)
        :param default: default answer
        :param group: group of decisions this decision belongs to
        :raises: :class:'AttributeError'::
        """
        self.status = Status.open
        self._value = None

        self.question = question
        self.validate_func = validate_func
        self.default = None
        if default is not None:
            if self.validate(default):
                self.default = default
            else:
                logger.warning("Invalid default value (%s) for %s: %s",
                               default, self.__class__.__name__, self.question)

        self.key = key
        self.global_key = global_key

        self.allow_skip = allow_skip
        self.allow_save_load = bool(global_key)

        self.validate_checksum = validate_checksum

        self.related = related
        self.context = context

        self.group = group

    @property
    def value(self):
        """Answer value of decision.

        Getting the value will raise a ValueError until set with valid value."""
        if self.valid():
            return self._value
        else:
            raise ValueError("Can't get value from invalid decision.")

    @value.setter
    def value(self, value):
        if self.status != Status.open:
            raise ValueError("Decision is not open. Call reset() first.")
        _value = self.convert(value)
        if _value is None:
            self.skip()
        elif self.validate(_value):
            self._value = _value
            self.status = Status.ok
        else:
            raise ValueError("Invalid value: %r for %s" % (value, self.question))

    def reset(self):
        self.status = Status.open
        self._value = None

    def skip(self):
        """Set value to None und mark as solved."""
        if not self.allow_skip:
            raise DecisionException("This Decision can not be skipped.")
        if self.status != Status.open:
            raise DecisionException(
                "This Decision is not open. Call reset() first.")
        self._value = None
        self.status = Status.skipped

    @staticmethod
    def build_checksum(item):
        """Create checksum for item."""
        return hashlib.md5(json.dumps(item, sort_keys=True)
                           .encode('utf-8')).hexdigest()

    def convert(self, value):
        """Convert value to inner type"""
        return value

    def _validate(self, value):
        raise NotImplementedError("Implement method _validate!")

    def validate(self, value):
        """Checks value with validate_func and returns truth value"""
        _value = self.convert(value)
        basic_valid = self._validate(_value)

        if self.validate_func:
            try:
                external_valid = bool(self.validate_func(_value))
            except:
                external_valid = False
        else:
            external_valid = True

        return basic_valid and external_valid

    def valid(self):
        return self.status == Status.ok \
               or (self.status == Status.skipped and self.allow_skip)

    def reset_from_deserialized(self, kwargs):
        """Reset decision from its serialized form."""
        value = kwargs['value']
        checksum = kwargs.get('checksum')
        if value is None:
            return
        if (not self.validate_func) or self.validate_func(value):
            if checksum == self.validate_checksum:
                self.value = self.deserialize_value(value)
                self.status = Status.ok
                logger.info("Loaded decision '%s' with value: %s", self.global_key, value)
            else:
                logger.warning("Checksum mismatch for loaded decision '%s", self.global_key)
        else:
            logger.warning("Check for loaded decision '%s' failed. Loaded value: %s",
                           self.global_key, value)

    def serialize_value(self):
        """Return JSON serializable value."""
        return {'value': self.value}

    def deserialize_value(self, value):
        """rebuild value from json deserialized object"""
        return value

    def get_serializable(self):
        """Returns json serializable object representing state of decision"""
        kwargs = self.serialize_value()
        if self.validate_checksum:
            kwargs['checksum'] = self.validate_checksum
        return kwargs

    def get_options(self):
        options = [Decision.CANCEL]
        if self.allow_skip:
            options.append(Decision.SKIP)

        return options

    def get_question(self):
        return self.question

    def get_body(self):
        """Returns list of tuples representing items of CollectionDecision else None"""
        return None

    def __repr__(self):
        value = str(self.value) if self.status == Status.ok else '???'
        return '<%s (<%s> Q: "%s" A: %s)>' % (
            self.__class__.__name__, self.status, self.question, value)


class RealDecision(Decision):
    """Accepts input of type real"""

    def __init__(self, *args, unit=None, **kwargs):
        """"""
        self.unit = unit if unit else ureg.dimensionless
        default = kwargs.get('default')
        if default is not None and not isinstance(default, pint.Quantity):
            kwargs['default'] = default * self.unit
        super().__init__(*args, **kwargs)

    def convert(self, value):
        if not isinstance(value, pint.Quantity):
            try:
                return value * self.unit
            except:
                pass
        return value

    def _validate(self, value):
        if isinstance(value, pint.Quantity):
            try:
                float(value.m)
            except:
                pass
            else:
                return True
        return False

    def get_question(self):
        return "{} in [{}]".format(self.question, self.unit)

    def get_body(self):
        return {'unit': str(self.unit)}

    def get_debug_answer(self):
        answer = super().get_debug_answer()
        if isinstance(answer, pint.Quantity):
            return answer.to(self.unit)
        return answer * self.unit

    def serialize_value(self):
        kwargs = {
            'value': self.value.magnitude,
            'unit': str(self.value.units)
        }
        return kwargs

    def reset_from_deserialized(self, kwargs):
        kwargs['value'] = kwargs['value'] * ureg[kwargs.pop('unit', str(self.unit))]
        super().reset_from_deserialized(kwargs)


class BoolDecision(Decision):
    """Accepts input convertable as bool"""

    POSITIVES = ("y", "yes", "ja", "j", "1")
    NEGATIVES = ("n", "no", "nein", "n", "0")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate_func=None, **kwargs)

    @staticmethod
    def _validate(value):
        """validates if value is acceptable as bool"""
        return value is True or value is False


class ListDecision(Decision):
    """Accepts index of list element as input.

    Choices is a list of either
      - values, str(value) is used for label
      - tuples of (value, label)"""

    def __init__(self, *args, choices, **kwargs):
        if not choices:
            raise AttributeError("choices must hold at least one item")
        if hasattr(choices[0], '__len__') and len(choices[0]) == 2:
            self.items = [choice[0] for choice in choices]
            self.labels = [str(choice[1]) for choice in choices]
        else:
            self.items = choices
            # self.labels = [str(choice) for choice in self.items]

        super().__init__(*args, validate_func=None, **kwargs)

        if len(self.items) == 1:
            if not self.status != Status.open:
                # set only item as default
                if self.default is None:
                    self.default = self.items[0]

    @property
    def choices(self):
        if hasattr(self, 'labels'):
            return zip(self.items, self.labels)
        else:
            return self.items

    def _validate(self, value):
        pass  # _validate not required. see validate

    def validate(self, value):
        return value in self.items

    def get_body(self):
        body = []
        for i, item in enumerate(self.choices):
            if isinstance(item, (list, tuple)) and len(item) == 2:
                # label provided
                body.append((i, *item))
            else:
                # no label provided
                body.append((i, item, ' '))
        return body


class StringDecision(Decision):
    """Accepts string input"""

    def __init__(self, *args, min_length=1, **kwargs):
        self.min_length = min_length
        super().__init__(*args, **kwargs)

    def _validate(self, value):
        return isinstance(value, str) and len(value) >= self.min_length


class GuidDecision(Decision):
    """Accepts GUID(s) as input. Value is a set of GUID(s)"""

    def __init__(self, *args, multi=False, **kwargs):
        self.multi = multi
        super().__init__(*args, **kwargs)

    def _validate(self, value):
        if isinstance(value, set) and value:
            if not self.multi and len(value) != 1:
                return False
            return all(isinstance(guid, str) and len(guid) == 22 for guid in value)
        return False

    def serialize_value(self):
        return {'value': list(self.value)}

    def deserialize_value(self, value):
        return set(value)


class DecisionBunch(list):
    """Collection of decisions."""

    def __init__(self, decisions: Iterable[Decision] = ()):
        super().__init__(decisions)

    def valid(self) -> bool:
        """Check status of all decisions."""
        return all(decision.status in (Status.ok, Status.skipped)
                   for decision in self)

    def to_answer_dict(self) -> Dict[Any, Decision]:
        """Create dict from DecisionBunch using decision.key."""
        return {decision.key: decision.value for decision in self}

    def to_serializable(self) -> dict:
        """Create JSON serializable dict of decisions."""
        decisions = {decision.global_key: decision.get_serializable()
                     for decision in self}
        return decisions

    def validate_global_keys(self):
        """Check if all global keys are unique.

        :raises: AssertionError on bad keys."""
        # mapping = {decision.global_key: decision for decision in self}
        count = Counter(item.global_key for item in self if item.global_key)
        duplicates = {decision for (decision, v) in count.items() if v > 1}

        if duplicates:
            raise AssertionError("Following global keys are not unique: %s",
                                 duplicates)


def save(bunch: DecisionBunch, path):
    """Save solved Decisions to file system"""

    logger = logging.getLogger(__name__)

    decisions = bunch.to_serializable()
    data = {
        'version': __VERSION__,
        'checksum_ifc': None,
        'decisions': decisions,
    }
    with open(path, "w") as file:
        json.dump(data, file, indent=2)
    logger.info("Saved %d decisions.", len(bunch))


def load(path) -> Dict[str, Any]:
    """Load previously solved Decisions from file system."""

    logger = logging.getLogger(__name__)
    try:
        with open(path, "r") as file:
            data = json.load(file)
    except IOError as ex:
        logger.info("Unable to load decisions. (%s)", ex)
        return {}
    version = data.get('version', '0')
    if version != __VERSION__:
        try:
            data = convert(version, __VERSION__, data)
            logger.info("Converted stored decisions from version '%s' to '%s'", version, __VERSION__)
        except:
            logger.error("Decision conversion from %s to %s failed")
            return {}
    decisions = data.get('decisions')
    logger.info("Found %d previous made decisions.", len(decisions or []))
    return decisions
