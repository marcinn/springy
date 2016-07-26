from elasticsearch_dsl import (
        Search as BaseSearch,
        MultiSearch as BaseMultiSearch,
        )


class IterableSearch(BaseSearch):
    """
    This class is used to make search class iterable
    (also fixes https://github.com/elastic/elasticsearch-dsl-py/issues/279)
    """

    def __iter__(self):
        return iter(self.execute())

    def __len__(self):
        return self.count()

    def execute(self):
        try:
            return self._cached_result
        except AttributeError:
            self._cached_result = super(IterableSearch, self).execute()
            return self._cached_result

    def parse(self, query):
        return self.query('query_string', query=query, use_dis_max=True)

    def raw(self, raw_dict):
        return self.update_from_dict(raw_dict)


class Search(IterableSearch):
    pass


class MultiSearch(object):
    def __init__(self, index=None, queries=None):
        self.index = index
        self._queries = BaseMultiSearch(
                index=self.index._meta.index if index else None)

        for query in queries or []:
            self.add(query)

    def raw(self, raw_dict):
        return Search().raw(raw_dict)

    def filter(self, *args, **kw):
        return Search().filter(*args, **kw)

    def query(self, *args, **kw):
        return Search().query(*args, **kw)

    def add(self, *queries):
        for query in queries:
            self._queries = self._queries.add(query)

    def execute(self):
        return self._queries.execute()

    def __iter__(self):
        return iter(self.execute())

    def __len__(self):
        return len(self._queries)
