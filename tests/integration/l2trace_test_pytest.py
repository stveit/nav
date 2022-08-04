from nav.models.manage import Netbox
from nav.models.manage import Vlan
from mock import Mock, patch
import types
import pytest

from django.core.management import call_command

from nav.web import l2trace
from nav.tests.cases import DjangoTransactionTestCase


@pytest.fixture()
def load_fixtures():
    call_command('loaddata', 'fixture_name.json')


@patch('nav.web.l2trace.Host.get_host_by_name', new=Mock(return_value=None))
@patch('nav.web.l2trace.Host.get_host_by_addr', new=Mock(return_value=None))
class L2traceTest():

    @pytest.fixture()
    def load_fixtures(self):
        fixtures = ['l2trace_fixture.xml']
        for fixture in fixtures:
            call_command('loaddata', fixture)

    @pytest.fixture()
    def foo_sw1(self, load_fixtures):
        foo_sw1 = Netbox.objects.get(sysname='foo-sw1.example.org')
        return foo_sw1

    @pytest.fixture()
    def foo_gw(self, load_fixtures):
        foo_gw = Netbox.objects.get(sysname='foo-gw.example.org')
        return foo_gw

    @pytest.fixture()
    def employee_vlan(self, load_fixtures):
        employee_vlan = Vlan.objects.get(net_ident='employeevlan')
        return employee_vlan

    @pytest.fixture()
    def admin_vlan(self, load_fixtures):
        admin_vlan = Vlan.objects.get(net_ident='adminvlan')
        return admin_vlan


class TestGetVlanFromThings(L2traceTest):
    def test_arbitrary_ip_is_on_vlan_10(self, load_fixtures):
        vlan = l2trace.get_vlan_from_ip('10.0.0.99')
        assert vlan is not None
        assert vlan.vlan == 10
        assert vlan.net_ident == 'adminvlan'

    def test_router_is_on_vlan_10(self, load_fixtures):
        host = l2trace.Host('10.0.0.1')
        vlan = l2trace.get_vlan_from_host(host)
        assert vlan is not None
        assert vlan.vlan == 10
        assert vlan.net_ident == 'adminvlan'

    def test_switch_is_on_vlan_10(self, load_fixtures, foo_sw1):
        vlan = l2trace.get_netbox_vlan(foo_sw1)
        assert vlan is not None
        assert vlan.vlan == 10
        assert vlan.net_ident == 'adminvlan'


class TestNetboxFromHost(L2traceTest):
    def test_known_ip_is_router(self, load_fixtures):
        host = l2trace.Host('10.0.0.1')
        found = l2trace.get_netbox_from_host(host)
        assert found is not None
        assert found.sysname == 'foo-gw.example.org'

    def test_unknown_ip_gives_none_as_result(self, load_fixtures):
        unknown_host = l2trace.Host('10.0.0.99')
        assert l2trace.get_netbox_from_host(unknown_host) is None

    def test_known_ip_is_netbox(self, load_fixtures):
        h = l2trace.get_host_or_netbox_from_addr('10.0.0.1')
        assert hasattr(h, 'sysname')
        assert h.sysname == 'foo-gw.example.org'

    def test_unknown_ip_is_host(self, load_fixtures):
        ip = '10.99.99.99'
        h = l2trace.get_host_or_netbox_from_addr(ip)
        assert hasattr(h, 'hostname')
        assert h.hostname == ip


class TestGateway(L2traceTest):
    def test_foo_gw_is_router_for_employee_vlan(self, load_fixtures, foo_gw, employee_vlan):
        assert l2trace.get_vlan_gateway(employee_vlan) == foo_gw

    def test_foo_gw_is_router_for_admin_vlan(self, load_fixtures, admin_vlan, foo_gw):
        assert l2trace.get_vlan_gateway(admin_vlan) == foo_gw

    def test_foo_gw_is_router(self, load_fixtures, foo_gw):
        assert l2trace.is_netbox_gateway(foo_gw)

    def test_foo_sw1_is_not_a_router(self, load_fixtures, foo_sw1):
        assert not l2trace.is_netbox_gateway(foo_sw1)


class TestVlanEquality(L2traceTest):
    def test_ips_should_be_on_same_vlan(self, load_fixtures):
        assert l2trace.are_hosts_on_same_vlan('10.0.0.1', '10.0.0.2')

    def test_ips_should_not_be_on_same_vlan(self, load_fixtures):
        assert not l2trace.are_hosts_on_same_vlan('10.0.20.1', '10.0.0.2')


class TestDownlink(L2traceTest):
    def test_employee1_downlink_should_be_foo_sw1_gi_0_10(self, load_fixtures, foo_sw1):
        host = l2trace.Host('10.0.20.10')
        host.hostname = 'employee10.example.org'

        swpvlan = l2trace.get_vlan_downlink_to_host(host)
        assert swpvlan is not None
        assert swpvlan.interface.ifname == 'Gi0/10'
        assert swpvlan.interface.netbox == foo_sw1
        assert swpvlan.vlan.vlan == 20

    def test_foo_sw1_vlan_downlink_should_be_on_foo_gw_gi_0_13(self, load_fixtures, foo_sw1, foo_gw):
        swpvlan = l2trace.get_vlan_downlink_to_netbox(foo_sw1)
        assert swpvlan is not None
        assert swpvlan.vlan.vlan == 10
        assert swpvlan.interface.ifname == 'Gi0/13'
        assert swpvlan.interface.netbox == foo_gw

    def test_foo_sw1_employee_vlan_uplink_should_be_foo_gw_gi_0_13(self, load_fixtures, foo_gw, foo_sw1, employee_vlan):
        swpvlan = l2trace.get_vlan_downlink_to_netbox(foo_sw1, employee_vlan)
        assert swpvlan is not None
        assert swpvlan.vlan.vlan == 20
        assert swpvlan.interface.ifname == 'Gi0/13'
        assert swpvlan.interface.netbox == foo_gw


class UplinkTests(L2traceTest):
    def test_foo_sw1_vlan_uplink_should_be_gi_0_1(self):
        swpvlan = l2trace.get_vlan_uplink_from_netbox(self.foo_sw1)
        self.assertTrue(swpvlan is not None)
        self.assertEqual(swpvlan.vlan.vlan, 10)
        self.assertEqual(swpvlan.interface.ifname, 'Gi0/1')

    def test_foo_sw1_employee_vlan_uplink_should_be_gi_0_1(self):
        vlan = self.employee_vlan
        swpvlan = l2trace.get_vlan_uplink_from_netbox(self.foo_sw1, vlan)
        self.assertTrue(swpvlan is not None)
        self.assertEqual(swpvlan.vlan, vlan)
        self.assertEqual(swpvlan.interface.ifname, 'Gi0/1')


class HostTests(L2traceTest):
    def test_host_without_resolvable_name(self):
        ip = '10.99.99.99'
        h = l2trace.Host(ip)
        self.assertEqual(h.host, ip)
        self.assertEqual(h.ip, ip)
        self.assertEqual(h.hostname, ip)

    def test_hosts_are_equal(self):
        host1 = l2trace.Host('10.99.99.99')
        host2 = l2trace.Host('10.99.99.99')
        self.assertEqual(host1, host2)

    def test_host_with_host_argument_returns_equal_instance(self):
        host1 = l2trace.Host('10.99.99.99')
        host2 = l2trace.Host(host1)
        self.assertEqual(host1, host2)


class StartPathTests(L2traceTest):
    def test_start_path_for_foo_sw1_ip_should_be_on_vlan_10(self):
        node = l2trace.get_start_path('10.0.0.11')
        self.assertTrue(node is not None)
        self.assertEqual(node.vlan.vlan, 10)
        self.assertTrue(node.if_in is None)
        self.assertTrue(isinstance(node.host, Netbox))
        self.assertEqual(node.host.sysname, 'foo-sw1.example.org')

    def test_start_path_for_employee1_should_be_on_vlan_20(self):
        ip = '10.0.20.10'
        node = l2trace.get_start_path(ip)
        self.assertTrue(node is not None)
        self.assertEqual(node.vlan.vlan, 20)
        self.assertTrue(node.if_in is None)
        self.assertTrue(isinstance(node.host, l2trace.Host))
        self.assertEqual(node.host.hostname, ip)
        self.assertTrue(node.if_out is None)


class PathTests(L2traceTest):
    def test_path_for_foo_sw1_should_be_2_long(self):
        path = l2trace.get_path(self.foo_sw1.ip)
        self.assertEqual(len(path), 2)

    def test_path_for_foo_sw1_should_start_with_foo_sw1(self):
        path = l2trace.get_path(self.foo_sw1.ip)
        self.assertEqual(path[0].host, self.foo_sw1)

    def test_path_for_foo_sw1_should_end_at_foo_gw(self):
        path = l2trace.get_path(self.foo_sw1.ip)
        self.assertEqual(path[-1].host, self.foo_gw)

    def test_path_for_foo_sw1_should_be_on_vlan_10(self):
        path = l2trace.get_path(self.foo_sw1.ip)
        self.assertEqual(path[0].vlan.vlan, 10)
        self.assertEqual(path[1].vlan.vlan, 10)

    def test_path_for_employee1_should_be_3_long(self):
        path = l2trace.get_path('10.0.20.10')
        self.assertEqual(len(path), 3)

    def test_path_for_employee2_should_be_3_long(self):
        path = l2trace.get_path('10.0.20.90')
        self.assertEqual(len(path), 3, path)

    def test_path_for_employee1_should_be_on_vlan_20(self):
        path = l2trace.get_path('10.0.20.10')
        self.assertEqual(path[0].vlan.vlan, 20)
        self.assertEqual(path[1].vlan.vlan, 20)

    def test_path_for_employee1_should_start_with_employee_1(self):
        path = l2trace.get_path('10.0.20.10')
        self.assertTrue(isinstance(path[0].host, l2trace.Host))

    def test_path_for_employee1_should_end_with_foo_gw(self):
        path = l2trace.get_path('10.0.20.10')
        self.assertEqual(path[-1].host, self.foo_gw)


class TraceTests(L2traceTest):
    def test_make_rows_returns_generator(self):
        tracequery = l2trace.L2TraceQuery('10.0.20.10', '')
        tracequery.trace()
        self.assertIsInstance(tracequery.make_rows(), types.GeneratorType)

    def test_make_rows_generates_result_rows(self):
        tracequery = l2trace.L2TraceQuery('10.0.20.10', '')
        tracequery.trace()
        generator = tracequery.make_rows()
        first = next(generator)
        self.assertTrue(isinstance(first, l2trace.ResultRow))

    def test_first_row_is_host_from(self):
        ip = '10.0.20.10'
        tracequery = l2trace.L2TraceQuery(ip, '')
        tracequery.trace()
        first_row = next(tracequery.make_rows())
        self.assertEqual(first_row.sysname, ip)

    def test_first_and_last_rows_match_hosts(self):
        ip1 = '10.0.20.10'
        ip2 = '10.0.20.90'
        tracequery = l2trace.L2TraceQuery(ip1, ip2)
        tracequery.trace()
        rows = list(tracequery.make_rows())
        self.assertEqual(rows[0].sysname, ip1, tracequery.path)
        self.assertEqual(rows[-1].sysname, ip2, tracequery.path)

    def test_employee_path_passes_through_foo_sw1(self):
        ip1 = '10.0.20.10'
        ip2 = '10.0.20.90'
        tracequery = l2trace.L2TraceQuery(ip1, ip2)
        tracequery.trace()
        rows = list(tracequery.make_rows())
        self.assertEqual(len(rows), 3, rows)
        switch_row = rows[1]

        self.assertEqual(switch_row.sysname, 'foo-sw1.example.org')

    def test_should_not_fail_on_invalid_hosts(self):
        tracequery = l2trace.L2TraceQuery('s;dfl', '923urfk\';')
        tracequery.trace()
        list(tracequery.make_rows())


class JunctionTests(L2traceTest):
    def setUp(self):
        super(JunctionTests, self).setUp()
        Host = l2trace.Host
        self.from_path = [
            l2trace.PathNode(None, None, Host('10.0.20.10'), None),
            l2trace.PathNode(None, None, self.foo_sw1, None),
            l2trace.PathNode(None, None, self.foo_gw, None),
        ]

        self.to_path = [
            l2trace.PathNode(None, None, self.foo_gw, None),
            l2trace.PathNode(None, None, self.foo_sw1, None),
            l2trace.PathNode(None, None, Host('10.0.20.90'), None),
        ]

    def test_find_junction_should_return_same_host(self):
        (node1, node2) = l2trace.find_junction(self.from_path, self.to_path)
        self.assertEqual(node1.host, node2.host)

    def test_find_junction_should_return_foo_sw1(self):
        (node1, node2) = l2trace.find_junction(self.from_path, self.to_path)
        self.assertEqual(node1.host, self.foo_sw1)
        self.assertEqual(node2.host, self.foo_sw1)

    def test_find_junction_should_return_nodes_from_paths(self):
        (from_node, to_node) = l2trace.find_junction(self.from_path, self.to_path)
        self.assertTrue(from_node in self.from_path)
        self.assertTrue(to_node in self.to_path)

    def test_join_at_junction_should_be_3_long(self):
        new_path = l2trace.join_at_junction(self.from_path, self.to_path)
        self.assertEqual(len(new_path), 3, new_path)

    def test_joined_path_should_start_and_end_with_correct_hosts(self):
        new_path = l2trace.join_at_junction(self.from_path, self.to_path)
        self.assertEqual(new_path[0], self.from_path[0])
        self.assertEqual(new_path[-1], self.to_path[-1])
