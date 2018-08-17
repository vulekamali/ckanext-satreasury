"""
Based on
https://github.com/stadt-karlsruhe/ckanext-discovery/blob/master/ckanext/discovery/plugins/similar_datasets/__init__.py
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import json

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.lib.search.common import make_connection
from ckan.common import config


log = logging.getLogger(__name__)

MAX_NUM = 5

def get_similar_datasets(context, data_dict):
    '''
    Get similar datasets for a dataset.
    :param string id: ID or nameof the target dataset.
    :return: A list of similar dataset dicts sorted by decreasing score.
    '''
    id_or_name = data_dict['id']
    package = tk.get_action('package_show')({'ignore_auth': True}, {'id': id_or_name})
    id = package['id']
    solr = make_connection()
    query = 'id:"{}"'.format(id)
    fields_to_compare = 'text'
    fields_to_return = 'id validated_data_dict score'
    site_id = config.get('ckan.site_id')
    filter_query = '''
        +site_id:"{}"
        +dataset_type:dataset
        +state:active
        +capacity:public
        -organization:national-treasury
        '''.format(site_id)
    results = solr.more_like_this(q=query,
                                  mltfl=fields_to_compare,
                                  fl=fields_to_return,
                                  fq=filter_query,
                                  rows=MAX_NUM)
    log.debug('Similar datasets for {}:'.format(id))
    print('Similar datasets for {}:'.format(id))
    for doc in results.docs:
        log.debug('  {id} (score {score})'.format(**doc))
    return [json.loads(doc['validated_data_dict']) for doc in results.docs]


class SimilarDatasetsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)

    def get_actions(self):
        return {
            'similar_datasets': get_similar_datasets,
        }
