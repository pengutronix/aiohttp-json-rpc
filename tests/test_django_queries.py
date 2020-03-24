import pytest

pytestmark = pytest.mark.django(reason='Depends on Django')


@pytest.mark.dependency
def test_Q_compares():
    from aiohttp_json_rpc.django.utils.query import Q

    assert Q(a=1) == Q(a=1)
    assert ~Q(a=1) == ~Q(a=1)
    assert Q(a=1) != Q(a=2)
    assert Q(a=1) != ~Q(a=1)
    assert Q(a=1) != Q(a=2, b=1)


@pytest.mark.dependency
def test_F_compares():
    from aiohttp_json_rpc.django.utils.query import F

    assert F(1) == F(1)
    assert F(1) + 1 == F(1) + 1
    assert F(1) + 1 != F(1) + 2
    assert F(1) != F(2)
    assert F(1) != F(F(1))


@pytest.mark.dependency(depends=['test_Q_compares', 'test_F_compares'])
def test_F_in_Q_compares():
    from aiohttp_json_rpc.django.utils.query import F, Q

    assert Q(a=F('b')) == Q(a=F('b'))
    assert Q(a=F('b')) != Q(a=F('c'))


@pytest.mark.dependency(depends=['test_Q_compares', 'test_F_compares'])
def test_parse_q():
    from aiohttp_json_rpc.django.utils.query import Q, parse_q

    assert parse_q({'a': 1}) == Q(a=1)
    assert parse_q({'a': 1, 'b': 2}) == Q(a=1, b=2)


@pytest.mark.dependency(depends=['test_parse_q'])
def test_parse_q_list():
    from aiohttp_json_rpc.django.utils.query import Q, parse_q_list

    assert parse_q_list([{'a': 1}, {'a': 2}]) == Q(a=1) & Q(a=2)
    assert parse_q_list([{'a': 1}, {'b': 2}]) == Q(a=1) & Q(b=2)
    assert parse_q_list([{'a': 1}, 'OR', {'a': 2}]) == Q(a=1) | Q(a=2)
    assert parse_q_list(['NOT', {'a': 1}, 'OR', {'a': 2}]) == ~Q(a=1) | Q(a=2)


@pytest.mark.dependency(depends=['test_F_compares'])
def test_parse_value():
    from datetime import datetime, timedelta

    from aiohttp_json_rpc.django.utils.query import F, parse_value

    assert parse_value(['!F', 1]) == F(1)
    assert parse_value(['F', 1]) == ['F', 1]

    assert parse_value(
        ['!datetime', 1970, 1, 1, 0, 0, 0]) == datetime(1970, 1, 1, 0, 0, 0)

    assert parse_value(['!timedelta', {'hours': 2}]) == timedelta(hours=2)

    assert parse_value([1]) == [1]
    assert parse_value([1, 2]) == [1, 2]
    assert parse_value(1) == 1

    assert parse_value([['!F', 1], '+', 1]) == F(1) + 1
