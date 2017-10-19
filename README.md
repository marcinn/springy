# Springy

![TravisBadge](https://travis-ci.org/marcinn/springy.svg?branch=master)


Springy is a Django wrapper for elasticsearch.

Originally based on BungieSearch, but with many conceptual changes.
It is written almost from scratch.


## Design and goals

Springy is build over `elasticsearch-dsl-py` and `elasticsearch-py`.

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

## Connections configuration

Springy requires connections configuration to be set in your project'
`settings` module as an `ELASTIC_DATABASES` dictionary. Configuration
is similar to Django `DATABASES` dictionary. 

The default connection name/alias is called `default`. 

Databases configuration is passed through to ElasticSearch-DSL
`conncetions.configure()`, so for the details please look at
http://elasticsearch-dsl.readthedocs.io/en/latest/configuration.html

Minimalistic configuration:

```python
ELASTIC_DATABASES = {
    'default': {
       'hosts': 'localhost',
       }
  }
```
## High-Level API

High-Level API is located in `springy` namespace. To work with these shortcut methods you should call `springy.autodisover()` on application startup.

Available methods:

* `springy.autodiscover()` - find and register search indices in whole Django project
* `springy.index(name)` - retrieve `Index` instance by its name
* `springy.query(*indices)` - query specified indices by their names, returns `Search` lazy object
* `springy.multisearch(index_name=None)` - construct MultiSearch object
  with optional index to perform multisearch queries
* `springy.parse(input_query_string)` - instantiate `Search` with DisMax query parser for specified input

## Autodiscover and index registration

Indices are automatically registered at the import time, so they must be imported explicite via `import` command or autodiscovered by Springy.

The minimal requirements for Django application are:
  * put your app (`my_app` for example) into `INSTALLED_APPS`
  * define indices in `my_app.search` module
  * call `springy.autodiscover()` somewhere, for example in your project `urls` module.
  
*You can autodiscover any module in your apps. Just provide module name as an argument for `springy.autodiscover()`. The default is set to `search`.*

## Examples

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

*Warning! This API may be changed. ElasticSearch supports many DocTypes
in one index, but index structure is shared between all. Index declaration will
be separated from doctype/models mappings.*

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

## Changelog

`0.3.11`
- Added support for Python 3 (Django 1.7.x only for Python 3.4)
- Supported Django versions are 1.7, 1.8, 1.9, 1.10, 1.11

