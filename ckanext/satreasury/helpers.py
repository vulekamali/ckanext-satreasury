import ckan.plugins.toolkit as tk


def active_financial_years():
    """ Financial years with at least one package associated with them.
    Ascending order.
    """
    facets = tk.get_action('package_search')(None, {
        'facet.field': ['vocab_financial_years'],
        'rows': 0,
    })['search_facets']['vocab_financial_years']['items']
    return sorted(x['name'] for x in facets)


def latest_financial_year():
    """ Latest financial year that has a public package associated with it.
    """
    return max(active_financial_years())


def packages_for_latest_financial_year(limit=None):
    return tk.get_action('package_search')(None, {
        'fq': 'vocab_financial_years:%s' % latest_financial_year(),
        'rows': limit or 100,
        'sort': 'name asc',
    })['results']
