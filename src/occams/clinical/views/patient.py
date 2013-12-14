import colander
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from sqlalchemy import bindparam, or_, func, orm, sql
import transaction
from webhelpers import paginate

from occams.datastore import model as datastore

from occams.clinical import _, log, models, Session


@view_config(
    route_name='patient_search',
    permission='patient_view',
    renderer='occams.clinical:templates/patient/search.pt')
def search(request):
    request.layout_manager.layout.content_title = _(u'Patients')
    search_term = request.GET.get('search')

    if not search_term:
        return {}

    current_page = int(request.GET.get('page', 0))
    search_query = query_by_ids(search_term)
    search_count = search_query.count()
    page_url = paginate.PageURL_WebOb(request)
    page = paginate.Page(
        search_query, current_page, item_count=search_count, url=page_url)

    return {
        'page': page}


def query_by_ids(term):
    """
    Search utility that returns a patient entry query based on reference numbers
    """
    wildcard = '%{0}%'.format(term)
    return (
        Session.query(models.Patient)
        .outerjoin(models.Patient.enrollments)
        .outerjoin(models.Patient.strata)
        .outerjoin(models.Patient.reference_numbers)
        .filter(or_(
            models.Patient.pid.ilike(wildcard),
            models.Enrollment.reference_number.ilike(wildcard),
            models.Stratum.reference_number.ilike(wildcard),
            models.PatientReference.reference_number.ilike(wildcard),
            models.Patient.initials.ilike(wildcard)))
        .order_by(models.Patient.pid.asc()))
