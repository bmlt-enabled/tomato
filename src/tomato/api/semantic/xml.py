import io
from django.db.models.query import QuerySet
from django.urls import reverse
import logging
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from xml.sax.saxutils import XMLGenerator
from . import model_get_value


logger = logging.getLogger('django')


def get_xml_schema_url(base_url, schema_name):
    return urljoin(base_url, reverse('xsd', kwargs={'schema_name': schema_name}))


def model_to_xml(writer, model, map, sequence_index):
    writer.startElement(name='row', attrs={'sequence_index': str(sequence_index)})
    for to_attr, from_params in map.items():
        if len(from_params) > 1:
            qualifier = from_params[1]
            if not qualifier(model):
                continue
        from_attr = from_params[0]
        value = model_get_value(model, from_attr)
        if value:
            writer.startElement(name=to_attr, attrs={})
            writer.characters(value)
            writer.endElement(name=to_attr)
    writer.endElement(name='row')


def models_to_xml(models, field_map, root_element_name, xmlns=None, schema_name=None,
                  sub_models=None, sub_models_field_map=None, sub_models_element_name=None):
    def gen():
        stream = io.StringIO()
        try:
            writer = XMLGenerator(stream, 'utf-8')
            writer.startDocument()
            start_element_attrs = {}
            if xmlns and schema_name:
                start_element_attrs['xmlns'] = xmlns
                start_element_attrs['xmlns:xsi'] = 'http://www.w3.org/2001/XMLSchema-instance'
                schema_url = get_xml_schema_url(xmlns, schema_name)
                start_element_attrs['xsi:schemaLocation'] = '{} {}'.format(xmlns, schema_url)
            writer.startElement(root_element_name, attrs=start_element_attrs)

            stream.seek(0)
            yield stream.getvalue()
            stream.truncate(0)

            i = 0
            iterator = models.iterator() if isinstance(models, QuerySet) else models
            for m in iterator:
                model_to_xml(writer, m, field_map, i)
                stream.seek(0)
                yield stream.getvalue()
                stream.truncate(0)
                i += 1

            if sub_models is not None and sub_models_field_map is not None and sub_models_element_name is not None:
                writer.startElement(sub_models_element_name, attrs={})
                stream.seek(0)
                yield stream.getvalue()
                stream.truncate(0)

                i = 0
                iterator = sub_models.iterator() if isinstance(sub_models, QuerySet) else sub_models
                for m in iterator:
                    model_to_xml(writer, m, sub_models_field_map, i)
                    stream.seek(0)
                    yield stream.getvalue()
                    stream.truncate(0)
                    i += 1
                writer.endElement(sub_models_element_name)

            writer.endElement(root_element_name)
            writer.endDocument()
            stream.seek(0)
            yield stream.getvalue()
        except Exception as e:
            logger.error('Error in iterator: {}'.format(str(e)))
            raise
        finally:
            stream.close()
    return gen()
