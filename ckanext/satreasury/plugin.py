import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class SATreasuryPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IFacets)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'satreasury')

    # IFacets
    def dataset_facets(self, facets_dict, package_type):
        del facets_dict['organization']
        del facets_dict['groups']
        del facets_dict['tags']
        del facets_dict['license_id']
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        del facets_dict['organization']
        del facets_dict['groups']
        del facets_dict['tags']
        del facets_dict['license_id']
        return facets_dict
