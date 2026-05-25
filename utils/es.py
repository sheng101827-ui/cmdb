from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch_dsl import Search

from django.conf import settings

from mgmt import models as mgmt_models


es = Elasticsearch(hosts=settings.ELASTICSEARCH["hosts"],
                   # sniff_on_start=True,
                   # # refresh nodes after a node fails to respond
                   # sniff_on_connection_fail=True,
                   # # and also every 60 seconds
                   # sniffer_timeout=12,
                   http_auth=(settings.ELASTICSEARCH["username"], settings.ELASTICSEARCH["password"])
                   )


indices_client = IndicesClient(es)


class Mapping:
    MAP = {
        0: {"type": "keyword"},
        1: {"type": "long"},
        2: {"type": "double"},
        3: {"type": "date", "format": "yyyy-MM-dd'T'HH:mm:ss"},
        4: {"type": "date", "format": "yyyy-MM-dd"},
        5: {"type": "boolean"},
        6: {"type": "ip"}
    }

    def _generate_mapping(self, table):
        mapping = {}
        for field in table.fields.all():
            mapping[field.name] = self.MAP[field.type]
        return mapping

    def generate_data_mapping(self, table):
        system_mapping = {
            "S-creator": self.MAP[0],
            "S-creation-time": self.MAP[3],
            "S-last-modified": self.MAP[0]
        }
        field_mapping = self._generate_mapping(table)
        return dict(**system_mapping, **field_mapping)

    def generate_record_data_mapping(self, table):
        system_mapping = {
            "S-data-id": self.MAP[0],
            "S-changer": self.MAP[0],
            "S-update-time": self.MAP[3]
        }
        field_mapping = self._generate_mapping(table)
        return dict(**system_mapping, **field_mapping)

    def generate_deleted_data_mapping(self, table):
        system_mapping = {
            "S-delete-people": self.MAP[0],
            "S-delete-time": self.MAP[3]
        }
        field_mapping = self._generate_mapping(table)
        return dict(**system_mapping, **field_mapping)


def export_all_assets(indices=None, doc_type="data"):
    """
    导出全部资产数据
    :param indices: 要查询的索引列表，默认为 None（查询所有索引）
    :param doc_type: 文档类型，默认为 "data"
    :return: 包含所有资产数据的列表
    """
    all_assets = []
    batch_size = 1000
    from_ = 0
    
    while True:
        s = Search(using=es, index=indices, doc_type=doc_type)
        s = s[from_:from_ + batch_size]
        response = s.execute()
        
        if not response.hits:
            break
            
        for hit in response.hits:
            all_assets.append(hit.to_dict())
            
        if len(response.hits) < batch_size:
            break
            
        from_ += batch_size
    
    return all_assets
