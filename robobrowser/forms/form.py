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
from .fields import Field
from . import fields
from .. import helpers
from .. import exceptions


_tags = ['input', 'textarea', 'select']
_tag_ptn = re.compile(
    '|'.join(_tags),
    re.I
)

#Some are still missing ...
_TOP_LEVEL_FORM_TAGS = ['input','textarea','select','button']

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
    """
    Parse form fields from HTML.

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
    """
    Container for serialized form outputs that knows how to export to
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





class Form(object):



    """
    http://www.w3.org/TR/html5/forms.html#the-form-element
    
    TODO: Clean this up ...
    ------------------------
    NYI accept-charset : Character encodings to use for form submission
    NYI action : URL to use for form submission
    IGNORE autocomplete - Default setting for autofill feature for controls in the form
    NYI enctype - Form data set encoding type to use for form submission
    HALF IMPLEMENTED method - HTTP method to use for form submission
    name - Name of form to use in the document.forms API
    novalidate - Bypass form control validation for form submission
    target - Browsing context for form submission


    
    Most fields can be set by:
    f['<field_name>'].value = '<text_value>'
    
    
    Attributes
    ----------
    tag : 
        The form tag that this object is representing
    field_tags: [bs4]
        All relevant tags
    field_objects
    tags_per_object
    method : string
        Method for submission
    action : string or None
        We'll keep this but also expose the URL as well.
    submit_info : Object in this module
        
    
    
    """

    #TODO:
    # - show editable fields (non-hidden)
    # - show options for submission    

    def __init__(self,soup_tag):
     
        """
        
        Parameters
        ----------
        soup_tag : bs4.BeautifulSoup OR bs4.element.Tag
            Beautiful Soup 4 representation of a form tag. Alternatively, 
            parents of a form can be passed in and the code will find the <form>
            tag. In this case an error will be thrown if there are no forms found
            or if more than one form is found.
         
        """      
        
        #TODO: Write method to ensure input is bs4        
        #soup_tag.__class__.__name__
        
       
        #Ensure form_tag is actually a 'form' tag =>  <form ...>
        #--------------------------------------------------------
        tag_type = soup_tag.name.lower()
        if tag_type != 'form':
            all_form_tags = soup_tag.find_all('form')
            if len(all_form_tags) == 1:
                soup_form_tag = all_form_tags[0]
            elif len(all_form_tags) == 0:
                raise Exception('No <form> tags found')
            else:
                raise Exception('Multiple <form> tags found, expecting only 1')
        else:
            soup_form_tag = soup_tag            
            
        self.tag = soup_form_tag
        
        #Step 1: Get all field tags for the form
        #---------------------------------------
        tags = self._get_field_tags(soup_form_tag)
        self.field_tags = list(tags)
              
        
        #Step 2: Create relevant field objects
        #-------------------------------------
        self.field_objects,self.tags_per_object = Field.initialize_field_objects(tags)
        
        #TODO: Check for valid names ...
        self._fields = {x.name: x for x in self.field_objects} 

        #Step 3: Populate submit list
        #------------------------------------            
        self.submit_info = SubmitInfo(self.field_objects)


    @staticmethod
    def _get_field_tags(soup_form_tag):

        """
        ------------- Initialization Helper -------------
        
        This returns all relevant field tags for the form. It also
        handles the case where a field tag is outside of the form and is linked
        via the 'form' attribute.
        
        For an example of the 'form' attribute see: 
            http://www.w3schools.com/tags/tryit.asp?filename=tryhtml5_select_form
            
        Parameters
        ----------
        soup_form_tag : bs4.element.Tag
            i.e. a tag of the form <form ...>
        
        """
        
        #* This appears to preserve order in the document which is important
        #  for some servers
        local_field_tags = soup_form_tag.find_all(_TOP_LEVEL_FORM_TAGS)         
        
        p = soup_form_tag.parent
        if p is None:
            #This generally happens only during test input cases
            return local_field_tags
        
        #Else, we have to look for fields that are outside of the form ...        
        while True:
            next_parent = p.parent
            if next_parent is None:
                break
            p = next_parent
            
        root_tag = p
        form_name = soup_form_tag.get('name')
        
        all_field_tags = root_tag.find_all(_TOP_LEVEL_FORM_TAGS) 

        #Early exit if no additional tags are found
        if len(all_field_tags) == len(local_field_tags):
            return local_field_tags
     
        #A tag belongs to the form if:
        #1) It is a child of the form tag OR
        #2) It has the attribute "form" with the value matching that
        #   of the form's name
        return [x for x in all_field_tags if (x.get('form',None)) == form_name or x in local_field_tags]

    
    def pprint(self,show_hidden=False):
        
        """
                TODO: Move this to a callable method with other options
            - have __repr__ call that method
            - don't display no name entries by default
            - don't display hidden by default
        """
        pass
    
    def get_pprint_str(self,show_hidden=False):
        """
        TODO: Merge type and name, make sure name is the last element in the tag
            - give this a try, I might not like it
        TODO: Rather than the class, I think I want a nice html display
        of the element:
            e.g. RadioInputGroup =>    <input type="radio" ...
            Select      =>      <select ...
            TextInput   =>      <input type='text'
        
        """
        
        #Relevant Properties
        #- method (DONE)
        #- action (DONE)        
        
        MAX_VALUE_LENGTH = 10
        MAX_OPTION_LENGTH = 20

        str = u''
        str += 'Form Object:\n'    
        str += '   .submit_info: %s\n' %self.submit_info.get_submit_summary_string()
        str += '        .action: "%s"\n' % self.action
        str += '        .method: %s\n' % self.method
        str += '   \n'
        
        #Display of the tag values
        #Let's get:
        #type , name, value, options
        rows = []
        n_hidden = 0
        for obj in self.field_objects:
            #TODO: Move to code which displays whether or not we want to display
            #the code
            #Filters:
            #- submittable - no
            show_field = True
            if obj.is_submit_option:
                show_field = False
            elif obj.is_hidden:
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
            str += '   Only hidden fields present in the form\n'
        else:
            str += '   No fields present in the form\n'

        return str
    
    @encode_if_py2
    def __repr__(self):
        return self.get_pprint_str()
    
    def __getitem__(self, key):
        """
        TODO: Build in support based on integers, strings or even a query
        """
        return self._fields[key]

    def list_param(param_name):
        """
        
        Examples
        --------
        f.list_param('label')
        
        """
        #I'd like this function to be able to list an attribute
        #of all tags        
        pass

    def find(self,*args,**kwargs):

        """
        Equivalent to BeautifulSoup's tag find() method but
        a local form object is returned instead of the underlying tag.
        
        Only top level fields are searchable. These include:
        
            - 'input'
            - 'select'
            - 'textarea'
            - 'button'
        
        Tags that are grouped will only return the group container:
            e.g. <input type='radio' ... >
        Returns:
            RadioInputGroup NOT RadioInput
        
        Examples:
        ---------
        I = f.find('input',{'id':'Email'})
        
        Returns
        -------
        Field object or None
        
        """
        
        """
        TODO: I'm working on improving this ...
        find_all => bs4.element.ResultSet
        
        ResultSet inherits from list, so we can combine them via list methods
        bs4.element.Tag
        
        """        
        
        #TODO: build in support for name AND tag_name
        #
        
        #TODO: This won't work for orphaned tags oustide of the form
        tag_result = self.tag.find(*args,**kwargs)

        if tag_result is None:
            return None

        final_object = None
        for field_object,object_tags in zip(self.field_objects,self.tags_per_object):
            #This was made more complex in that 'in' for Beautiful Soup 
            #apparently tests for nested tags, and is not a "is" 
            #comparison over a list
            # i.e. I was gettting a match with:
            # <input name='1'><input name='2'></input></input>
            #
            # I was getting a match for 2 when looking at 1, since 2 is 'in' 1
            if tag_result is object_tags:
                final_object = field_object
                break
            elif hasattr(final_object,'tags'):
                temp = final_object.tags
                for tag in temp:
                    if tag_result is tag:
                        final_object = field_object
                        break
            
        return field_object
        

    
    def find_all(self,tag_id,*args,**kwargs):
        
        """
        Equivalent to BeautifulSoup's tag find_all() method but
        a local form object is returned instead of the underlying tag.
        
        Only top level fields are searchable. These include:
        
            - 'input'
            - 'select'
            - 'textarea'
            - 'button'
        
        Tags that are grouped will only return the group container:
            e.g. <input type='radio' ... >
        Returns:
            RadioInputGroup NOT RadioInput
        
        Examples:
        ---------
        I = f.find_all('input',{'type':'text'})
        
        Returns:
        --------
        [Field objects] OR []
        
        """
        
        if tag_id not in _TOP_LEVEL_FORM_TAGS:
            raise Exception('Only top level tags can be found using find()')
        
        tag_results = self.tag.find_all(tag_id,*args,**kwargs)
        if len(tag_results) == 0:
            return []
        
        results = []
        for tag in tag_results:
            for i,object_tags in enumerate(self.tags_per_object):
                if tag is object_tags or tag in object_tags:
                    results.append(self.tags_per_object[i])
                    break
        
        return results
    
    @property
    def method(self):
        """
        http://www.w3.org/TR/html5/forms.html#attr-fs-method
        
        If not present the default is "GET"
        If invalid the default is "GET"
        """

        #TODO: Check submit_via status

        return_method = self.tag.get('method','GET').upper()
        if return_method != 'POST' and return_method != 'GET':
            return_method = 'GET'
               
        temp_method = self.submit_info.method
        if temp_method is not None:
            return_method = temp_method
        
        return return_method
        
    @property
    def action(self):
        """
        http://stackoverflow.com/questions/9401521/is-action-really-required-on-forms
        
        Empty refers to the current URI
        """

        #The default behavior        
        action_to_return = self.tag.get('action',None)
        
        #We may override with a submit option (submit button)

        temp_action = self.submit_info.action
        if temp_action is not None:
            action_to_return = temp_action
        
        if action_to_return is None:
            action_to_return = ""
            
        return action_to_return
        
    @property
    def enctype(self):
        pass

    def get_payload(self, submit=None):
        """
        
        Returns
        -------
        dict : Contains an entry for the next request        
        
        """

        if submit is not None:
            raise Exception("not yet coded")
        
        temp = []
        for x in self.field_objects:
            if x.include_in_request:
                temp.extend(x.get_final_values())
         
        payload = {}    
        if self.method.lower() == 'get':
            payload['params'] = dict(temp)
        else:
            #Noramlly you might expect a dict here, but the list of tuples
            #allows for repeated "keys"
            #http://stackoverflow.com/questions/23384230/how-to-post-multiple-value-with-same-key-in-python-requests
            payload['data'] = temp

        
        return payload

class SubmitInfo(object):
    """
    I'd like this to handle resolving the form tag and any submit options
    to declutter the Form tag
    
    Attributes
    ----------
    is_submit_option
    submit_via: a submittable field object
        Tag to use for submitting the form
    
    """    

    

    def __init__(self,field_objects):
        
        self.submit_options = [x for x in field_objects if x.is_submit_option]        

        if len(self.submit_options) > 0:
            self._submit_via = self.submit_options[0]
        else:
            self._submit_via = None
     
    #TODO: Rename this ...       
    @property
    def is_submit_option(self):
        return self._submit_via is not None
        
    def get_submit_summary_string(self):
        if self.is_submit_option:
            return utils.get_opening_tag_text(self._submit_via.tag)
        else:
            if len(self.submit_options) == 0:
                return "No submit options detected"
            else:
                return "No submit option selected"
         
    @property
    def submit_via(self,value):
        return self._submit_via 
        
    @submit_via.setter 
    def submit_via(self,value):
        """
        Parameters
        ----------
        value : Should be a Field Object
        
        """
        #TODO: Check for field type
        if value.is_submit_option:
            self._submit_via = value
        else:
            raise ValueError('Input is not available as a submit option')

     
    def submit_name(self,name):
        #TODO: find name in options and change submit_via
        pass
    
    def submit_id(self,tag_id):
        #TODO: find id in options and change submit_via
        pass
        
    @encode_if_py2
    def __repr__(self):
        str = u''
        str += 'Submit Info Object:\n'
        str += '    .submit_via: %s\n' % self.get_submit_summary_string()
        str += '        .action: %s\n' % self.action
        str += '        .method: %s\n' % self.method
        str += '.submit_options: [Field (n = %d)]\n' % len(self.submit_options)                      
        for i, obj in enumerate(self.submit_options):
            if obj is self._submit_via:
                selected = '[x]'
            else:
                selected = '[ ]'
                
            str += '    %s %d)  %s\n' % (selected, i, utils.get_opening_tag_text(obj.tag))
        
        return str
        
    @property
    def action(self):
        if self.is_submit_option:
            return self._submit_via.action
        else:
            return None
            
    @property
    def method(self):
        if self.is_submit_option:
            return self._submit_via.method
        else:
            return None  




"""=================   Input Tags ======================="""
##http://www.w3schools.com/html/html_form_input_types.asp  