from datetime import datetime, timedelta, date

from django.db.models import fields, Q as _Q, F as _F

from django.db.models.expressions import (
        CombinedExpression as _CombinedExpression,
        Value as _Value,
        DurationValue,
)


class Q(_Q):
    def __eq__(self, other):
        if not self.__class__ == other.__class__:
            return False

        return ((self.connector, self.negated, self.children) ==
                (other.connector, other.negated, other.children))


class CombinedExpression(_CombinedExpression):
    def __eq__(self, other):
        if not self.__class__ == other.__class__:
            return False

        return (self.lhs, self.rhs) == (other.lhs, other.rhs)


class Value(_Value):
    def __eq__(self, other):
        if not self.__class__ == other.__class__:
            return False

        return self.value == other.value


class F(_F):
    def __eq__(self, other):
        if not self.__class__ == other.__class__:
            return False

        return self.name == other.name

    def _combine(self, other, connector, reversed, node=None):
        if not hasattr(other, 'resolve_expression'):
            if isinstance(other, timedelta):
                other = DurationValue(other,
                                      output_field=fields.DurationField())
            else:
                other = Value(other)

        if reversed:
            return CombinedExpression(other, connector, self)

        return CombinedExpression(self, connector, other)


LOGIC_CONNECTORS = {
    'AND': lambda a, b: a & b,
    'OR': lambda a, b: a | b,
}

ARITHMETIC_CONNECTORS = {
    '+': lambda a, b: a + b,
    '-': lambda a, b: a - b,
    '*': lambda a, b: a * b,
    '/': lambda a, b: a / b,
    '%': lambda a, b: a % b,
}

FUNCTIONS = {
    'F': F,
    'date': date,
    'date_today': date.today,
    'datetime': datetime,
    'datetime_now': datetime.now,
    'datetime_today': datetime.today,
    'timedelta': timedelta,
}

OPERATIONS = [
    'filter',
    'exclude',
]


def parse_function_call(value):
    """
    ['!F', 'a']
    ['!datetime', 1970, 1, 1, 10, 0, 0]
    ['!timedelta', {'days': 3}]
    """

    name = value.pop(0)[1:]
    kwargs = {}

    for index, v in enumerate(value):
        if isinstance(v, dict):
            value.pop(index)
            kwargs.update(v)

    try:
        return FUNCTIONS[name](*value, **kwargs)

    except KeyError:
        raise ValueError('function "{}" is unknown'.format(name))


def parse_value(raw_value):
    if not isinstance(raw_value, list):
        return raw_value

    if(len(raw_value) > 0 and
       isinstance(raw_value[0], str) and
       raw_value[0].startswith('!')):

        return parse_function_call(raw_value)

    for index, value in enumerate(raw_value):
        raw_value[index] = parse_value(value)

    # arithmetic
    if not set(ARITHMETIC_CONNECTORS.keys()) & set(raw_value):
        return raw_value

    value = raw_value[0]

    for index in range(1, len(raw_value)):
        if not isinstance(raw_value[index], str):
            continue

        connector = raw_value[index].strip().lower()

        if connector in ARITHMETIC_CONNECTORS:
            value = ARITHMETIC_CONNECTORS[connector](value,
                                                     raw_value[index + 1])

            index += 1

    return value


def parse_q(raw_q):
    """
    {'a': 1}
    """

    lookups = {}

    for field, value in raw_q.items():
        if field in lookups:
            raise ValueError('lookup "{}" repeated'.format(field))

        lookups[field] = parse_value(value)

    return Q(**lookups)


def parse_q_list(raw_q_list):
    """
    ['NOT', {'a': 1}]
    [{'a': 1}, {'b': 1}]
    [{'a': 1}, 'OR', {'b': 1}]

    """

    for index, value in enumerate(raw_q_list):
        if isinstance(value, dict):  # raw_q
            raw_q_list[index] = parse_q(value)

        elif isinstance(value, list):  # raw_q_list
            raw_q_list[index] = parse_q_list(value)

        elif isinstance(value, str):  # connector
            value = value.upper()

            if value not in LOGIC_CONNECTORS and value != 'NOT':
                raise ValueError(
                    'unsupported connector "{}"'.format(value))

            raw_q_list[index] = value

        else:
            raise ValueError('unsupported type "{}"'.format(value))

    q = None
    connector = LOGIC_CONNECTORS['AND']
    negate = False

    for i in raw_q_list:
        if isinstance(i, str):
            if i == 'NOT':
                negate = True
                continue

            connector = LOGIC_CONNECTORS[i]
            continue

        if q is None:
            q = i

        else:
            q = connector(q, i)

        if negate:
            q = ~q
            negate = False

    return q


def parse_query(query):
    if not isinstance(query, (dict, list)):
        raise ValueError('query has to be dict or list')

    if not isinstance(query, list):
        query = [query]

    return parse_q_list(query)


def parse_operations(operation_list):
    """
    ['filter', {'a': 1}, 'exclude', {'b': 1}]
    ['filter', {'a': 1}, 'exclude', {'b': 1}, 'values']
    """

    operation = 'filter'

    if not isinstance(operation_list[0], str):
        operation_list.insert(0, 'filter')

    for index, chunk in enumerate(operation_list):
        if index % 2 == 0:  # chunk is an operation keyword
            chunk = chunk.strip().lower()

            if chunk not in OPERATIONS:
                raise ValueError('operation "{}" unknown'.format(chunk))

            operation = chunk

        else:  # chunk is a query list
            yield operation, parse_query(chunk)
