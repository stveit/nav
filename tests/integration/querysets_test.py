import datetime as dt

import pytest

from nav.models.event import AlertHistory
from nav.models.event import AlertHistoryVariable
from nav.models.event import EventType
from nav.models.event import Subsystem
from nav.models.fields import INFINITY
from nav.models.manage import Netbox
from nav.models.manage import Category
from nav.models.manage import Room
from nav.models.manage import Organization


class TestNetboxQueryset():
    @pytest.fixture()
    def netboxes(self, db):
        # Some rows have already been created
        _netbox_data = {
            "room": Room.objects.get(id="myroom"),
            "organization": Organization.objects.get(id="myorg"),
            "category": Category.objects.get(id="SW"),
        }
        TEST_NETBOX_DATA = [
            dict(sysname="foo.bar.com", ip="158.38.152.169", **_netbox_data),
            dict(sysname="bar.bar.com", ip="158.38.152.231", **_netbox_data),
            dict(sysname="spam.bar.com", ip="158.38.152.9", **_netbox_data),
        ]

        netboxes = [
            Netbox.objects.create(**netbox_data) for netbox_data in TEST_NETBOX_DATA
        ]
        ah = AlertHistory.objects.create(
            source=Subsystem.objects.first(),
            netbox=netboxes[2],
            event_type=EventType.objects.get(id="maintenanceState"),
            start_time=dt.datetime.now(),
            value=0,
            end_time=INFINITY,  # UNRESOLVED
            severity=3,
        )
        AlertHistoryVariable.objects.create(alert_history=ah, variable="netbox")
        return netboxes

    def test_on_maintenance_true(self, netboxes):
        on_maintenance = Netbox.objects.on_maintenance(True)
        assert on_maintenance.count() == 1
        assert on_maintenance[0] == netboxes[2]

    def test_on_maintenance_false(self, netboxes):
        # A netbox not used in this test has already been created
        not_on_maintenance = Netbox.objects.on_maintenance(False)
        assert netboxes[0] in not_on_maintenance
        assert netboxes[1] in not_on_maintenance
        assert not netboxes[2] in not_on_maintenance
