#
# Copyright (C) 2022 Sikt AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#

import napalm
import pytest
from unittest.mock import Mock, patch

from jnpr.junos.exception import RpcError
from lxml import etree

from nav.enterprise.ids import VENDOR_ID_RESERVED, VENDOR_ID_JUNIPER_NETWORKS_INC
from nav.models import manage
from nav.portadmin.handlers import (
    DeviceNotConfigurableError,
    ProtocolError,
    POEStateNotSupportedError,
)
from nav.portadmin.napalm.juniper import wrap_unhandled_rpc_errors, Juniper


@pytest.fixture()
def netbox_mock():
    """Create netbox model mock object"""
    netbox = Mock()
    netbox.ip = '10.0.0.1'
    netbox.type.get_enterprise_id.return_value = VENDOR_ID_JUNIPER_NETWORKS_INC
    yield netbox


@pytest.fixture()
def profile_mock():
    """Create management profile model mock object"""
    profile = Mock()
    profile.protocol = manage.ManagementProfile.PROTOCOL_NAPALM
    profile.PROTOCOL_NAPALM = manage.ManagementProfile.PROTOCOL_NAPALM
    profile.configuration = {"driver": "mock"}
    yield profile


@pytest.fixture()
def handler_mock(netbox_mock, profile_mock):
    """Create management handler mock object"""
    juniper = Juniper(netbox=netbox_mock)
    juniper._profile = profile_mock
    yield juniper


@pytest.fixture()
def xml(interface1_mock):
    """Creates a ElementTree containing poe information for one interface"""
    tree_string = f"""
        <poe>
            <interface-information-detail>
                <interface-name-detail>{interface1_mock.ifname}</interface-name-detail>
                <interface-enabled-detail>Enabled</interface-enabled-detail>
            </interface-information-detail>
        </poe>"""
    tree = etree.fromstring(tree_string)
    yield tree


@pytest.fixture()
def xml_bulk(interface1_mock, interface2_mock):
    """Creates a ElementTree containing poe information for two interfaces"""
    tree_string = f"""
        <poe>
            <interface-information>
                <interface-name>{interface1_mock.ifname}</interface-name>
                <interface-enabled>Enabled</interface-enabled>
            </interface-information>
            <interface-information>
                <interface-name>{interface2_mock.ifname}</interface-name>
                <interface-enabled>Disabled</interface-enabled>
            </interface-information>
        </poe>"""
    tree = etree.fromstring(tree_string)
    yield tree


@pytest.fixture()
def interface1_mock():
    interface = Mock()
    interface.ifname = "ge-0/0/1"
    interface.ifindex = 1
    yield interface


@pytest.fixture()
def interface2_mock():
    interface = Mock()
    interface.ifname = "ge-0/0/2"
    interface.ifindex = 2
    yield interface


class TestWrapUnhandledRpcErrors:
    def test_rpcerrors_should_become_protocolerrors(self):
        @wrap_unhandled_rpc_errors
        def wrapped_function():
            raise RpcError("bogus")

        with pytest.raises(ProtocolError):
            wrapped_function()

    def test_non_rpcerrors_should_pass_through(self):
        @wrap_unhandled_rpc_errors
        def wrapped_function():
            raise TypeError("bogus")

        with pytest.raises(TypeError):
            wrapped_function()


class TestJuniper:
    def test_juniper_device_returns_device_connection(self, handler_mock):
        driver = napalm.get_network_driver('mock')
        device = driver(
            hostname='foo',
            username='user',
            password='pass',
            optional_args={},
        )
        device.open()
        assert handler_mock.device

    def test_juniper_device_raises_error_if_vendor_not_juniper(
        self, netbox_mock, profile_mock
    ):
        netbox_mock.type.get_enterprise_id.return_value = VENDOR_ID_RESERVED
        juniper = Juniper(netbox=netbox_mock)
        juniper._profile = profile_mock

        with pytest.raises(DeviceNotConfigurableError):
            juniper.device

    def test_juniper_device_raises_error_if_no_connected_profile(self, netbox_mock):
        juniper = Juniper(netbox=netbox_mock)
        netbox_mock.profiles.filter.return_value.first.return_value = None

        with pytest.raises(DeviceNotConfigurableError):
            juniper.device

    @patch('nav.models.manage.Vlan.objects', Mock(return_value=[]))
    def test_get_netbox_vlans_should_ignore_vlans_with_non_integer_tags(self):
        """Regression test for #2452"""

        class MockedJuniperHandler(Juniper):
            @property
            def vlans(self):
                """Mock a VLAN table response from the device"""
                return [Mock(tag='NA'), Mock(tag='10')]

        m = MockedJuniperHandler(Mock())
        assert len(m.get_netbox_vlans()) == 1


class TestJuniperPoe:
    def test_returns_correct_state_options(self, handler_mock):
        state_options = handler_mock.get_poe_state_options()
        assert Juniper.POE_ENABLED in state_options
        assert Juniper.POE_DISABLED in state_options

    def test_state_converter_returns_correct_states(self, handler_mock):
        assert handler_mock._poe_string_to_state("enabled") == Juniper.POE_ENABLED
        assert handler_mock._poe_string_to_state("disabled") == Juniper.POE_DISABLED

    def test_state_converter_raises_error_for_invalid_states(self, handler_mock):
        with pytest.raises(POEStateNotSupportedError):
            handler_mock._poe_string_to_state("invalid_state")

    def test_get_poe_state_for_one_interface_returns_correct_state(
        self, handler_mock, xml, interface1_mock
    ):
        handler_mock._get_poe_interface_information = Mock(return_value=xml)
        state = handler_mock._get_poe_state(interface1_mock)
        assert state == Juniper.POE_ENABLED

    def test_get_poe_states_bulk_returns_correct_states(
        self, handler_mock, xml_bulk, interface1_mock, interface2_mock
    ):
        handler_mock._get_all_poe_interface_information = Mock(return_value=xml_bulk)
        states = handler_mock._get_poe_states_bulk([interface1_mock, interface2_mock])
        assert states[interface1_mock.ifindex] == Juniper.POE_ENABLED
        assert states[interface2_mock.ifindex] == Juniper.POE_DISABLED

    def test_get_poe_states_bulk_maps_interface_to_none_if_poe_not_supported(
        self, handler_mock, xml_bulk
    ):
        handler_mock._get_all_poe_interface_information = Mock(return_value=xml_bulk)
        if_mock = Mock()
        if_mock.ifname == "random_if"
        if_mock.ifindex = 0
        states = handler_mock._get_poe_states_bulk([if_mock])
        assert states[if_mock.ifindex] is None

    def test_get_poe_states_returns_empty_dict_with_empty_input(self, handler_mock):
        assert handler_mock.get_poe_states([]) == {}

    def test_get_poe_state_uses_interfaces_from_db_if_input_is_none(self):
        pass

    def test_get_poe_state_raises_exception_if_no_interfaces_in_xml(self):
        pass

    def test_get_poe_state_raises_exception_if_multiple_interfaces_in_xml(self):
        pass

    def test_get_poe_states_bulk_returns_empty_dict_if_no_interfaces_in_xml(self):
        pass
