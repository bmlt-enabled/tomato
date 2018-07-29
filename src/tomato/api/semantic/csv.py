import csv
from django.db.models.query import QuerySet
import logging
from . import model_get_value


logger = logging.getLogger('django')


class StreamingCSVBuffer:
    def write(self, value):
        return value


def model_to_csv(writer, model, map):
    d = {}
    for to_attr in writer.fieldnames:
        from_params = map.get(to_attr, None)
        if from_params is None:
            continue
        if len(from_params) > 1:
            qualifier = from_params[1]
            if not qualifier(model):
                continue
        from_attr = from_params[0]
        value = model_get_value(model, from_attr)
        d[to_attr] = value
    return writer.writerow(d)


def models_to_csv(models, field_map, fieldnames=None):
    if not fieldnames:
        fieldnames = []
        for k, v in field_map.items():
            if len(v) > 1:
                try:
                    model = next(models.iterator())
                except StopIteration:
                    pass
                else:
                    qualifier = v[1]
                    if qualifier(model):
                        fieldnames.append(k)
            else:
                fieldnames.append(k)

    writer = csv.DictWriter(StreamingCSVBuffer(), fieldnames=fieldnames, quoting=csv.QUOTE_ALL, lineterminator='\n')

    def gen():
        header = dict(zip(writer.fieldnames, writer.fieldnames))
        try:
            yield writer.writerow(header)
            iterator = models.iterator() if isinstance(models, QuerySet) else models
            for m in iterator:
                yield model_to_csv(writer, m, field_map)
        except Exception as e:
            logger.error('Error in iterator: {}'.format(str(e)))
            raise

    return gen()
