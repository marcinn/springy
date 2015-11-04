# Springy

Springy is a Django wrapper for elasticsearch.

Originally based on BungieSearch, but with many conceptual changes.
It is written almost from scratch.


## Design and goals

Springy is build over `elasticsearch-dsl-py` and `elasticsearch-py`.

But due to limitations and design misconceptions of `elasticsearch-dsl`,
it will be dropped in far future. Springy will provide own schema/doctype
definition and querying layers.


Springy goals:

    * easy, queryset-like index querying
    * crossindex querying,
    * easy and fast indices managing,
    * easy document creation and validation,
    * mapping models to documents,
    * Django management commands,
    * automated document updates on model updates.


## Current status

    * querying is available via extended `Search` class provided by
      `elasticsearch-dsl`, which is wrapped in `ModelIndex` class
    * index managing supports `initialize` and `clear` operations
    * support for bulk create/update
    * updating index from QuerySet or any generator/iterable
    * simple composition layer for mapping models to documents
      (`ModelIndex`)

Springy is under development. Use at own risk.

## Example


### Defining an index

This declaration maps Product model into `products` index.  A proper doctype
is automatically generated from specified fields and model definition.

```
class ProductIndex(ModelIndex):
    class Meta:
        index = 'products'
        model = Product
        fields = ('name', 'description', 'price', 'default_picture')

    def get_query_set(self):
        return super(ProductIndex, self).get_query_set().filter(is_published=True)
```

Warning! This API will be changed. ElasticSearch supports many DocTypes
in one index, but index structure is shared between all. Index declaration will
be separated from doctype/models mappings.

### Indexing

```
products = ProductIndex()
products.initialize()         # run only once!
products.update_index()
```

### Querying

```
products = ProductIndex()
result = products.query_string('mouse OR keyboard')
```

### Clearing index

```
products = ProductIndex()
products.clear_index()
```

## License

BSD



