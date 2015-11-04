from elasticsearch_dsl import Search as BaseSearch


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


class Search(IterableSearch):
    pass

