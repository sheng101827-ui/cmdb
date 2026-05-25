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


def export_all_assets():
    assets = []
    page_size = 1000
    from_ = 0

    indices = [table.name for table in mgmt_models.Table.objects.all()]

    s = Search(using=es, index=indices, doc_type='data')

    while True:
        response = s[from_:from_ + page_size].execute()

        hits = response.hits.hits
        if not hits:
            break

        for hit in hits:
            assets.append(hit.to_dict())

        from_ += page_size

    return assets
