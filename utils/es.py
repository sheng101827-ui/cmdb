from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient

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


from elasticsearch_dsl import Search

def export_all_assets_by_pagination(index_name):
    """
    【警告】：按照需求描述使用 from_ 和 size 循环分页查询（不推荐）。
    注意：Elasticsearch 默认的 max_result_window 为 10000。
    当 from_ + size > 10000 时，会抛出 Result window is too large 异常。
    因此这种方法无法直接导出 50 万条数据，除非修改集群配置，但这会带来极大的内存压力。
    """
    all_assets = []
    from_ = 0
    size = 1000
    
    while True:
        # 使用切片语法 [from_:from_ + size] 设置分页
        s = Search(using=es, index=index_name)[from_:from_ + size]
        response = s.execute()
        
        if not response.hits:
            break
            
        for hit in response:
            all_assets.append(hit.to_dict())
            
        from_ += size
        
    return all_assets

def export_all_assets(index_name):
    """
    【推荐】：正确的导出 50 万条资产数据的方式是使用 scan (底层封装了 Scroll API)。
    专门用于处理大量数据的导出，不受 max_result_window 限制。
    """
    all_assets = []
    s = Search(using=es, index=index_name)
    
    # scan() 方法每次在后台通过 scroll 获取数据，无需手动维护 from_ 和 size
    for hit in s.scan():
        all_assets.append(hit.to_dict())
        
    return all_assets
