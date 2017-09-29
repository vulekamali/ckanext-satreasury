import ckan.plugins.toolkit as tk


def latest_financial_year():
    """ Latest financial year that has a public package associated with it.
    """
    facets = tk.get_action('package_search')(None, {
        'facet.field': ['vocab_financial_years'],
        'rows': 0,
    })['search_facets']['vocab_financial_years']['items']
    return max(x['name'] for x in facets)


def packages_for_latest_financial_year(limit=None):
    return tk.get_action('package_search')(None, {
        'fq': 'vocab_financial_years:%s' % latest_financial_year(),
        'rows': limit or 100,
        'sort': 'name asc',
    })['results']
