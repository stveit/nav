import pytest

from nav.models.arnold import Justification

from nav.auditlog import find_modelname
from nav.auditlog.models import LogEntry
from nav.auditlog.utils import get_auditlog_entries


class TestAuditlogModel():

    @pytest.fixture()
    def justification(self, db):
        justification = Justification.objects.create(name='testarossa')
        return justification

    def test_str(self, db, justification):
        LogEntry.add_log_entry(justification, u'str test', 'foo')
        l = LogEntry.objects.filter(verb='str test').get()
        assert str(l) == 'foo'

    def test_add_log_entry_bad_template(self, db, justification):
        LogEntry.add_log_entry(
            justification, u'bad template test', u'this is a {bad} template'
        )
        l = LogEntry.objects.filter(verb='bad template test').get()
        assert l.summary == u'Error creating summary - see error log'

    def test_add_log_entry_actor_only(self, db, justification):
        LogEntry.add_log_entry(
            justification, u'actor test', u'actor "{actor}" only is tested'
        )
        l = LogEntry.objects.filter(verb='actor test').get()
        assert l.summary == u'actor "testarossa" only is tested'

    def test_add_create_entry(self, db, justification):
        LogEntry.add_create_entry(justification, justification)
        l = LogEntry.objects.filter(verb=u'create-justification').get()
        assert l.summary == u'testarossa created testarossa'

    def test_add_delete_entry(self, db, justification):
        LogEntry.add_delete_entry(justification, justification)
        l = LogEntry.objects.filter(verb=u'delete-justification').get()
        assert l.summary == u'testarossa deleted testarossa'

    def test_compare_objects(self, db, justification):
        j1 = Justification.objects.create(name='ferrari', description='Psst!')
        j2 = Justification.objects.create(name='lambo', description='Hush')
        LogEntry.compare_objects(
            justification, j1, j2, ('name', 'description'), ('description',)
        )
        l = LogEntry.objects.filter(verb=u'edit-justification-name').get()
        assert  l.summary == u'testarossa edited lambo: name changed' u" from 'ferrari' to 'lambo'"
        l = LogEntry.objects.filter(verb=u'edit-justification-description').get()
        assert l.summary == u'testarossa edited lambo: description changed'

    def test_addLog_entry_before(self, db, justification):
        LogEntry.add_log_entry(justification, u'actor test', u'blbl', before=1)
        l = LogEntry.objects.filter(verb='actor test').get()
        assert l.before == u'1'

    def test_find_name(self, justification):
        name = find_modelname(justification)
        assert name == 'blocked_reason'


class TestAuditlogUtils():
    @pytest.fixture()
    def justification(self, db):
        justification = Justification.objects.create(name='testarossa')
        return justification

    def test_get_auditlog_entries(self, db, justification):
        modelname = 'blocked_reason'  # Justification's db_table
        j1 = Justification.objects.create(name='j1')
        j2 = Justification.objects.create(name='j2')
        LogEntry.add_create_entry(justification, j1)
        LogEntry.add_log_entry(
            justification,
            u'greet',
            u'{actor} greets {object}',
            object=j2,
            subsystem="hello",
        )
        LogEntry.add_log_entry(
            justification,
            u'deliver',
            u'{actor} delivers {object} to {target}',
            object=j1,
            target=j2,
            subsystem='delivery',
        )
        entries = get_auditlog_entries(modelname=modelname)
        assert entries.count() == 3
        entries = get_auditlog_entries(modelname=modelname, subsystem='hello')
        assert entries.count() == 1
        entries = get_auditlog_entries(modelname=modelname, pks=[j1.pk])
        assert entries.count() == 2
