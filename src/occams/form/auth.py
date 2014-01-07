"""
Permission constants
All permissions are declared here for easier overview
"""


from repoze.who.interfaces import IChallengeDecider
from pyramid.events import subscriber, NewRequest
from pyramid.security import has_permission
from zope.interface import directlyProvides
import transaction

from occams.form import log, Session
from occams.datastore import model as datastore


def challenge_decider(environ, status, headers):
    """
    Backwards-compatibility fix to trigger challenge an authorized user.

    Repoze.who expects a status code of 401 to trigger the challenge UI,
    but pyramid will only raise 403 when the user has not authenticated.
    """
    return status.startswith('403') or status.startswith('401')


directlyProvides(challenge_decider, IChallengeDecider)


def groupfinder(identity, request):

    if 'groups' not in identity:
        log.warn('groups has not been set in the repoze identity!')

    # TODO: move to externa bitcore auth module
    mapping = {
        'aeh-admin': 'administrators',
        'aeh-nurses': 'nurses',
        'aeh-primary_investigators': 'primariy_investicagors'}

    groups = [mapping[g] for g in identity.get('groups', [])]
    return groups


@subscriber(NewRequest)
def track_user(event):
    """
    Annotates the database session with the current user.
    """
    identity = event.request.environ.get('repoze.who.identity')

    if not identity:
        return

    login = identity['login']

    if not Session.query(datastore.User).filter_by(key=login).count():
        with transaction.manager:
            Session.add(datastore.User(key=login))

    # update the current scoped session's infor attribute
    session = Session()
    session.info['user'] = login


def includeme(config):
    log.debug('Initializing auth helpers...')

    # Wrap has_permission to make it less cumbersome
    # TODO: This is built-in to pyramid 1.5, remove when we switch
    config.add_request_method(
        lambda r, n: has_permission(n, r.context, r),
        'has_permission')

    config.scan('occams.form.auth')
