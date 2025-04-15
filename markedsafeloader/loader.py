import base64
import binascii
import datetime
import re
from yaml import MappingNode, Mark, SafeLoader, SequenceNode, load
from yaml.constructor import ConstructorError

from marked_types import MarkedBool, MarkedBytes, MarkedDate, MarkedDateTime, MarkedDict, MarkedFloat, MarkedInt, MarkedList, MarkedNone, MarkedSet, MarkedStr, MarkedTuple, Markers


class MarkedLoader(SafeLoader):

    def __init__(self, stream):
        self._marked_types = {
            "markedstr": MarkedStr,
            "markedint": MarkedInt,
            "markedfloat": MarkedFloat,
            "markedtuple":  MarkedTuple,
            
            "markedlist": MarkedList,
            "markeddict": MarkedDict,
            "markedset": MarkedSet,
            "markedbytes": MarkedBytes,
            # hackish types:
            "markedbool": MarkedBool,
            "markednonetype": MarkedNone,
        }
        super().__init__(stream)

    def _convert_to_marked_type(self, value, node):
        # Since not all types allow you to just add __mark__
        # I just decided to essentially subclass all types
        # at runtime to add this, this however doesn't always
        # work either so, so some types are handled manually
        # in the below constructors....
        marked_type = f"marked{value.__class__.__name__.lower()}"
        
        if marked_type in self._marked_types:
            marked_value = self._marked_types[marked_type](value)
            marked_value.__mark__ = Markers(start=node.start_mark, end=node.end_mark)
            return marked_value
        else:
            try:
            # Attempt to create marked type
                print(value)
                print(value.__class__)
                new_marked_type = type(marked_type, (value.__class__,), {"__mark__": None})
                self._marked_types[marked_type] = new_marked_type
                print(new_marked_type)
                marked_value = new_marked_type(value)
                marked_value.__mark__ = Markers(start=node.start_mark, end=node.end_mark)
                return marked_value
            except Exception as e:
                print(e)
                raise ConstructorError(None, None,
                        f"failed to create marked type for {value.__class__.__name__}: {node.start_mark}",
                        )

    # def construct_document(self, node):
    #     return self._convert_to_marked_type(super().construct_document(node), node)

    def construct_scalar(self, node):
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if key_node.tag == 'tag:yaml.org,2002:value':
                    return self.construct_scalar(value_node)
        return self._convert_to_marked_type(super().construct_scalar(node), node)


    def construct_mapping(self, node, deep=False):
        return self._convert_to_marked_type(super().construct_mapping(node, deep=deep), node)

    def construct_yaml_null(self, node):
        return self._convert_to_marked_type(super().construct_yaml_null(node), node)

    def construct_yaml_bool(self, node):
        return self._convert_to_marked_type(super().construct_yaml_bool(node), node)

    def construct_yaml_int(self, node):
        return self._convert_to_marked_type(super().construct_yaml_int(node), node)

    def construct_yaml_float(self, node):
        return self._convert_to_marked_type(super().construct_yaml_float(node), node)

    def construct_yaml_binary(self, node):
        return self._convert_to_marked_type(super().construct_yaml_binary(node), node)

    def construct_yaml_timestamp(self, node):
        value = self.construct_scalar(node)
        match = self.timestamp_regexp.match(node.value)
        values = match.groupdict()
        year = int(values['year'])
        month = int(values['month'])
        day = int(values['day'])
        if not values['hour']:
            return MarkedDate(year, month, day, __mark__=Markers(start=node.start_mark, end=node.end_mark))
        hour = int(values['hour'])
        minute = int(values['minute'])
        second = int(values['second'])
        fraction = 0
        tzinfo = None
        if values['fraction']:
            fraction = values['fraction'][:6]
            while len(fraction) < 6:
                fraction += '0'
            fraction = int(fraction)
        if values['tz_sign']:
            tz_hour = int(values['tz_hour'])
            tz_minute = int(values['tz_minute'] or 0)
            delta = datetime.timedelta(hours=tz_hour, minutes=tz_minute)
            if values['tz_sign'] == '-':
                delta = -delta
            tzinfo = datetime.timezone(delta)
        elif values['tz']:
            tzinfo = datetime.timezone.utc
        return MarkedDateTime(year, month, day, hour, minute, second, fraction,
                                 tzinfo=tzinfo, __mark__=Markers(start=node.start_mark, end=node.end_mark))

    def construct_yaml_omap(self, node):
        # Note: we do not check for duplicate keys, because it's too
        # CPU-expensive.
        omap = MarkedList(__mark__= Markers(start=node.start_mark, end=node.end_mark))
        yield omap
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing an ordered map", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap.append((key, value))

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        pairs = MarkedList(__mark__=Markers(start=node.start_mark, end=node.end_mark))
        yield pairs
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing pairs", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            pairs.append((key, value))

    def construct_yaml_set(self, node):
        data = MarkedSet(__mark__=Markers(start=node.start_mark, end=node.end_mark))
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_str(self, node):
        return MarkedStr(self.construct_scalar(node), __mark__=Markers(start=node.start_mark, end=node.end_mark))

    def construct_yaml_seq(self, node):
        data = MarkedList(__mark__=Markers(start=node.start_mark, end=node.end_mark))
        yield data
        data.extend(self.construct_sequence(node))

    def construct_yaml_map(self, node):
        data = MarkedDict(__mark__=Markers(start=node.start_mark, end=node.end_mark))
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_object(self, node, cls):
        data = self._convert_to_marked_type(cls.__new__(cls), node)
        yield data
        if hasattr(data, '__setstate__'):
            state = self.construct_mapping(node, deep=True)
            data.__setstate__(state)
        else:
            state = self.construct_mapping(node)
            data.__dict__.update(state)

    def construct_undefined(self, node):
        raise ConstructorError(None, None,
                "could not determine a constructor for the tag %r" % node.tag,
                node.start_mark)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:null',
        MarkedLoader.construct_yaml_null)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:bool',
        MarkedLoader.construct_yaml_bool)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:int',
        MarkedLoader.construct_yaml_int)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:float',
        MarkedLoader.construct_yaml_float)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:binary',
        MarkedLoader.construct_yaml_binary)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:timestamp',
        MarkedLoader.construct_yaml_timestamp)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:omap',
        MarkedLoader.construct_yaml_omap)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:pairs',
        MarkedLoader.construct_yaml_pairs)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:set',
        MarkedLoader.construct_yaml_set)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:str',
        MarkedLoader.construct_yaml_str)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:seq',
        MarkedLoader.construct_yaml_seq)

MarkedLoader.add_constructor(
        'tag:yaml.org,2002:map',
        MarkedLoader.construct_yaml_map)

MarkedLoader.add_constructor(None,
        MarkedLoader.construct_undefined)

test= """
---
# Example YAML 1.1 document

name: "Jane Doe"
age: 29
is_active: yes
height: 5.6
roles:
  - admin
  - editor
  - viewer
address:
  street: "123 Maple Street"
  city: "Springfield"
  zip: 12345
  state: "IL"
  country: "USA"
created_at: 2025-04-15T10:00:00Z
metadata:
  score: !!float "98.6"
"""

data = load(test, Loader=MarkedLoader)

print(data.__mark__)

print("Address map Whole map start end", data["address"].__mark__ )
for key, value in data.items():
    # to get full line cols you want the start mark of key
    # and the end mark of the value for that key
    # or you can use the dict value as a whole for a start and end
    print(key, " : ", key.__mark__)
    print(value, " : ", value.__mark__)

print("Roles List Whole list start end", data["roles"].__mark__ )
for value in data["roles"]:
    print("Roles:", value, value.__mark__)