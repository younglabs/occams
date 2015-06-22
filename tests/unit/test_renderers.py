from ddt import ddt, data, unpack
import wtforms.fields.html5
import wtforms.ext.dateutil.fields

from occams_forms.fields import FileField

from tests import IntegrationFixture


class annotatedlist(list):
    pass


def expect_type(type_, class_):
    r = annotatedlist([type_, class_])
    setattr(r, '__name__', 'test_types_%s_to_%s' % (type_, class_.__name__))
    return r


@ddt
class TestMakeField(IntegrationFixture):

    def test_unknown(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        attribute = models.Attribute(name=u'f', title=u'F', type='unknown')
        with self.assertRaises(Exception):
            make_field(attribute)

    @data(
        expect_type('string', wtforms.StringField),
        expect_type('text', wtforms.TextAreaField),
        expect_type('blob', FileField),
        expect_type('date', wtforms.ext.dateutil.fields.DateField),
        expect_type('datetime', wtforms.ext.dateutil.fields.DateTimeField),
        expect_type('section', wtforms.FormField))
    @unpack
    def test_basic_types(self, type_, class_):
        from occams_forms import models
        from occams_forms.renderers import make_field
        attribute = models.Attribute(name=u'f', title=u'F', type=type_)
        field = make_field(attribute)
        self.assertIs(field.field_class, class_)

    def test_integer(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        attribute = models.Attribute(
            name=u'f', title=u'F', type='number', decimal_places=0)
        field = make_field(attribute)
        self.assertIs(field.field_class, wtforms.fields.html5.IntegerField)

    def test_decimal_any(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        attribute = models.Attribute(name=u'f', title=u'F', type='number')
        field = make_field(attribute)
        self.assertIs(field.field_class, wtforms.fields.html5.DecimalField)

    def test_decimal_precision(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        attribute = models.Attribute(
            name=u'f', title=u'F', type='number', decimal_places=1)
        field = make_field(attribute)
        self.assertIs(field.field_class, wtforms.fields.html5.DecimalField)

    def test_choice_single(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        attribute = models.Attribute(
            name=u'f', title=u'F', type='choice', is_collection=False)
        field = make_field(attribute)
        self.assertIs(field.field_class, wtforms.SelectField)

    def test_choice_multi(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        attribute = models.Attribute(
            name=u'f', title=u'F', type='choice', is_collection=True)
        field = make_field(attribute)
        self.assertIs(field.field_class, wtforms.SelectMultipleField)

    def test_string_min_max(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        import wtforms
        from wtforms.validators import Length
        attribute = models.Attribute(
            name=u'string_test', title=u'string_test', type='string',
            value_min=1, value_max=12)
        field = make_field(attribute)
        field = field.bind(wtforms.Form(), attribute.name)
        self.assertTrue(
            any(isinstance(v, Length) for v in field.validators))

    def test_number_min_max(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        import wtforms
        from wtforms.validators import NumberRange
        attribute = models.Attribute(
            name=u'number_test', title=u'number_test', type='number',
            value_min=1, value_max=12)
        field = make_field(attribute)
        field = field.bind(wtforms.Form(), attribute.name)
        self.assertTrue(
            any(isinstance(v, NumberRange) for v in field.validators))

    def test_daterange_date(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        import wtforms
        from wtforms_components import DateRange
        attribute = models.Attribute(
            name=u'daterange_test', title=u'daterange_test', type='date')
        field = make_field(attribute)
        field = field.bind(wtforms.Form(), attribute.name)
        self.assertTrue(
            any(isinstance(v, DateRange) for v in field.validators))

    def test_daterange_datetime(self):
        from occams_forms import models
        from occams_forms.renderers import make_field
        import wtforms
        from wtforms_components import DateRange
        attribute = models.Attribute(
            name=u'daterange_test', title=u'daterange_test', type='datetime')
        field = make_field(attribute)
        field = field.bind(wtforms.Form(), attribute.name)
        self.assertTrue(
            any(isinstance(v, DateRange) for v in field.validators))


class TestMakeForm(IntegrationFixture):

    def _make_schema(self):
        from datetime import date
        from occams_forms import models, Session
        schema = models.Schema(
            name=u'dymmy_schema',
            title=u'Dummy Schema',
            publish_date=date.today(),
            attributes={
                'dummy_field': models.Attribute(
                    name=u'dummy_field',
                    title=u'Dummy Field',
                    type='string',
                    is_required=True,
                    order=0
                )
            })

        Session.add(schema)
        Session.flush()

        return schema

    def test_skip_validation_if_pending_entry(self):
        from webob.multidict import MultiDict
        from occams_forms import Session
        from occams_forms.renderers import make_form, states, modes

        schema = self._make_schema()
        Form = make_form(Session, schema, transition=modes.ALL)
        form = Form(MultiDict({
            'ofworkflow_-state': states.PENDING_ENTRY,
        }))
        self.assertTrue(form.validate(), form.errors)

    def test_skip_validation_if_not_collected(self):
        from datetime import date
        from webob.multidict import MultiDict
        from occams_forms import Session
        from occams_forms.renderers import make_form

        schema = self._make_schema()
        Form = make_form(Session, schema)

        form = Form(MultiDict({
            'ofmetadata_-collect_date': str(date.today()),
            'ofmetadata_-version': str(schema.publish_date),
            'ofmetadata_-not_done': '1',
        }))
        self.assertTrue(form.validate(), form.errors)

    def test_validation_if_collected(self):
        from datetime import date
        from webob.multidict import MultiDict
        from occams_forms import Session
        from occams_forms.renderers import make_form

        schema = self._make_schema()
        Form = make_form(Session, schema)

        form = Form(MultiDict({
            'ofmetadata_-collect_date': str(date.today()),
            'ofmetadata_-version': str(schema.publish_date),
            'ofmetadata_-not_done': '',
        }))

        self.assertFalse(form.validate())
        self.assertIn('dummy_field', form.errors)


@ddt
class TestRenderForm(IntegrationFixture):

    def setUp(self):
        super(TestRenderForm, self).setUp()
        self.config.include('pyramid_chameleon')

    def _make_form(self):
        from datetime import date
        from occams_forms import models, Session
        from occams_forms.renderers import make_form

        schema = models.Schema(
            name=u'dymmy_schema',
            title=u'Dummy Schema',
            publish_date=date.today(),
            attributes={
                'dummy_field': models.Attribute(
                    name=u'dummy_field',
                    title=u'Dummy Field',
                    type='string',
                    order=0
                )
            })

        entity = models.Entity(schema=schema)
        Session.add(entity)
        Session.flush()

        return make_form(Session, schema, entity=entity)

    @data('pending-entry', 'pending-review', 'pending-correction')
    def test_enabled_for_editable_states(self, state):

        from occams_forms import models, Session
        from occams_forms.renderers import render_form
        from bs4 import BeautifulSoup

        Form = self._make_form()
        form = Form()

        form.meta.entity.state = (
            Session.query(models.State)
            .filter_by(name=state)
            .one())

        markup = render_form(form)
        soup = BeautifulSoup(markup)

        field = soup.find(id='dummy_field')

        self.assertFalse(field.has_attr('disabled'))

    def test_disabled_if_complete(self):

        from occams_forms import models, Session
        from occams_forms.renderers import render_form, states
        from bs4 import BeautifulSoup

        Form = self._make_form()
        form = Form()

        form.meta.entity.state = (
            Session.query(models.State)
            .filter_by(name=states.COMPLETE)
            .one())

        markup = render_form(form)
        soup = BeautifulSoup(markup)

        field = soup.find(id='dummy_field')

        self.assertTrue(field.has_attr('disabled'))


class TestApplyData(IntegrationFixture):

    def setUp(self):
        super(TestApplyData, self).setUp()
        import tempfile
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _call(self, *args, **kw):
        from occams_forms.renderers import apply_data
        return apply_data(*args, **kw)

    def _make_entity(self):
        from datetime import date
        from occams_forms import models
        schema = models.Schema(
            name=u'test', title=u'', publish_date=date.today(),
            attributes={
                'q1': models.Attribute(
                    name=u'q1',
                    title=u'',
                    type='string',
                    order=0,
                )
            })
        entity = models.Entity(schema=schema)
        return entity

    def test_clear_if_not_done(self):
        from datetime import date
        from occams_forms import Session

        entity = self._make_entity()
        entity['q1'] = u'Some value'

        formdata = {'ofmetadata_': {
            'not_done': True,
            'collect_date': date.today(),
            'version': entity.schema.publish_date
        }}

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertIsNone(entity['q1'])

    def test_clear_if_pending_entry(self):
        from datetime import date
        from occams_forms import Session
        from occams_forms.renderers import states

        entity = self._make_entity()
        entity['q1'] = u'Some value'

        formdata = {
            'ofmetadata_': {
                'not_done': True,
                'collect_date': date.today(),
                'version': entity.schema.publish_date
            },
            'ofworkflow_': {
                'state': states.PENDING_ENTRY
            }
        }

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertFalse(entity.not_done)
        self.assertIsNone(entity['q1'])

    def test_unknown_state_to_pending_entry(self):
        """
        It should clear data if transitioning to "Pending Entry"
        """
        from occams_forms import Session
        from occams_forms.renderers import states

        entity = self._make_entity()
        entity['q1'] = u'Some value'

        formdata = {
            'ofworkflow_': {
                'state': states.PENDING_ENTRY
            }
        }

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertEquals(entity.state.name, states.PENDING_ENTRY)
        self.assertIsNone(entity['q1'])

    def test_pending_entry_to_pending_correction(self):
        from occams_forms import Session
        from occams_forms.renderers import states

        entity = self._make_entity()
        entity['q1'] = u'Some value'

        formdata = {
            'ofworkflow_': {
                'state': states.PENDING_CORRECTION,
            },
            'q1': u'Some new value'
        }

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertEquals(entity.state.name, states.PENDING_CORRECTION)
        self.assertEquals(entity['q1'], formdata['q1'])

    def test_pending_entry_to_pending_review(self):
        from occams_forms import Session
        from occams_forms.renderers import states

        entity = self._make_entity()
        entity['q1'] = u'Some value'

        formdata = {
            'ofworkflow_': {
                'state': states.PENDING_REVIEW,
            },
            'q1': u'Some new value'
        }

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertEquals(entity.state.name, states.PENDING_REVIEW)
        self.assertEquals(entity['q1'], formdata['q1'])

    def test_pending_entry_to_complete(self):
        from occams_forms import Session
        from occams_forms.renderers import states

        entity = self._make_entity()
        entity['q1'] = u'Some value'

        formdata = {
            'ofworkflow_': {
                'state': states.COMPLETE,
            },
            'q1': u'Some new value'
        }

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertEquals(entity.state.name, states.COMPLETE)
        self.assertEquals(entity['q1'], formdata['q1'])

    def test_pending_review_to_complete(self):
        from occams_forms import Session, models
        from occams_forms.renderers import states

        entity = self._make_entity()
        entity.state = (
            Session.query(models.State)
            .filter_by(name=states.PENDING_REVIEW)
            .one())
        entity['q1'] = u'Some value'

        formdata = {
            'ofworkflow_': {
                'state': states.COMPLETE,
            },
            'q1': u'Last minute changes'
        }

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertEquals(entity.state.name, states.COMPLETE)
        self.assertEquals(entity['q1'], formdata['q1'])

    def test_auto_pending_entry_to_pending_review(self):

        from occams_forms import Session
        from occams_forms.renderers import states

        entity = self._make_entity()
        entity['q1'] = u'Some value'

        formdata = {'q1': 'Some new value'}

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertEquals(entity.state.name, states.PENDING_REVIEW)
        self.assertEqual(entity['q1'], formdata['q1'])

    def test_auto_pending_correction_to_pending_review(self):

        from occams_forms import Session, models
        from occams_forms.renderers import states

        entity = self._make_entity()
        entity.state = (
            Session.query(models.State)
            .filter_by(name=states.PENDING_CORRECTION)
            .one())
        entity['q1'] = u'Some value'

        formdata = {'q1': 'Some new value'}

        self._call(Session, entity, formdata, self.tmpdir)

        self.assertEquals(entity.state.name, states.PENDING_REVIEW)
        self.assertEqual(entity['q1'], formdata['q1'])

    def test_file_is_deleted(self):
        """
        Test file is deleted on the system after a non-FieldStorage
        object is passed to apply_data
        """

        import os
        from datetime import date

        from occams_forms import models
        from occams_forms import Session

        from mock import Mock

        schema = models.Schema(
            name=u'test', title=u'', publish_date=date.today(),
            attributes={
                'q1': models.Attribute(
                    name=u'q1',
                    title=u'',
                    type='blob',
                    order=0
                )
            })

        entity = models.Entity(schema=schema)

        formdata = {'q1': u''}

        with open(os.path.join(self.tmpdir, 'test.txt'), 'w'):
            fullpath = os.path.join(self.tmpdir, 'test.txt')

        entity['q1'] = Mock(path=fullpath)

        self._call(Session, entity, formdata, self.tmpdir)
        self.assertFalse(os.path.exists(fullpath))

    def test_previous_file_is_deleted(self):
        """
        Test if previous file is deleted from the
        system after a new non-FieldStoarage object
        is passed to apply_data
        """

        import os
        import cgi
        from datetime import date

        from occams_forms import models
        from occams_forms import Session

        from mock import Mock

        schema = models.Schema(
            name=u'test', title=u'', publish_date=date.today(),
            attributes={
                'q1': models.Attribute(
                    name=u'q1',
                    title=u'',
                    type='blob',
                    order=0
                )
            })

        entity = models.Entity(schema=schema)

        form = cgi.FieldStorage()
        form.filename = u'test.txt'
        form.file = form.make_file()
        form.file.write(u'test_content')
        form.file.seek(0)

        formdata = {'q1': form}

        with open(os.path.join(self.tmpdir, 'test.txt'), 'w'):
            fullpath = os.path.join(self.tmpdir, 'test.txt')

        entity['q1'] = Mock(path=fullpath)

        self._call(Session, entity, formdata, self.tmpdir)

        formdata = {'q1': u''}
        self._call(Session, entity, formdata, self.tmpdir)
        self.assertFalse(os.path.exists(fullpath))

    def test_old_file_is_deleted_after_update(self):
        """
        Test if previous file is deleted from the
        system after a new FieldStoarage object
        is passed to apply_data
        """
        import os
        import cgi
        from datetime import date

        from occams_forms import models
        from occams_forms import Session

        from mock import Mock

        schema = models.Schema(
            name=u'test', title=u'', publish_date=date.today(),
            attributes={
                'q1': models.Attribute(
                    name=u'q1',
                    title=u'',
                    type='blob',
                    order=0
                )
            })

        entity = models.Entity(schema=schema)

        form = cgi.FieldStorage()
        form.filename = u'test.txt'
        form.file = form.make_file()
        form.file.write(u'test_content')
        form.file.seek(0)

        formdata = {'q1': form}

        with open(os.path.join(self.tmpdir, 'test.txt'), 'w'):
            fullpath = os.path.join(self.tmpdir, 'test.txt')

        entity['q1'] = Mock(path=fullpath)

        self._call(Session, entity, formdata, self.tmpdir)

        form_update = cgi.FieldStorage()
        form_update.filename = u'test2.txt'
        form_update.file = form.make_file()
        form_update.file.write(u'test_content')
        form_update.file.seek(0)

        formdata2 = {'q1': form_update}
        self._call(Session, entity, formdata2, self.tmpdir)

        self.assertFalse(os.path.exists(fullpath))

    def test_file_is_inserted_to_db(self):
        """
        Test if a new record is inserted to value_blob
        table after a FieldStorage object is passed to apply_data
        """

        import os
        import cgi
        from datetime import date

        from occams_forms import models
        from occams_datastore import models as datastore
        from occams_forms import Session

        from mock import Mock

        schema = models.Schema(
            name=u'test', title=u'', publish_date=date.today(),
            attributes={
                'q1': models.Attribute(
                    name=u'q1',
                    title=u'',
                    type='blob',
                    order=0
                )
            })

        entity = models.Entity(schema=schema)

        form = cgi.FieldStorage()
        form.filename = u'test.txt'
        form.file = form.make_file()
        form.file.write(u'test_content')
        form.file.seek(0)

        formdata = {'q1': form}

        with open(os.path.join(self.tmpdir, 'test.txt'), 'w'):
            fullpath = os.path.join(self.tmpdir, 'test.txt')

        entity['q1'] = Mock(path=fullpath)

        self._call(Session, entity, formdata, self.tmpdir)

        blob = Session.query(datastore.ValueBlob).filter_by(
            file_name=u'test.txt').one()
        self.assertEquals(blob.file_name, u'test.txt')

    def test_old_file_is_deleted_db_after_empty_string_applied(self):
        """
        Test if previous file is deleted from db after
        a non-FieldStoarage is passed to apply_data
        """

        import os
        import cgi
        from datetime import date

        from occams_forms import models
        from occams_datastore import models as datastore
        from occams_forms import Session

        from mock import Mock

        schema = models.Schema(
            name=u'test', title=u'', publish_date=date.today(),
            attributes={
                'q1': models.Attribute(
                    name=u'q1',
                    title=u'',
                    type='blob',
                    order=0
                )
            })

        entity = models.Entity(schema=schema)

        form = cgi.FieldStorage()
        form.filename = u'test.txt'
        form.file = form.make_file()
        form.file.write(u'test_content')
        form.file.seek(0)

        formdata = {'q1': form}

        with open(os.path.join(self.tmpdir, 'test.txt'), 'w'):
            fullpath = os.path.join(self.tmpdir, 'test.txt')

        entity['q1'] = Mock(path=fullpath)

        self._call(Session, entity, formdata, self.tmpdir)

        formdata = {'q1': u''}
        self._call(Session, entity, formdata, self.tmpdir)

        blob = Session.query(datastore.ValueBlob).filter_by(
            file_name=u'test.txt').first()
        self.assertEquals(blob, None)

    def test_one_record_exists_db_after_update(self):
        """
        Test if one updated record exists in value_blob tbl
        after FieldStorage object passed to apply_data
        """

        import os
        import cgi
        from datetime import date

        from occams_forms import models
        from occams_datastore import models as datastore
        from occams_forms import Session

        from mock import Mock

        schema = models.Schema(
            name=u'test', title=u'', publish_date=date.today(),
            attributes={
                'q1': models.Attribute(
                    name=u'q1',
                    title=u'',
                    type='blob',
                    order=0
                )
            })

        entity = models.Entity(schema=schema)

        form = cgi.FieldStorage()
        form.filename = u'test.txt'
        form.file = form.make_file()
        form.file.write(u'test_content')
        form.file.seek(0)

        formdata = {'q1': form}

        with open(os.path.join(self.tmpdir, 'test.txt'), 'w'):
            fullpath = os.path.join(self.tmpdir, 'test.txt')

        entity['q1'] = Mock(path=fullpath)

        self._call(Session, entity, formdata, self.tmpdir)

        blob = Session.query(datastore.ValueBlob).one()
        entity_id = blob.entity.id

        form_update = cgi.FieldStorage()
        form_update.filename = u'test2.txt'
        form_update.file = form.make_file()
        form_update.file.write(u'test_content')
        form_update.file.seek(0)

        formdata2 = {'q1': form_update}
        self._call(Session, entity, formdata2, self.tmpdir)

        blob = Session.query(datastore.ValueBlob).filter_by(
            file_name=u'test2.txt').first()
        entity_id_after_update = blob.entity_id
        self.assertEquals(entity_id, entity_id_after_update)
