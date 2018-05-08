"""
Override package_search to utilise solr highlighting.

Overridden code copied from CKAN 2.7.2

The strategy is to keep the overridden code as close to upstream as possible
and do the rest of the work in the IPackageController plugin.
"""

from ckan.common import _
from ckan.common import config
from ckan.lib import search
from ckan.lib.search.common import make_connection, SearchError, SearchQueryError
from ckan.lib.search.query import QUERY_FIELDS, solr_literal
from paste.deploy.converters import asbool
from paste.util.multidict import MultiDict
import ckan.authz as authz
import ckan.lib.activity_streams as activity_streams
import ckan.lib.datapreview as datapreview
import ckan.lib.dictization
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.jobs as jobs
import ckan.lib.navl.dictization_functions
import ckan.lib.plugins as lib_plugins
import ckan.lib.search as search
import ckan.logic as logic
import ckan.logic.action
import ckan.logic.schema
import ckan.model as model
import ckan.model.misc as misc
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import datetime
import json
import logging
import pysolr
import six
import socket
import sqlalchemy
import uuid

import re

VALID_SOLR_PARAMETERS = search.query.VALID_SOLR_PARAMETERS.copy()

_validate = ckan.lib.navl.dictization_functions.validate
_table_dictize = ckan.lib.dictization.table_dictize
_check_access = logic.check_access
NotFound = logic.NotFound
ValidationError = logic.ValidationError
_get_or_bust = logic.get_or_bust

_select = sqlalchemy.sql.select
_aliased = sqlalchemy.orm.aliased
_or_ = sqlalchemy.or_
_and_ = sqlalchemy.and_
_func = sqlalchemy.func
_desc = sqlalchemy.desc
_case = sqlalchemy.case
_text = sqlalchemy.text


log = logging.getLogger(__name__)


class PackageSearchQuery(search.PackageSearchQuery):
    def __init__(self, **kwargs):
        super(PackageSearchQuery, self).__init__(**kwargs)
        self.highlighting = {}

    def run(self, query, permission_labels=None, **kwargs):
        '''
        Performs a dataset search using the given query.

        :param query: dictionary with keys like: q, fq, sort, rows, facet
        :type query: dict
        :param permission_labels: filter results to those that include at
            least one of these labels. None to not filter (return everything)
        :type permission_labels: list of unicode strings; or None

        :returns: dictionary with keys results and count

        May raise SearchQueryError or SearchError.
        '''
        assert isinstance(query, (dict, MultiDict))
        # check that query keys are valid
        valid_solr_parameters = VALID_SOLR_PARAMETERS
        for item in plugins.PluginImplementations(plugins.IPackageController):
            if 'update_valid_solr_parameters' in dir(item):
                valid_solr_parameters = item.update_valid_solr_parameters(valid_solr_parameters)

        if not set(query.keys()) <= valid_solr_parameters:
            invalid_params = [s for s in set(query.keys()) - valid_solr_parameters]
            raise SearchQueryError("Invalid search parameters: %s" % invalid_params)

        # default query is to return all documents
        q = query.get('q')
        if not q or q == '""' or q == "''":
            query['q'] = "*:*"

        # number of results
        rows_to_return = min(1000, int(query.get('rows', 10)))
        if rows_to_return > 0:
            # #1683 Work around problem of last result being out of order
            #       in SOLR 1.4
            rows_to_query = rows_to_return + 1
        else:
            rows_to_query = rows_to_return
        query['rows'] = rows_to_query

        fq = []
        if 'fq' in query:
            fq.append(query['fq'])
        fq.extend(query.get('fq_list', []))

        # show only results from this CKAN instance
        fq.append('+site_id:%s' % solr_literal(config.get('ckan.site_id')))

        # filter for package status
        if not '+state:' in query.get('fq', ''):
            fq.append('+state:active')

        # only return things we should be able to see
        if permission_labels is not None:
            fq.append('+permission_labels:(%s)' % ' OR '.join(
                solr_literal(p) for p in permission_labels))
        query['fq'] = fq

        # faceting
        query['facet'] = query.get('facet', 'true')
        query['facet.limit'] = query.get('facet.limit', config.get('search.facets.limit', '50'))
        query['facet.mincount'] = query.get('facet.mincount', 1)

        # return the package ID and search scores
        query['fl'] = query.get('fl', 'name')

        # return results as json encoded string
        query['wt'] = query.get('wt', 'json')

        # If the query has a colon in it then consider it a fielded search and do use dismax.
        defType = query.get('defType', 'dismax')
        if ':' not in query['q'] or defType == 'edismax':
            query['defType'] = defType
            query['tie'] = query.get('tie', '0.1')
            # this minimum match is explained
            # http://wiki.apache.org/solr/DisMaxQParserPlugin#mm_.28Minimum_.27Should.27_Match.29
            query['mm'] = query.get('mm', '2<-1 5<80%')
            query['qf'] = query.get('qf', QUERY_FIELDS)

        conn = make_connection(decode_dates=False)
        log.debug('Package query: %r' % query)
        try:
            solr_response = conn.search(**query)
        except pysolr.SolrError, e:
            # Error with the sort parameter.  You see slightly different
            # error messages depending on whether the SOLR JSON comes back
            # or Jetty gets in the way converting it to HTML - not sure why
            #
            if e.args and isinstance(e.args[0], str):
                if "Can't determine a Sort Order" in e.args[0] or \
                        "Can't determine Sort Order" in e.args[0] or \
                        'Unknown sort order' in e.args[0]:
                    raise SearchQueryError('Invalid "sort" parameter')
            raise SearchError('SOLR returned an error running query: %r Error: %r' %
                              (query, e))
        self.count = solr_response.hits
        self.results = solr_response.docs
        self.highlighting = solr_response.highlighting

        # #1683 Filter out the last row that is sometimes out of order
        self.results = self.results[:rows_to_return]

        # get any extras and add to 'extras' dict
        for result in self.results:
            extra_keys = filter(lambda x: x.startswith('extras_'), result.keys())
            extras = {}
            for extra_key in extra_keys:
                value = result.pop(extra_key)
                extras[extra_key[len('extras_'):]] = value
            if extra_keys:
                result['extras'] = extras

        # if just fetching the id or name, return a list instead of a dict
        if query.get('fl') in ['id', 'name']:
            self.results = [r.get(query.get('fl')) for r in self.results]

        # get facets and convert facets list to a dict
        self.facets = solr_response.facets.get('facet_fields', {})
        for field, values in six.iteritems(self.facets):
            self.facets[field] = dict(zip(values[0::2], values[1::2]))

        query_response = {
            'results': self.results,
            'count': self.count,
        }

        return query_response


# It's probably best to keep this as close to CKAN's version as possible
# and use IPackageController to modify whatever it can to make merging CKAN
# updates as easy as possible.
def package_search(context, data_dict):
    # sometimes context['schema'] is None
    schema = (context.get('schema') or
              logic.schema.default_package_search_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    # put the extras back into the data_dict so that the search can
    # report needless parameters
    data_dict.update(data_dict.get('__extras', {}))
    data_dict.pop('__extras', None)
    if errors:
        raise ValidationError(errors)

    model = context['model']
    session = context['session']
    user = context.get('user')

    _check_access('package_search', context, data_dict)

    # Move ext_ params to extras and remove them from the root of the search
    # params, so they don't cause and error
    data_dict['extras'] = data_dict.get('extras', {})
    for key in [key for key in data_dict.keys() if key.startswith('ext_')]:
        data_dict['extras'][key] = data_dict.pop(key)

    # check if some extension needs to modify the search params
    for item in plugins.PluginImplementations(plugins.IPackageController):
        data_dict = item.before_search(data_dict)

    # the extension may have decided that it is not necessary to perform
    # the query
    abort = data_dict.get('abort_search', False)

    if data_dict.get('sort') in (None, 'rank'):
        data_dict['sort'] = 'score desc, metadata_modified desc'

    results = []
    if not abort:
        if asbool(data_dict.get('use_default_schema')):
            data_source = 'data_dict'
        else:
            data_source = 'validated_data_dict'
        data_dict.pop('use_default_schema', None)

        result_fl = data_dict.get('fl')
        if not result_fl:
            data_dict['fl'] = 'id {0}'.format(data_source)
        else:
            data_dict['fl'] = ' '.join(result_fl)

        # Remove before these hit solr FIXME: whitelist instead
        include_private = asbool(data_dict.pop('include_private', False))
        include_drafts = asbool(data_dict.pop('include_drafts', False))
        data_dict.setdefault('fq', '')
        if not include_private:
            data_dict['fq'] = '+capacity:public ' + data_dict['fq']
        if include_drafts:
            data_dict['fq'] += ' +state:(active OR draft)'

        # Pop these ones as Solr does not need them
        extras = data_dict.pop('extras', None)

        # enforce permission filter based on user
        if context.get('ignore_auth') or (user and authz.is_sysadmin(user)):
            labels = None
        else:
            labels = lib_plugins.get_permission_labels(
                ).get_user_dataset_labels(context['auth_user_obj'])

        query = PackageSearchQuery()
        query.run(data_dict, permission_labels=labels)

        # Add them back so extensions can use them on after_search
        data_dict['extras'] = extras

        if result_fl and not extras['fl_compatible']:
            for package in query.results:
                if package.get('extras'):
                    package.update(package['extras'] )
                    package.pop('extras')
                results.append(package)
        else:
            for package in query.results:
                # get the package object
                package_dict = package.get(data_source)
                ## use data in search index if there
                if package_dict:
                    # the package_dict still needs translating when being viewed
                    package_dict = json.loads(package_dict)
                    if context.get('for_view'):
                        for item in plugins.PluginImplementations(
                                plugins.IPackageController):
                            package_dict = item.before_view(package_dict)
                    results.append(package_dict)
                else:
                    log.error('No package_dict is coming from solr for package '
                              'id %s', package['id'])

        count = query.count
        facets = query.facets
        raw_solr_results = {
            'results': query.results,
            'highlighting': query.highlighting,
            'count': query.count,
            'facets': query.facets,
        }
    else:
        count = 0
        facets = {}
        results = []
        raw_solr_results = {}

    search_results = {
        'count': count,
        'facets': facets,
        'results': results,
        'sort': data_dict['sort'],
    }

    include_raw_solr_results = False
    for item in plugins.PluginImplementations(plugins.IPackageController):
        if 'include_raw_solr_results' in dir(item):
            include_raw_solr_results = include_raw_solr_results \
                                       or item.include_raw_solr_results(data_dict)

    if include_raw_solr_results:
        search_results['raw_solr_results'] = raw_solr_results

    # create a lookup table of group name to title for all the groups and
    # organizations in the current search's facets.
    group_names = []
    for field_name in ('groups', 'organization'):
        group_names.extend(facets.get(field_name, {}).keys())

    groups = (session.query(model.Group.name, model.Group.title)
                    .filter(model.Group.name.in_(group_names))
                    .all()
              if group_names else [])
    group_titles_by_name = dict(groups)

    # Transform facets into a more useful data structure.
    restructured_facets = {}
    for key, value in facets.items():
        restructured_facets[key] = {
            'title': key,
            'items': []
        }
        for key_, value_ in value.items():
            new_facet_dict = {}
            new_facet_dict['name'] = key_
            if key in ('groups', 'organization'):
                display_name = group_titles_by_name.get(key_, key_)
                display_name = display_name if display_name and display_name.strip() else key_
                new_facet_dict['display_name'] = display_name
            elif key == 'license_id':
                license = model.Package.get_license_register().get(key_)
                if license:
                    new_facet_dict['display_name'] = license.title
                else:
                    new_facet_dict['display_name'] = key_
            else:
                new_facet_dict['display_name'] = key_
            new_facet_dict['count'] = value_
            restructured_facets[key]['items'].append(new_facet_dict)
    search_results['search_facets'] = restructured_facets

    # check if some extension needs to modify the search results
    for item in plugins.PluginImplementations(plugins.IPackageController):
        search_results = item.after_search(search_results, data_dict)

    # After extensions have had a chance to modify the facets, sort them by
    # display name.
    for facet in search_results['search_facets']:
        search_results['search_facets'][facet]['items'] = sorted(
            search_results['search_facets'][facet]['items'],
            key=lambda facet: facet['display_name'], reverse=True)

    return search_results


HIGHLIGHTING_PARAMETERS = ['hl', 'hl.fl', 'hl.snippets', 'hl.fragsize', 'pf']


class SATreasurySearchPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IActions)

    def get_actions(self):
        package_search.side_effect_free = True
        return {
            'package_search': package_search,
        }

    def before_search(self, search_params):
        # log.info("before_search %r", search_params)
        extras = search_params.get('extras')
        if extras and 'ext_highlight' in extras:
            search_params['hl'] = 'on'
            search_params['hl.fl'] = '*'
            search_params['hl.snippets'] = 5
            search_params['hl.fragsize'] = 200
            # Make sure that matches where the query words are in close
            # proximity get higher ranking
            search_params['pf'] = ['name^4 title^4 tags^2 groups^2 text']
            # Request what package_search requests by default + index_id
            field_list = ['id', 'validated_data_dict', 'index_id']
            search_params['fl'] = search_params.get('fl', field_list)
            # Tell CKAN that the custom fl is compatible with its original
            # and it should behave like it's not modified
            search_params['extras']['fl_compatible'] = True

        return search_params

    def update_valid_solr_parameters(self, valid_solr_parameters):
        """
        Takes a set and returns a set
        """
        for param in HIGHLIGHTING_PARAMETERS:
            valid_solr_parameters.add(param)
        return valid_solr_parameters

    def include_raw_solr_results(self, search_params):
        extras = search_params.get('extras')
        if extras and 'ext_highlight' in extras:
            return True
        else:
            return False

    def after_search(self, search_results, search_params):
        # log.info("after_search %r %r", search_results, search_params)
        extras = search_params.get('extras')
        if extras and 'ext_highlight' in extras:
            ckan_results = search_results['results']
            solr_results = search_results['raw_solr_results']['results']
            highlighting = search_results['raw_solr_results']['highlighting']
            assign_highlighting(ckan_results, solr_results, highlighting)

            # Clean up the stuff we needed for assigning highlighting
            del search_results['raw_solr_results']

        return search_results


RESOURCE_RE = re.compile('^ckanext-extractor_([a-z0-9_-]+)_fulltext$')


def assign_highlighting(result_packages, solr_results, highlighting):
    for idx, solr_result in enumerate(solr_results):

        index_id = solr_result['index_id']
        package_highlighting = highlighting[index_id]
        package_result = result_packages[idx]
        package_result['highlighting'] = package_highlighting

        # Initialise resource highlighting key
        for resource in package_result['resources']:
            resource['highlighting'] = {}

        # Move resource highlighting to the resource
        for key in package_highlighting.keys():
            match = RESOURCE_RE.match(key)
            if match:
                resource_id = match.group(1)
                highlights = package_highlighting.pop(key)
                for resource in package_result['resources']:
                    if resource['id'] == resource_id:
                        resource['highlighting']['fulltext'] = highlights
