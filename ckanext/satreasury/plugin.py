import datetime

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk

import ckanext.satreasury.helpers as helpers


PROVINCES = [
    'Eastern Cape',
    'Free State',
    'Gauteng',
    'KwaZulu-Natal',
    'Limpopo',
    'Mpumalanga',
    'North West',
    'Northern Cape',
    'Western Cape',
]


class SATreasuryPlugin(plugins.SingletonPlugin, tk.DefaultDatasetForm):
    """ Plugin for the SA National Treasury CKAN website.
    """
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer
    def update_config(self, config_):
        tk.add_template_directory(config_, 'templates')
        tk.add_public_directory(config_, 'public')
        tk.add_resource('fanstatic', 'satreasury')

    # IFacets
    def dataset_facets(self, facets_dict, package_type):
        del facets_dict['organization']
        del facets_dict['groups']
        del facets_dict['tags']
        del facets_dict['license_id']
        facets_dict['vocab_financial_years'] = 'Financial Year'
        facets_dict['vocab_provinces'] = 'Province'
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        del facets_dict['organization']
        del facets_dict['groups']
        del facets_dict['tags']
        del facets_dict['license_id']
        return facets_dict

    # IDatasetForm
    def show_package_schema(self):
        schema = super(SATreasuryPlugin, self).show_package_schema()
        schema['tags']['__extras'].append(tk.get_converter('free_tags_only'))
        schema.update({
            'financial_year': [
                tk.get_converter('convert_from_tags')('financial_years'),
                tk.get_validator('ignore_missing')
            ],
            'province': [
                tk.get_converter('convert_from_tags')('provinces'),
                tk.get_validator('ignore_missing')
            ],
        })
        return schema

    def create_package_schema(self):
        schema = super(SATreasuryPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(SATreasuryPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    def _modify_package_schema(self, schema):
        schema.update({
            'financial_year': [
                tk.get_validator('ignore_missing'),
                tk.get_converter('convert_to_tags')('financial_years')
            ],
            'province': [
                tk.get_validator('ignore_missing'),
                tk.get_converter('convert_to_tags')('provinces')
            ]
        })
        return schema

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'financial_years': load_financial_years,
            'provinces': load_provinces,
            'active_financial_years': helpers.active_financial_years,
            'latest_financial_year': helpers.latest_financial_year,
            'packages_for_latest_financial_year': helpers.packages_for_latest_financial_year,
        }


def create_financial_years():
    """ Ensure all necessary financial years tags exist.
    """
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    try:
        vocab = tk.get_action('vocabulary_show')(context, {'id': 'financial_years'})
    except tk.ObjectNotFound:
        vocab = tk.get_action('vocabulary_create')(context, {'name': 'financial_years'})

    tag_create = tk.get_action('tag_create')
    existing = set(t['name'] for t in vocab['tags'])
    for year in set(required_financial_years()) - existing:
        tag_create(context, {
            'name': year,
            'vocabulary_id': vocab['id'],
        })


def load_financial_years():
    create_financial_years()
    try:
        tag_list = tk.get_action('tag_list')
        return tag_list(data_dict={'vocabulary_id': 'financial_years'})
    except tk.ObjectNotFound:
        return None


def required_financial_years():
    # eg. 2017-18
    return ['%s-%s' % (y, y + 1 - 2000)
            for y in xrange(2007, datetime.date.today().year + 2)
            ]


def create_provinces():
    """ Ensure all necessary province tags exist.
    """
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    try:
        vocab = tk.get_action('vocabulary_show')(context, {'id': 'provinces'})
    except tk.ObjectNotFound:
        vocab = tk.get_action('vocabulary_create')(context, {'name': 'provinces'})

    tag_create = tk.get_action('tag_create')
    existing = set(t['name'] for t in vocab['tags'])
    for province in set(PROVINCES) - existing:
        tag_create(context, {
            'name': province,
            'vocabulary_id': vocab['id'],
        })


def load_provinces():
    create_provinces()
    try:
        tag_list = tk.get_action('tag_list')
        return tag_list(data_dict={'vocabulary_id': 'provinces'})
    except tk.ObjectNotFound:
        return None
