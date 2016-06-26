"""
HTML forms.
"""

#Standard
import re
import collections


#Third Party
from werkzeug.datastructures import OrderedMultiDict


#Local


from ..compat import iteritems, encode_if_py2
from ..tabulate import tabulate
from .. import utils
from . import fields
from .. import helpers
from .. import exceptions


_tags = ['input', 'textarea', 'select']
_tag_ptn = re.compile(
    '|'.join(_tags),
    re.I
)


def _group_flat_tags(tag, tags):
    """Extract tags sharing the same name as the provided tag. Used to collect
    options for radio and checkbox inputs.

    :param Tag tag: BeautifulSoup tag
    :param list tags: List of tags
    :return: List of matching tags

    """
    grouped = [tag]
    name = tag.get('name', '').lower()
    while tags and tags[0].get('name', '').lower() == name:
        grouped.append(tags.pop(0))
    return grouped


def _parse_field(tag, tags):

    tag_type = tag.name.lower()

    if tag_type == 'input':
        tag_type = tag.get('type', '').lower()
        if tag_type == 'submit':
            return fields.Submit(tag)
        if tag_type == 'file':
            return fields.FileInput(tag)
        if tag_type == 'radio':
            radios = _group_flat_tags(tag, tags)
            return fields.Radio(radios)
        if tag_type == 'checkbox':
            checkboxes = _group_flat_tags(tag, tags)
            return fields.Checkbox(checkboxes)
        return fields.Input(tag)
    if tag_type == 'textarea':
        return fields.Textarea(tag)
    if tag_type == 'select':
        if tag.get('multiple') is not None:
            return fields.MultiSelect(tag)
        return fields.Select(tag)


def _parse_fields(parsed):
    """Parse form fields from HTML.

    :param BeautifulSoup parsed: Parsed HTML
    :return OrderedDict: Collection of field objects

    """
    # Note: Call this `out` to avoid name conflict with `fields` module
    out = []

    # Prepare field tags
    tags = parsed.find_all(_tag_ptn)
    for tag in tags:
        helpers.lowercase_attr_names(tag)

    while tags:
        tag = tags.pop(0)
        try:
            field = _parse_field(tag, tags)
        except exceptions.InvalidNameError:
            continue
        if field is not None:
            out.append(field)

    return out


def _filter_fields(fields, predicate):
    return OrderedMultiDict([
        (key, value)
        for key, value in fields.items(multi=True)
        if predicate(value)
    ])


class Payload(object):
    """Container for serialized form outputs that knows how to export to
    the format expected by Requests. By default, form values are stored in
    `data`.

    """
    def __init__(self):
        self.data = OrderedMultiDict()
        self.options = collections.defaultdict(OrderedMultiDict)

    @classmethod
    def from_fields(cls, fields):
        """

        :param OrderedMultiDict fields:

        """
        payload = cls()
        for _, field in fields.items(multi=True):
            if not field.disabled:
                payload.add(field.serialize(), field.payload_key)
        return payload

    def add(self, data, key=None):
        """Add field values to container.

        :param dict data: Serialized values for field
        :param str key: Optional key; if not provided, values will be added
            to `self.payload`.

        """
        sink = self.options[key] if key is not None else self.data
        for key, value in iteritems(data):
            sink.add(key, value)

    def to_requests(self, method='get'):
        """Export to Requests format.

        :param str method: Request method
        :return: Dict of keyword arguments formatted for `requests.request`

        """
        out = {}
        data_key = 'params' if method.lower() == 'get' else 'data'
        out[data_key] = self.data
        out.update(self.options)
        return dict([
            (key, list(value.items(multi=True)))
            for key, value in iteritems(out)
        ])


def prepare_fields(all_fields, submit_fields, submit):
    """
    TODO: What is this doing?????
    """
    if len(list(submit_fields.items(multi=True))) > 1:
        if not submit:
            raise exceptions.InvalidSubmitError()
        if submit not in submit_fields.getlist(submit.name):
            raise exceptions.InvalidSubmitError()
        return _filter_fields(
            all_fields,
            lambda f: not isinstance(f, fields.Submit) or f == submit
        )
    return all_fields


class Form(object):
    """Representation of an HTML form."""

    def __init__(self, parsed):

        #TODO: This should be an error, create static method from_page
        parsed = helpers.ensure_soup(parsed)
        if parsed.name != 'form':
            parsed = parsed.find('form')
            
        self.parsed = parsed
        self.action = self.parsed.get('action')
        self.method = self.parsed.get('method', 'get')
        self.fields = OrderedMultiDict()
        for field in _parse_fields(self.parsed):
            self.add_field(field)

    def add_field(self, field):
        """Add a field.

        :param field: Field to add
        :raise: ValueError if `field` is not an instance of `BaseField`.

        """
        if not isinstance(field, fields.BaseField):
            raise ValueError('Argument "field" must be an instance of BaseField')
        self.fields.add(field.name, field)

    @property
    def submit_fields(self):
        #TODO: This will need to be changed
        return _filter_fields(
            self.fields,
            lambda field: isinstance(field, fields.Submit)
        )

    @encode_if_py2
    def __repr__(self):
        return self.get_pprint_str()


    def get_pprint_str(self,show_hidden=False):
         #Relevant Properties
        #- method (DONE)
        #- action (DONE)        
        
        MAX_VALUE_LENGTH = 10
        MAX_OPTION_LENGTH = 20

        str = u''
        str += 'Form Object:\n'
        #str += '%s\n' % utils.get_opening_tag_text(self.parsed)        
        
        #TODO: We need to support this
        #str += ' .submit_info: %s\n' %self.submit_info.get_submit_summary_string()
        str += '      .action: "%s"\n' % self.action
        str += '      .method: %s\n' % self.method
        str += '   \n'
        
        #Display of the tag values
        #Let's get:
        #type , name, value, options
        n_hidden = 0
        rows = []
        for key in self.fields:
            obj = self.fields[key]
            #TODO: Move to code which displays whether or not we want to display
            #the code
            #Filters:
            #- submittable - no
            show_field = True
            #if obj.is_submit_option:
            #    show_field = False
            
            
            if obj.is_hidden:
                n_hidden += 1
                show_field = show_hidden
            elif obj.name is None:
                show_field = False
                
                
            if show_field:            
                temp_value = obj.value.__repr__()
                if len(temp_value) > MAX_VALUE_LENGTH:
                    temp_value = temp_value[:MAX_VALUE_LENGTH-3] + '...'
                
                #option_str = obj.options_display_str            
                #if len(temp_value) > MAX_OPTION_LENGTH:
                #    option_str = option_str[:MAX_OPTION_LENGTH-3] + '...'            
                
                rows.append([obj.tag_type_str, obj.name, obj.label, temp_value])
        
        if len(rows) > 0:        
            str += tabulate(rows,headers=['Tag Type','Name','Label','Value'],tablefmt="pipe")
        elif n_hidden > 0:
            str += '    Only hidden fields present in the form\n'
        else:
            str += '    No fields present in the form\n'

        return str

    def keys(self):
        return self.fields.keys()

    def __getitem__(self, item):
        return self.fields[item]

    def __setitem__(self, key, value):
        self.fields[key].value = value

    def serialize(self, submit=None):
        """Serialize each form field to a Payload container.

        :param Submit submit: Optional `Submit` to click, if form includes
            multiple submits
        :return: Payload instance

        """
        include_fields = prepare_fields(self.fields, self.submit_fields, submit)
        return Payload.from_fields(include_fields)
