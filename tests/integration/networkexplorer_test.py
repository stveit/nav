import pytest

from nav.web.networkexplorer import search
from nav.web.networkexplorer.forms import NetworkSearchForm
from nav.web.networkexplorer.views import (
    IndexView,
    RouterJSONView,
    SearchView,
)

from django.test.client import RequestFactory


class TestNetworkExplorerSearch():
    """Tests that the various network explorer search functions don't raise
    database exceptions.

    Will not cover all code paths on an empty database.

    """

    def test_search_expand_swport(self):
        search.search_expand_swport(1)

    def test_search_expand_netbox(self):
        search.search_expand_netbox(1)

    def test_search_expand_sysname(self):
        search.search_expand_sysname('foo-gw.example.org')

    def test_search_expand_mac(self):
        search.search_expand_mac('00:12:34:56:78:90')

    def test_sysname_search(self):
        search.sysname_search('foo-gw.example.org')

    def test_ip_search(self):
        search.ip_search('10.0.1')

    def test_ip_search_exact(self):
        search.ip_search('10.0.1.0', exact=True)

    def test_portname_search(self):
        search.portname_search('KX182')

    def test_portname_search_exact(self):
        search.portname_search('KX182', exact=True)

    def test_room_search(self):
        search.room_search('myroom')

    def test_room_search_exact(self):
        search.room_search('myroom', exact=True)

    def test_mac_search(self):
        search.mac_search('00:12:34:56:78:90')

    def test_vlan_search(self):
        search.vlan_search('20')

    def test_vlan_search_exact(self):
        search.vlan_search('20', exact=True)

@pytest.fixture()
def valid_data():
    valid_data = {
        'query_0': 'somequery',
        'query_1': 'sysname',
    }
    return valid_data

@pytest.fixture()
def invalid_data():
    invalid_data = {
        'query_0': 'somequery',
        # Missing query type
    }
    return invalid_data

@pytest.fixture()
def url_root():
    url_root = '/networkexplorer/'
    return url_root

class TestViews():

    @pytest.fixture()
    def factory(self):
        factory = RequestFactory()
        return factory

    def test_index_view(self, factory, url_root):
        request = factory.get(url_root)
        response = IndexView.as_view()(request)
        assert response.status_code == 200

    def test_router_json_view(self, factory, url_root):
        request = factory.get(url_root + 'routers/')
        response = RouterJSONView.as_view()(request)
        assert response.status_code == 200

    def test_search_view_with_valid_query(self, factory, valid_data, url_root):
        request = factory.get(
            url_root + 'search/',
            valid_data,
        )
        response = SearchView.as_view()(request)
        content = response.content.decode('utf-8')
        assert response.status_code == 200
        assert 'routers' in content
        assert 'gwports' in content
        assert 'swports' in content

    def test_search_view_with_invalid_query(self, factory, invalid_data, url_root):
        request = factory.get(
            url_root + 'search/',
            invalid_data,
        )
        response = SearchView.as_view()(request)
        content = response.content.decode('utf-8')
        assert response.status_code == 200
        assert not 'routers' in content
        assert not 'gwports' in content
        assert not 'swports' in content


class TestForms():
    def test_search_form(self, valid_data, invalid_data):
        valid_form = NetworkSearchForm(valid_data)
        invalid_form = NetworkSearchForm(invalid_data)
        assert valid_form.is_valid(), 'Valid form failed validaion'
        assert not invalid_form.is_valid(), 'Invalid form passed validation'
