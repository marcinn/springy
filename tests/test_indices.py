import unittest
import datetime

import django
from django.conf import settings

settings.configure(**{
    'ALLOWED_HOSTS': ['testserver'],
    })

django.setup()

from django.db import models
from elasticsearch_dsl import String
import springy


class MyModel(models.Model):
    test_field = models.CharField(max_length=100)
    class Meta:
        app_label = 'test'


class SpecialFieldAttributeErrorIndex(springy.Index):
    special_field = String()

    class Meta:
        fields = ('test_field', 'special_field',)
        model = MyModel
        index = 'special'

    def prepare_special_field(self, obj):
        raise AttributeError('Inner attribute error')


class SimpleTestIndex(springy.Index):
    special_field = String()

    class Meta:
        fields = ('test_field', 'special_field',)
        model = MyModel
        index = 'simple'

    def prepare_special_field(self, obj):
        return 'special value'


class PreparingDocTypeTestCase(unittest.TestCase):
    def setUp(self):
        self.obj = MyModel(test_field='test value')

    def test_that_custom_prepare_field_func_raise_inner_attribute_error(self):
        idx = SpecialFieldAttributeErrorIndex()
        with self.assertRaises(AttributeError):
            idx.to_doctype(self.obj)

    def test_that_doctype_preparation_contains_model_field_values(self):
        idx = SimpleTestIndex()
        dt = idx.to_doctype(self.obj)
        self.assertEqual(dt.test_field, 'test value')

    def test_that_doctype_preparation_contains_model_prepared_values(self):
        idx = SimpleTestIndex()
        dt = idx.to_doctype(self.obj)
        self.assertEqual(dt.special_field, 'special value')

