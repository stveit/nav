from nav.portadmin.snmp.juniper import Juniper


def test_returns_correct_state_options(handler_juniper):
    state_options = handler_juniper.get_poe_state_options()
    assert Juniper.POE_ENABLED in state_options
    assert Juniper.POE_DISABLED in state_options
