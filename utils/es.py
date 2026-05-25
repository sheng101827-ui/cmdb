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


def export_all_assets():
    indices = list(mgmt_models.Table.objects.values_list("name", flat=True))
    if not indices:
        return []

    all_assets = []
    from_ = 0
    size = 1000
    max_assets = 500000

    while from_ < max_assets:
        search = Search(using=es, index=indices).doc_type("data").extra(from_=from_, size=size)
        response = search.execute()
        hits = list(response)
        if not hits:
            break

        for hit in hits:
            all_assets.append({
                "_index": hit.meta.index,
                "_type": hit.meta.doc_type,
                "_id": hit.meta.id,
                "_source": hit.to_dict()
            })

        if len(hits) < size:
            break
        from_ += size

    return all_assets


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
