from ddt import ddt, data

from tests import FunctionalFixture, USERID


@ddt
class TestPermissionsStudyList(FunctionalFixture):

    url = '/studies'

    def setUp(self):
        super(TestPermissionsStudyList, self).setUp()

        import transaction
        from occams import Session
        from occams_datastore import models as datastore

        # Any view-dependent data goes here
        # Webtests will use a different scope for its transaction
        with transaction.manager:
            Session.add(datastore.User(key=USERID))

    @data('administrator', 'manager', 'enterer', 'reviewer',
          'consumer', 'member', None)
    def test_allowed(self, group):
        environ = self.make_environ(userid=USERID, groups=[group])
        response = self.app.get(self.url, extra_environ=environ)
        from nose.tools import set_trace; set_trace()
        self.assertEquals(200, response.status_code)

    def test_not_authenticated(self):
        self.app.get(self.url, status=401)


# @ddt
# class TestPermissionsStudyView(FunctionalFixture):

#     study = 'test'
#     url = '/studies/{}'.format(study)

#     def setUp(self):
#         super(TestPermissionsStudyView, self).setUp()

#         import transaction
#         from occams import Session
#         from occams_studies import models as studies
#         from occams_datastore import models as datastore
#         from datetime import date

#         # Any view-dependent data goes here
#         # Webtests will use a different scope for its transaction
#         with transaction.manager:
#             user = datastore.User(key=USERID)
#             Session.info['blame'] = user
#             Session.add(user)
#             Session.flush()
#             Session.add(studies.Study(
#                         name=u'test',
#                         title=u'test',
#                         short_title=u'test',
#                         code=u'test',
#                         consent_date=date.today(),
#                         is_randomized=False))

#     @data('administrator', 'manager', 'enterer', 'reviewer',
#           'consumer', 'member', None)
#     def test_allowed(self, group):
#         environ = self.make_environ(userid=USERID, groups=[group])
#         response = self.app.get(self.url, extra_environ=environ)
#         from nose.tools import set_trace; set_trace()
#         self.assertEquals(200, response.status_code)

#     def test_not_authenticated(self):
#         self.app.get(self.url, status=401)


@ddt
class TestPermissionsStudyEdit(FunctionalFixture):

    study = 'test'
    url = '/studies/{}'.format(study)

    def setUp(self):
        super(TestPermissionsStudyEdit, self).setUp()

        import transaction
        from occams import Session
        from occams_studies import models as studies
        from occams_datastore import models as datastore
        from datetime import date

        # Any view-dependent data goes here
        # Webtests will use a different scope for its transaction
        with transaction.manager:
            user = datastore.User(key=USERID)
            Session.info['blame'] = user
            Session.add(user)
            Session.flush()
            Session.add(studies.Study(
                        name=u'test',
                        title=u'test',
                        short_title=u'test',
                        code=u'test',
                        consent_date=date.today(),
                        is_randomized=False))

    @data('administrator', 'manager')
    def test_allowed(self, group):
        environ = self.make_environ(userid=USERID, groups=[group])
        response = self.app.put(self.url, extra_environ=environ, xhr=True, status='*')
        # from nose.tools import set_trace; set_trace()
        self.assertEquals(200, response.status_code)

    @data('enterer', 'reviewer', 'consumer', 'member', None)
    def test_not_allowed(self, group):
        environ = self.make_environ(userid=USERID, groups=[group])
        response = self.app.put(self.url, extra_environ=environ, xhr=True, status='*')
        self.assertEquals(403, response.status_code)

    def test_not_authenticated(self):
        self.app.get(self.url, status=401)


# @ddt
# class TestPermissionsStudyDelete(FunctionalFixture):

#     study = 'test'
#     url = '/studies/{}'.format(study)

#     def setUp(self):
#         super(TestPermissionsStudyDelete, self).setUp()

#         import transaction
#         from occams import Session
#         from occams_studies import models as studies
#         from occams_datastore import models as datastore
#         from datetime import date

#         # Any view-dependent data goes here
#         # Webtests will use a different scope for its transaction
#         with transaction.manager:
#             user = datastore.User(key=USERID)
#             Session.info['blame'] = user
#             Session.add(user)
#             Session.flush()
#             Session.add(studies.Study(
#                         name=u'test',
#                         title=u'test',
#                         short_title=u'test',
#                         code=u'test',
#                         consent_date=date.today(),
#                         is_randomized=False))

#     @data('administrator', 'manager', 'whatever')
#     def test_allowed(self, group):
#         environ = self.make_environ(userid=USERID, groups=[group])
#         response = self.app.delete(self.url, extra_environ=environ, xhr=True)
#         self.assertEquals(200, response.status_code)

#     # @data('enterer', 'reviewer', 'consumer', 'member', None)
#     # def test_not_allowed(self, group):
#     #     environ = self.make_environ(userid=USERID, groups=[group])
#     #     response = self.app.delete(self.url, extra_environ=environ, xhr=True)
#     #     self.assertEquals(403, response.status_code)

#     def test_not_authenticated(self):
#         self.app.get(self.url, status=403)