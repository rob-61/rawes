#
#   Copyright 2012 The HumanGeo Group, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rawes
import unittest
import config

import logging
log_level = logging.ERROR
log_format = '[%(levelname)s] [%(name)s] %(asctime)s - %(message)s'
logging.basicConfig(format=log_format, datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)
soh = logging.StreamHandler(sys.stdout)
soh.setLevel(log_level)
logger = logging.getLogger("rawes.tests")
logger.addHandler(soh)


class TestElasticCore(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        http_url = '%s:%s' % (config.ES_HOST, config.ES_HTTP_PORT)
        self.es_http = rawes.Elastic(url=http_url)
        thrift_url = '%s:%s' % (config.ES_HOST, config.ES_THRIFT_PORT)
        self.es_thrift = rawes.Elastic(url=thrift_url)

    def test_http(self):
        self._reset_indices(self.es_http)
        self._test_document_search(self.es_http)
        self._test_document_update(self.es_http)
        self._test_document_delete(self.es_http)

    def test_thrift(self):
        self._reset_indices(self.es_thrift)
        self._test_document_search(self.es_thrift)
        self._test_document_update(self.es_thrift)
        self._test_document_delete(self.es_thrift)

    def _reset_indices(self, es):
        # If the index does not exist, test creating it and deleting it
        index_status_result = es.get('%s/_status' % config.ES_INDEX)
        if 'status' in index_status_result and index_status_result['status'] == 404:
            create_index_result = es.put(config.ES_INDEX)

        # Test deleting the index
        delete_index_result = es.delete(config.ES_INDEX)
        index_deleted = es.get('%s/_status' % config.ES_INDEX)['status'] == 404
        self.assertTrue(index_deleted)

        # Now remake the index
        es.put(config.ES_INDEX)
        index_exists = es.get('%s/_status' % config.ES_INDEX)['ok'] == True
        self.assertTrue(index_exists)

    def _test_document_search(self, es):
        # Create some sample documents
        result1 = es.post('%s/tweet/' % config.ES_INDEX, data={
            'user': 'dwnoble',
            'post_date': '2012-8-27T08:00:30',
            'message': 'Tweeting about elasticsearch'
        }, params={
            'refresh': True
        })
        self.assertTrue(result1['ok'])
        result2 = es.put('%s/post/2' % config.ES_INDEX, data={
            'user': 'dan',
            'post_date': '2012-8-27T09:30:03',
            'title': 'Elasticsearch',
            'body': 'Blogging about elasticsearch'
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(result2['ok'])

        # Search for documents of one type
        search_result = es.get('%s/tweet/_search' % config.ES_INDEX, data={
            'query': {
                'match_all': {}
            }
        }, params={
            'size': 2
        })
        self.assertTrue(search_result['hits']['total'] == 1)

        # Search for documents of both types
        search_result2 = es.get('%s/tweet,post/_search' % config.ES_INDEX, data={
            'query': {
                'match_all': {}
            }
        }, params={
            'size': '2'
        })
        self.assertTrue(search_result2['hits']['total'] == 2)

    def _test_document_update(self, es):
        # Ensure the document does not already exist (using alternate syntax)
        search_result = es[config.ES_INDEX].sometype['123'].get()
        self.assertFalse(search_result['exists'])

        # Create a sample document (using alternate syntax)
        insert_result = es[config.ES_INDEX].sometype[123].put(data={
            'value': 100,
            'other': 'stuff'
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(insert_result['ok'])

        # Perform a simple update (using alternate syntax)
        update_result = es[config.ES_INDEX].sometype['123']._update.post(data={
            'script': 'ctx._source.value += value',
            'params': {
                'value': 50
            }
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(update_result['ok'])

        # Ensure the value was updated
        search_result2 = es[config.ES_INDEX].sometype['123'].get()
        self.assertTrue(search_result2['_source']['value'] == 150)

    def _test_document_delete(self, es):
        # Ensure the document does not already exist (using alternate syntax)
        search_result = es[config.ES_INDEX].persontype['555'].get()
        self.assertFalse(search_result['exists'])

        # Create a sample document (using alternate syntax)
        insert_result = es[config.ES_INDEX].persontype[555].put(data={
            'name': 'bob'
        }, params={
            'refresh': 'true'
        })
        self.assertTrue(insert_result['ok'])

        # Delete the document
        delete_result = es[config.ES_INDEX].delete('persontype/555')
        self.assertTrue(delete_result['ok'])

        # Verify the document was deleted
        search_result = es[config.ES_INDEX]['persontype']['555'].get()
        self.assertFalse(search_result['exists'])
