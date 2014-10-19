from good import *  # NOQA
from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPOk
from pyramid.session import check_csrf_token
from pyramid.view import view_config
import sqlalchemy as sa
from sqlalchemy import orm
import six
from zope.sqlalchemy import mark_changed

from .. import _, models, Session
from . import cycle as cycle_views, form as form_views
from ..validators import invalid2dict, Model


@view_config(
    route_name='home',
    permission='view',
    renderer='../templates/study/list.pt')
def home(request):
    studies_query = (
        Session.query(models.Study)
        .order_by(models.Study.title.asc()))

    modified_query = (
        Session.query(models.Patient)
        .order_by(models.Patient.modify_date.desc())
        .limit(10))

    viewed = sorted((request.session.get('viewed') or {}).values(),
                    key=lambda v: v['view_date'],
                    reverse=True)

    return {
        'studies': studies_query,
        'studies_count': studies_query.count(),

        'modified': modified_query,
        'modified_count': modified_query.count(),

        'viewed': viewed,
        'viewed_count': len(viewed),
    }


@view_config(
    route_name='study',
    permission='view',
    renderer='../templates/study/view.pt')
def view(context, request):
    return {
        'study': view_json(context, request)
        }


@view_config(
    route_name='study',
    permission='view',
    xhr=True,
    renderer='json')
def view_json(context, request):
    study = context
    return {
        '__url__': request.route_path('study', study=study.name),
        'id': study.id,
        'name': study.name,
        'title': study.title,
        'code': study.code,
        'short_title': study.short_title,
        'consent_date': study.consent_date.isoformat(),
        'start_date': study.start_date and study.start_date.isoformat(),
        'end_date': study.end_date and study.end_date.isoformat(),
        'is_randomized': study.is_randomized,
        'is_blinded': study.is_blinded,
        'is_locked': study.is_locked,
        'cycles': [
            cycle_views.view_json(cycle, request) for cycle in study.cycles],
        'termination_form':
            study.termination_schema
            and form_views.form2json(study.termination_schema),
        'randomization_form':
            study.randomization_schema
            and form_views.form2json(study.randomization_schema),
        'forms': form_views.form2json(study.schemata)
        }


@view_config(
    route_name='study_progress',
    permission='view',
    renderer='../templates/study/progress.pt')
def progress(context, request):

    states_query = Session.query(models.State)

    VisitCycle = orm.aliased(models.Cycle)

    cycles_query = (
        Session.query(models.Cycle)
        .filter_by(study=context)
        .add_column(
            Session.query(sa.func.count(models.Visit.id))
            .join(VisitCycle, models.Visit.cycles)
            .filter(VisitCycle.id == models.Cycle.id)
            .correlate(models.Cycle)
            .label('visits_count')))

    for state in states_query:
        cycles_query = cycles_query.add_column(
            Session.query(sa.func.count(models.Visit.id))
            .join(VisitCycle, models.Visit.cycles)
            .filter(models.Visit.entities.any(state=state))
            .filter(VisitCycle.id == models.Cycle.id)
            .correlate(models.Cycle)
            .label(state.name))

    cycles_query = cycles_query.order_by(models.Cycle.week.asc())
    cycles_count = context.cycles.count()

    return {
        'states': states_query,
        'cycles': cycles_query,
        'cycles_count': cycles_count,
        'has_cycles': cycles_count > 0}


@view_config(
    route_name='studies',
    permission='add',
    request_method='POST',
    xhr=True,
    renderer='json')
@view_config(
    route_name='study',
    permission='edit',
    request_method='PUT',
    xhr=True,
    renderer='json')
def edit_json(context, request):
    check_csrf_token(request)

    schema = StudySchema(context, request)

    try:
        data = schema(request.json_body)
    except Invalid as e:
        raise HTTPBadRequest(json={'errors': invalid2dict(e)})

    if isinstance(context, models.StudyFactory):
        study = models.Study()
        Session.add(study)
    else:
        study = context

    study.name = data['name']
    study.title = data['title']
    study.code = data['code']
    study.short_title = data['short_title']
    study.consent_date = data['consent_date']
    study.start_date = data['start_date']
    study.end_date = data['end_date']
    study.termination_schema = data['termination_form']
    study.is_locked = data['is_locked']
    study.is_randomized = data['is_randomized']

    if study.is_randomized:
        study.is_blinded = data['is_blinded']
        study.randomization_schema = data['randomization_form']
    else:
        study.is_blinded = None
        study.randomization_schema = None

    Session.flush()

    if isinstance(context, models.StudyFactory):
        request.session.flash(_(u'New study added!', 'success'))

    return view_json(study, request)


@view_config(
    route_name='studies',
    permission='add',
    xhr=True,
    request_param='vocabulary=available_termination',
    renderer='json')
@view_config(
    route_name='study',
    permission='edit',
    xhr=True,
    request_param='vocabulary=available_termination',
    renderer='json')
def available_termination(context, request):
    """
    Returns a JSON listing of avavilable schemata for terminiation
    """
    term = (request.GET.get('term') or u'').strip()

    query = (
        Session.query(models.Schema)
        .filter(models.Schema.publish_date != sa.null())
        .filter(models.Schema.retract_date == sa.null()))

    if isinstance(context, models.Study):
        query = (
            query
            .filter(~models.Schema.name.in_(
                # Filter out schemata that is already in use by the study
                Session.query(models.Schema.name)
                .select_from(models.Study)
                .filter(models.Study.id == context.id)
                .join(models.Study.schemata)
                .union(
                    # Filter out randomization schemata
                    Session.query(models.Schema.name)
                    .select_from(models.Study)
                    .join(models.Study.randomization_schema)
                    .filter(models.Study.id == context.id))
                .subquery())))

    if term:
        query = query.filter(models.Schema.title.ilike(u'%' + term + u'%'))

    query = (
        query
        .order_by(
            models.Schema.title,
            models.Schema.publish_date)
        .limit(100))

    return {'schemata': [form_views.version2json(i) for i in query]}


@view_config(
    route_name='studies',
    permission='add',
    xhr=True,
    request_param='vocabulary=available_randomization',
    renderer='json')
@view_config(
    route_name='study',
    permission='edit',
    xhr=True,
    request_param='vocabulary=available_randomization',
    renderer='json')
def available_randomiation(context, request):
    """
    Returns a JSON listing of avavilable schemata for randomization
    """
    term = (request.GET.get('term') or u'').strip()

    query = (
        Session.query(models.Schema)
        .filter(models.Schema.publish_date != sa.null())
        .filter(models.Schema.retract_date == sa.null()))

    if isinstance(context, models.Study):
        query = (
            query
            .filter(~models.Schema.name.in_(
                # Filter out schemata that is already in use by the study
                Session.query(models.Schema.name)
                .select_from(models.Study)
                .filter(models.Study.id == context.id)
                .join(models.Study.schemata)
                .union(
                    # Filter out terminiation schemata
                    Session.query(models.Schema.name)
                    .select_from(models.Study)
                    .join(models.Study.termination_schema)
                    .filter(models.Study.id == context.id))
                .subquery())))

    if term:
        query = query.filter(models.Schema.title.ilike(u'%' + term + u'%'))

    query = (
        query
        .order_by(
            models.Schema.title,
            models.Schema.publish_date)
        .limit(100))

    return {'schemata': [form_views.version2json(i) for i in query]}


@view_config(
    route_name='study',
    permission='edit',
    xhr=True,
    request_param='vocabulary=available_schemata',
    renderer='json')
def available_schemata(context, request):
    """
    Returns a JSON listing of avavilable schemata for studies to use.
    """
    term = (request.GET.get('term') or u'').strip()

    InnerSchema = orm.aliased(models.Schema)
    titles_query = (
        Session.query(models.Schema.name)
        .add_column(
            Session.query(InnerSchema.title)
            .filter(InnerSchema.name == models.Schema.name)
            .filter(InnerSchema.publish_date != sa.null())
            .filter(InnerSchema.retract_date == sa.null())
            .order_by(InnerSchema.publish_date.desc())
            .limit(1)
            .correlate(models.Schema)
            .as_scalar()
            .label('title'))
        .filter(models.Schema.publish_date != sa.null())
        .filter(models.Schema.retract_date == sa.null())
        .filter(~models.Schema.name.in_(
            # Filter out schemata that is already in use by the study
            Session.query(models.Schema.name)
            .select_from(models.Study)
            .filter(models.Study.id == context.id)
            .join(models.Study.schemata)
            .union(
                # Filter out termination schemata
                Session.query(models.Schema.name)
                .select_from(models.Study)
                .join(models.Study.termination_schema)
                .filter(models.Study.id == context.id),

                # Filter out randomization schemata
                Session.query(models.Schema.name)
                .select_from(models.Study)
                .join(models.Study.randomization_schema)
                .filter(models.Study.id == context.id))
            .subquery()))
        .group_by(models.Schema.name)
        .subquery())

    query = Session.query(titles_query)

    if term:
        query = query.filter(titles_query.c.title.ilike(u'%' + term + u'%'))

    query = query.order_by(titles_query.c.title).limit(100)

    return {'schemata': [{'name': r.name, 'title': r.title} for r in query]}


@view_config(
    route_name='study',
    permission='edit',
    xhr=True,
    request_param='vocabulary=available_versions',
    renderer='json')
def available_version(context, request):
    """
    Returns a JSON listing of schemata versions for studies to use.
    """
    term = (request.GET.get('term') or u'').strip()
    schema = (request.GET.get('schema') or u'').strip()

    if not schema:
        return []

    query = (
        Session.query(models.Schema)
        .filter(models.Schema.name == schema)
        .filter(models.Schema.publish_date != sa.null())
        .filter(models.Schema.retract_date == sa.null()))

    if term:
        publish_string = sa.cast(models.Schema.publish_date, sa.String)
        query = query.filter(publish_string.ilike(u'%' + term + u'%'))

    query = query.order_by(models.Schema.publish_date.desc()).limit(100)

    return {'versions': [form_views.version2json(s) for s in query]}


@view_config(
    route_name='study',
    permission='delete',
    request_method='DELETE',
    xhr=True,
    renderer='json')
def delete_json(context, request):
    check_csrf_token(request)

    (has_enrollments,) = (
        Session.query(
            Session.query(models.Enrollment)
            .filter_by(study=context)
            .exists())
        .one())

    if has_enrollments and not request.has_permission('admin', context):
        raise HTTPForbidden(_(u'Cannot delete a study with enrollments'))

    Session.delete(context)
    Session.flush()

    request.session.flash(
        _(u'Successfully removed "${study}"', mapping={
            'study': context.title}))

    return {'__next__': request.route_path('studies')}


@view_config(
    route_name='study_schemata',
    permission='edit',
    request_method='POST',
    xhr=True,
    renderer='json')
def add_schema_json(context, request):
    check_csrf_token(request)

    def check_published(value):
        if value.publish_date is None:
            raise Invalid(request.localizer.translate(
                _(u'${schema} is not published'),
                mapping={'schema': value.title}))
        return value

    def check_not_patient_schema(value):
        (exists,) = (
            Session.query(
                Session.query(models.Schema)
                .join(models.patient_schema_table)
                .filter(models.Schema.name == value.name)
                .exists())
            .one())
        if exists:
            raise Invalid(request.localizer.translate(
                _(u'${schema} is already used as a patient form'),
                mapping={'schema': value.title}))
        return value

    def check_not_randomization_schema(value):
        if (context.randomization_schema is not None
                and context.randomization_schema.name == value.name):
            raise Invalid(request.localizer.translate(
                _(u'${schema} is already used as a randomization form'),
                mapping={'schema': value.title}))
        return value

    def check_not_termination_schema(value):
        if (context.termination_schema is not None
                and context.termination_schema.name == value.name):
            raise Invalid(request.localizer.translate(
                _(u'${schema} is already used as a termination form'),
                mapping={'schema': value.title}))
        return value

    def check_same_schema(value):
        versions = value['versions']
        schema = value['schema']
        invalid = [i.publish_date for i in versions if i.name != schema]
        if invalid:
            raise Invalid(
                request.localizer(
                    _(u'Incorrect version: ${versions}'),
                    mapping={'versions': ', '.join(map(str, invalid))}
                ),
                path='versions')
        return value

    schema = Schema(All({
        'schema': Coerce(six.binary_type),
        'versions': [All(
            Model(models.Schema, localizer=request.localizer),
            check_published,
            check_not_patient_schema,
            check_not_randomization_schema,
            check_not_termination_schema,
            )],
        Extra: Remove},
        check_same_schema,
        ))

    try:
        data = schema(request.json_body)
    except Invalid as e:
        raise HTTPBadRequest(json={'errors': invalid2dict(e)})

    old_items = set(i for i in context.schemata if i.name == data['schema'])
    new_items = set(data['versions'])

    # Remove unselected
    context.schemata.difference_update(old_items - new_items)

    # Add newly selected
    context.schemata.update(new_items)

    # Get a list of cycles to update
    cycles = (
        Session.query(models.Cycle)
        .options(orm.joinedload(models.Cycle.schemata))
        .filter(models.Cycle.study == context)
        .filter(models.Cycle.schemata.any(name=data['schema'])))

    # Also update available cycle schemata versions
    for cycle in cycles:
        cycle.schemata.difference_update(old_item - new_items)
        cycle.schemata.update(new_items)

    return form_views.form2json(new_items)[0]


@view_config(
    route_name='study_schema',
    permission='edit',
    request_method='DELETE',
    xhr=True,
    renderer='json')
def delete_schema_json(context, request):
    check_csrf_token(request)
    schema_name = request.matchdict.get('schema')

    if not schema_name:
        return HTTPBadRequest()

    # Remove from cycles
    Session.execute(
        models.cycle_schema_table.delete()
        .where(
            models.cycle_schema_table.c.cycle_id.in_(
                Session.query(models.Cycle.id)
                .filter_by(study=context)
                .subquery())
            & models.cycle_schema_table.c.schema_id.in_(
                Session.query(models.Schema.id)
                .filter_by(name=schema_name)
                .subquery())))

    # Remove from study
    Session.execute(
        models.study_schema_table.delete()
        .where(
            (models.study_schema_table.c.study_id == context.id)
            & (models.study_schema_table.c.schema_id.in_(
                Session.query(models.Schema.id)
                .filter_by(name=schema_name)
                .subquery()))))

    mark_changed(Session())

    # Expire relations so they load their updated values
    Session.expire_all()

    return HTTPOk()


@view_config(
    route_name='study_schedule',
    permission='edit',
    request_method='PUT',
    xhr=True,
    renderer='json')
def edit_schedule_json(context, request):
    check_csrf_token(request)

    def check_schema_in_study(value):
        (exists,) = (
            Session.query(
                Session.query(models.Study)
                .filter(models.Study.cycles.any(study_id=context.id))
                .filter(models.Study.schemata.any(name=value))
                .exists())
            .one())
        if not exists:
            msg = _('${study} does not have form "${schema}"')
            mapping = {'schema': value, 'study': context.title}
            raise Invalid(request.localizer.translate(msg, mapping=mapping))
        return value

    def check_cycle_in_study(value):
        if value.study != context:
            msg = _('${study} does not have cycle "${cycle}"')
            mapping = {'cycle': value.title, 'study': context.title}
            raise Invalid(request.localizer.translate(msg, mapping=mapping))
        return value

    schema = Schema({
        'schema': All(
            Coerce(six.binary_type),
            check_schema_in_study),
        'cycle': All(
            Model(models.Cycle, localizer=request.localizer),
            check_cycle_in_study),
        'enabled': Boolean(),
        Extra: Remove
        })

    try:
        data = schema(request.json_body)
    except Invalid as e:
        raise HTTPBadRequest(json={'errors': invalid2dict(e)})

    schema_name = data['schema']
    cycle = data['cycle']
    enabled = data['enabled']

    study_items = set(i for i in context.schemata if i.name == schema_name)
    cycle_items = set(i for i in cycle.schemata if i.name == schema_name)

    if enabled:
        # Match cycle schemata to the study's schemata for the given name
        cycle.schemata.difference_update(cycle_items - study_items)
        cycle.schemata.update(study_items)
    else:
        cycle.schemata.difference_update(study_items | cycle_items)

    return HTTPOk()


def StudySchema(context, request):
    """
    Returns a validator for incoming study modification data
    """

    def check_unique_name(value):
        query = Session.query(models.Study).filter_by(name=value)
        if isinstance(context, models.Study):
            query = query.filter(models.Study.id != context.id)
        (exists,) = Session.query(query.exists()).one()
        if exists:
            msg = _('"${name}" already exists')
            mapping = {'name': value}
            raise Invalid(request.localizer.translate(msg, mapping=mapping))
        return value

    return Schema({
        'name': All(
            Coerce(six.binary_type),
            Length(min=3, max=32),
            Match(r'^[a-z0-9_\-]+$'),
            check_unique_name),
        'title': All(Coerce(six.text_type), Length(min=3, max=32)),
        'code': All(Coerce(six.binary_type), Length(min=3, max=8)),
        'short_title': All(Coerce(six.text_type), Length(min=3, max=8)),
        'consent_date': Date('%Y-%m-%d'),
        'start_date': Maybe(Date('%Y-%m-%d')),
        'end_date': Maybe(Date('%Y-%m-%d')),
        'is_locked': Boolean(),
        'termination_form': All(
            Model(models.Schema, localizer=request.localizer)),
        'is_randomized': Maybe(Boolean()),
        'is_blinded': Maybe(Boolean()),
        'randomization_form': Maybe(
            Model(models.Schema, localizer=request.localizer)),
        Extra: Remove})
