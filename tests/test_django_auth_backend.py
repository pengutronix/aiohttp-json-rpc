import pytest

pytestmark = pytest.mark.django(reason='Depends on Django')


@pytest.fixture
def items(db):
    from django_project.models import Item

    for i in range(10):
        Item.objects.create(client_id=i, number=i)


@pytest.mark.asyncio
async def test_login(django_rpc_context, django_staff_user):
    from aiohttp_json_rpc.auth import login_required

    # setup rpc
    @login_required
    async def restricted_method(request):
        return True

    django_rpc_context.rpc.add_methods(('', restricted_method))

    # setup client
    client = await django_rpc_context.make_client()

    # run test
    # # without login
    methods = await client.call('get_methods')

    assert 'login' in methods
    assert 'restricted_method' not in methods

    # # after login login
    assert await client.call('login', {
        'username': 'admin',
        'password': 'admin',
    })

    methods = await client.call('get_methods')

    assert 'login' not in methods
    assert 'restricted_method' in methods


@pytest.mark.asyncio
async def test_generic_orm_methods(django_rpc_context, django_staff_user):
    client = await django_rpc_context.make_client()

    assert await client.call('login', {
        'username': 'admin',
        'password': 'admin',
    })

    methods = await client.call('get_methods')

    assert list(filter(lambda m: m.startswith('db__'), methods))


@pytest.mark.asyncio
async def test_generic_orm_view(django_rpc_context, django_staff_user, items):
    client = await django_rpc_context.make_client()

    assert await client.call('login', {
        'username': 'admin',
        'password': 'admin',
    })

    assert len(await client.call('db__django_project.view_item')) == 10

    items = await client.call('db__django_project.view_item', {
        'number__gt': 0,
        'number__lt': 9,
    })

    assert len(items) == 8


@pytest.mark.asyncio
async def test_generic_orm_delete(django_rpc_context, django_staff_user,
                                  items):

    client = await django_rpc_context.make_client()

    assert await client.call('login', {
        'username': 'admin',
        'password': 'admin',
    })

    assert len(await client.call('db__django_project.view_item')) == 10

    await client.call('db__django_project.delete_item', {
        'number__gt': 0,
        'number__lt': 9,
    })

    assert len(await client.call('db__django_project.view_item')) == 2


@pytest.mark.asyncio
async def test_generic_orm_add(django_rpc_context, django_staff_user, items):
    client = await django_rpc_context.make_client()

    assert await client.call('login', {
        'username': 'admin',
        'password': 'admin',
    })

    assert len(await client.call('db__django_project.view_item')) == 10

    new_item = await client.call('db__django_project.add_item', {
        'client_id': 100,
        'number': 100,
    })

    assert len(await client.call('db__django_project.view_item')) == 11

    assert await client.call('db__django_project.view_item', {
        'pk': new_item['pk'],
    })


@pytest.mark.asyncio
async def test_generic_orm_change(django_rpc_context, django_staff_user,
                                  items):

    client = await django_rpc_context.make_client()

    assert await client.call('login', {
        'username': 'admin',
        'password': 'admin',
    })

    item = (await client.call('db__django_project.view_item'))[0]

    assert await client.call('db__django_project.change_item', {
        'pk': item['pk'],
        'number': item['number'] + 1,
    })

    change_item = (await client.call('db__django_project.view_item', {
        'pk': item['pk'],
    }))[0]

    assert change_item['number'] == item['number'] + 1
