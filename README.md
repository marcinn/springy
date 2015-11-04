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
* multiple elastic databases/connections support,
* connections routing,
* automated document updates on model updates.


## Current status

* querying is available via extended `Search` class provided by
  `elasticsearch-dsl`, which is wrapped in `Index` class
* index managing supports `initialize` and `clear` operations
* support for bulk create/update
* updating index from QuerySet or any generator/iterable
* simple composition layer for mapping models to documents
  (`Index`)

**Springy is under development. Use at own risk.**

## Example


### Defining an index

This declaration maps Product model into `products` index.  A proper doctype
is automatically generated from specified fields and model definition.

```python
import springy

class ProductIndex(springy.Index):
    class Meta:
        index = 'products'
        model = Product
        fields = ('name', 'description', 'price', 'default_picture')

    def get_query_set(self):
        return super(ProductIndex, self).get_query_set().filter(is_published=True)
```

Warning! This API may be changed. ElasticSearch supports many DocTypes
in one index, but index structure is shared between all. Index declaration will
be separated from doctype/models mappings.

### Index initialization

```python
idx = ProductIndex()
idx.initialize() 
```

### Indexing

```python
idx = ProductIndex()
idx.update_index()
```

Indexing one model instance:

```python
idx = ProductIndex()
obj = Product.objects.get(id=1)
idx.save(obj)
```

Indexing a queryset:

```python
idx = ProductIndex()
idx.save_many(Product.objects.filter(category__name='keyboards'))
```


### Querying

```python
idx = ProductIndex()
result = idx.query_string('mouse OR keyboard')
```

Result is a `IterableSearch` instance, a "lazy" object, which inherits directly
from `Search` (see `elasticsearch-dsl` for more information and API).

`Index` provides some useful query shortcuts:

* `all()` - return all documents
* `filter()` - shortcut to `Search.filter()`
* `query()` - shortcut to `Search.query()`
* `query_string()` - wrapper for querying by "query string" using DisMax parser.

### Clearing and dropping index

To remove all documents from index:

```python
idx = ProductIndex()
idx.clear_index()
```

To drop index just call:

```
idx.drop_index()
```

## License

BSD


