import json
from collections import OrderedDict
from django.conf import settings
from django.db.models.query import QuerySet
import logging
from . import model_get_value


logger = logging.getLogger('django')


class StreamList(list):
    def __init__(self, models, field_map, return_attrs, *args, **kwargs):
        self.models = models
        self.field_map = field_map
        self.return_attrs = return_attrs
        super().__init__(*args, **kwargs)

    def __iter__(self):
        try:
            for m in self.models.iterator():
                yield model_to_json(m, self.field_map, return_attrs=self.return_attrs)
        except Exception as e:
            logger.error('Error in iterator: {}'.format(str(e)))
            raise

    def __len__(self):
        try:
            next(self.__iter__())
        except StopIteration:
            return 0
        else:
            return 1


def model_to_json(model, map, return_attrs=None):
    ret = OrderedDict()
    keys = return_attrs if return_attrs else map.keys()
    for to_attr in keys:
        from_params = map.get(to_attr, None)
        if from_params is None:
            continue
        if len(from_params) > 1:
            qualifier = from_params[1]
            if not qualifier(model):
                continue
        from_attr = from_params[0]
        value = model_get_value(model, from_attr)
        ret[to_attr] = value
    return ret


def models_to_json(models, field_maps, return_attrs=None, parent_keys=None):
    if not isinstance(models, tuple):
        models = (models,)
    if not isinstance(field_maps, tuple):
        field_maps = (field_maps,)
    if not isinstance(return_attrs, tuple):
        return_attrs = (return_attrs,)
    if parent_keys is not None and not isinstance(parent_keys, tuple):
        parent_keys = (parent_keys,)
    if len(models) == 1:
        if isinstance(models[0], QuerySet):
            ret = StreamList(models[0], field_maps[0], return_attrs[0])
        else:
            ret = [model_to_json(m, field_maps[0], return_attrs[0]) for m in models[0]]
        if parent_keys:
            ret = {parent_keys[0]: ret}
    else:
        if not parent_keys:
            raise Exception('parent_keys must be set')
        ret = {}
        for i in range(len(models)):
            if isinstance(models[i], QuerySet):
                ret[parent_keys[i]] = StreamList(models[i], field_maps[i], return_attrs[i])
            else:
                ret[parent_keys[i]] = [model_to_json(m, field_maps[i], return_attrs[i]) for m in models[i]]

    if getattr(settings, 'DEBUG', False):
        return json.JSONEncoder(indent=2).iterencode(ret)
    return json.JSONEncoder(separators=(',', ':')).iterencode(ret)
