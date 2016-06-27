# -*- coding: utf-8 -*-
"""
This module contains form field classes. These classes represent specific pieces
of information that can be entered into a form. The classes encapsulate an 
underlying bit of html code that specifies how the field should act.

e.g. <input type="text" (html tag)  ==> TextInput (field class)
"""

from .. import utils
from ..compat import iteritems, encode_if_py2

class CodeError(Exception):
    """
    I place these in places where things shouldn't happen if they do it is most
    likely my fault.
    """
    pass

class Field(object):

    """
    
    #TODO: Force inheritance from here and use abstract properties
    
    Required methods
    ----------------
    get_final_values    
    
    
    Required properties are described in SimpleField.    
    
    See Also
    --------
    SimpleField
    SubmitField
    Input
    Button
    Select
    """


    @staticmethod
    def initialize_field_objects(tags):
        
        """
        
        This method is meant to handle the details of initializing field
        objects given bs4 object tags. This is essentially a factory method.

        Returns
        -------
        (field_objects,tags_per_object)
        field_objects : [classes in this module]
        tags_per_object : [bs4 objects]
            
            
        See Also
        --------
        .Form.Form.__init__()
        """

        objects = []
        tags_per_object = []
        while tags:
            tag = tags.pop(0)
            tag_type = tag.name.lower()
            tag_name = tag.get('name',None)
            
            if tag_type == 'input':
                input_type = tag.get('type').lower()
                #TODO: I am not thrilled with this approach
                #Can submit via image as well, see:
                #http://www.w3schools.com/tags/tryit.asp?filename=tryhtml_input_src
                if input_type == 'radio':
                    radio_tags = Field._get_group_tags(tag,tags)
                    new_object = RadioInputGroup(radio_tags)
                    objects.append(new_object)
                    tags_per_object.append(radio_tags)
                elif input_type == 'checkbox':
                    checkbox_tags = Field._get_group_tags(tag,tags)
                    new_object = CheckboxInputGroup(checkbox_tags)
                    objects.append(new_object)
                    tags_per_object.append(checkbox_tags)
                else:
                    new_object = Input.create(tag)
                    objects.append(new_object)
                    tags_per_object.append(tag)
            else:
                if tag_name is None:
                    #This could indicate some javascript in play, i.e. that
                    #the name may be dynamically assigned, but we'll
                    #ignore it for now.
                    continue
                elif tag_type == 'textarea':
                    new_object = TextArea(tag)
                    objects.append(new_object)
                    tags_per_object.append(tag)
                elif tag_type == 'select':
                    new_object = Select(tag)
                    objects.append(new_object)
                    tags_per_object.append(tag)
                elif tag_type == 'button':
                    new_object = Button(tag)
                    objects.append(new_object)
                    tags_per_object.append(tag)
                else:
                    raise CodeError('Tag name not recognized: ' + tag_name)

            new_object.resolve_label()

        return (objects,tags_per_object)

    def resolve_label(self):
    #This is the default resolvle label. Eventually I'd like to remove it
        self.label = ''
        if hasattr(self,'tag'):
            tag = self.tag
            aria_label = tag.get('aria-label',None)
            if aria_label is not None:
                self.label = aria_label

    @staticmethod
    def _get_group_tags(tag, tags):
        """
        ------------- Initialization Helper -------------
        
        Attributes
        ----------
        tag : [tag]
        tags : [bs4 tags]
            All remaining tags left to process        
        
        Extract tags sharing the same name as the provided tag. Used to collect
        options for radio and checkbox inputs.

    
        """
        #TODO: This is wrong for Google Scholar        
        
        #http://stackoverflow.com/questions/949098/python-split-a-list-based-on-a-condition        
        #There has got to be a better way of doing this ...
   
        current_name = tag.get('name').lower()
        all_tag_names = [x.get('name','').lower() for x in tags]
        same_name_tags = [x for (x,name) in zip(tags,all_tag_names) if name == current_name]
        different_name_tags = [x for (x,name) in zip(tags,all_tag_names) if name != current_name]
        
        tags[:] = different_name_tags #reference update        
        
        same_name_tags = [tag] + same_name_tags        
        
#        grouped = [tag]
#        name = 
#        while tags and tags[0].get('name', '').lower() == name:
#            grouped.append(tags.pop(0))
        return same_name_tags


class SimpleField(Field):
    
    """
    
    Simple fields are tags without a nested set of options or multiple tags
    with the same name. Most fields inherit from this class.
    
    Things that are not simple fields
    ---------------------------------
    1) CheckboxInputGroup
        Checkboxes have multiple tags that are linked with the same name. There
        is technically nothing special that needs to be done, only that the 
        selection of a particular checkbox is muddied by the fact that the 
        "name" attribute, the attribute which we use to select a tag (and
        subsequently set a value), is the same for multiple checkboxes.
    2) RadioInputGroup
        Radio tags have multiple options for a given entry.
    
    Attributes
    ----------
    tag: bs4 tag
        The original html tag that led to the construction of this class.
    name: string or None
        The name attribute of the html tag
    is_hidden: logical
        The 'hidden' attribute of the html tag
    include_in_request : logical
        Whether or not the value should be returned. A value by not be returned
        because:
            - it is a submit button that is not being used
            - it doesn't have a name
            - it is disabled
    is_submit_option: logical
        This indicates that an entry can be used to trigger a submission of the 
        form.
    options_display_str: string
        This string, when presented to the user, should convey to the user
        what options are available. The default, <text input>, implies that
        a user is allowed to input free form text.
        
    """    
    
    def __init__(self,tag):
        #These are default valuse that might be overridden by the more
        #specific class that inherits from this class.
        self.tag = tag
        self.name = tag.get('name',None)
        self.is_hidden = False
        self.include_in_request = True
        self.is_submit_option = False
        
        #This default indicates a non-specific text input. In other words, the 
        #user gets to decide what they want to enter.
        self.options_display_str = "<text input>"    
    
    @property
    def value(self):
        return self.tag.get('value',None)
        
    @value.setter
    def value(self,value):
        self.tag['value'] = value
      
    @encode_if_py2
    def __repr__(self):
        str = u''
        str += '              tag : <bs4 tag>\n'
        str += '              name: %s\n' % self.name
        str += '         is_hidden: %s\n' % self.is_hidden
        str += 'include_in_request: %s\n' % self.include_in_request
        str += '  is_submit_option: %s\n' % self.is_submit_option
        str += '             label: %s\n' % self.label
        #TODO: Incorporate options display str
        
        return str

    def get_final_values(self):
        if self.include_in_request:
            return [(self.name,self.value)]
        else:
            return []
                
    def resolve_label(self):
        #We may eventually want to remove this function
        #Being hidden doesn't mean a label doesn't exist
        #What we really want is lazy evaluation of the label
        if self.is_hidden:
            self.label = ''
        else:
            self.label = resolve_label(self.tag)
          
        #We'll add on a label attribute for finding ...   
        self.tag['label'] = self.label

    @property
    def tag_type_str(self):
        """
        This property is for display purposes from the Form class
        """
        
        tag = self.tag
        type_attribute = tag.get('type',None)
        if type_attribute is None:
            type_string = ''
        else:
            type_string = 'type="%s" ' % type_attribute
        
        return '<%s %s' % (tag.name,type_string)

class SubmitField(SimpleField):
    
    def __init__(self,tag):
        super(SubmitField, self).__init__(tag)
        self.include_in_request = False
        self.is_submit_option = True
        self.options_display_str = ''
    
    @property
    def method(self):
        #The final method if None will be determined by form
        self.tag.get('formmethod',None)
    
    @property
    def action(self):
        self.tag.get('formaction',None)
        
    @property
    def enctype(self):
        self.tag.get('formenctype',None)
        
class Input(SimpleField):
    
    """
    An input tag is one of the form:
    <input ...
    
    This however has many different types which significantly impact the
    behavior of the object. For example an input tag could be a for a user to
    input text or to select a date.
    
    Formal specification:
    http://www.w3.org/TR/html5/forms.html#the-input-element
    
    Nice documentaton of an input tag can be found at:
    http://www.w3schools.com/tags/tag_input.asp
    
    Most Input classes actually inherit from this class, with this class
    providing a factory method for creating those classes.
    
    See Also
    --------
    Field.initialize_field_objects
    
    """

    
    def __init__(self,tag):
        super(Input, self).__init__(tag)

    @staticmethod
    def create(tag):
        tag_type = tag.get('type',None)
        if tag_type is None:
            #The missing default is Text
            #http://www.w3.org/TR/html5/forms.html#attr-input-type
            return TextInput(tag)
        elif tag_type == 'text':
            return TextInput(tag)
        elif tag_type == 'hidden':
            return HiddenInput(tag)
        elif tag_type == 'password':
            return PasswordInput(tag)
        elif tag_type == 'submit':
            return SubmitInput(tag)
        elif tag_type == 'radio':
            return RadioInput(tag)
        elif tag_type == 'checkbox':
            return CheckboxInput(tag)
        elif tag_type == 'button':
            return ButtonInput(tag)
        elif tag_type == 'color':
            return ColorInput(tag)
        elif tag_type == 'date':
            return DateInput(tag)
        elif tag_type == 'datetime':
            return DateTimeInput(tag)
        elif tag_type == 'datetime-local':
            return DateTimeLocalInput(tag)
        elif tag_type == 'email':
            return EmailInput(tag)
        elif tag_type == 'month':
            return MonthInput(tag)
        elif tag_type == 'range':
            return RangeInput(tag)
        elif tag_type == 'search':
            return SearchInput(tag)
        elif tag_type == 'tel':
            return TelInput(tag)
        elif tag_type == 'time':
            return TimeInput(tag)
        elif tag_type == 'url':
            return URLInput(tag)
        elif tag_type == 'week':
            return WeekInput(tag)
        else:
            raise CodeError('Tag type not recognized')

class Button(SubmitField):
    
    """
    http://www.w3.org/TR/html5/forms.html#the-button-element
    
    
    ??? Does type need to be submit to have this be submittable ???
    We'll go with this approach for now.
    
    Real Life Examples
    ------------------
    * https://scholar.google.com/       (See search button)
    * http://www.ncbi.nlm.nih.gov/pubmed/     (See search button)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)
        button_type = self.tag.get('type',None)
        self.is_submit_option = button_type == "submit"

class ButtonInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#button-state-(type=button)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)    
     
class CheckboxInputGroup(Field):
    
    """
    http://www.w3.org/TR/html5/forms.html#checkbox-state-(type=checkbox)
    http://www.w3schools.com/tags/tryit.asp?filename=tryhtml_input_checked
    
    With a checkbox, multiple values can be selected that have the same name.
    Values are submitted separately, e.g. car=Volvo&car=Saab
    
    Attributes
    ----------
    tags : [bs4 objects]
    name : string
        Name of the checkboxes (they are all the same)
    objects : 
    value_options : 
    is_hidden :
    is_submit_option : 
        
    
    Interfacing with this class
    ---------------------------
    1) Set checked via list of checked values
    2) Get an individual object and toggle (NYI)
    
    TODO: Get value based checking the individual checkboxes
    
    """
    def __init__(self,tags):
        self.tags = tags
        self.name = tags[0].get('name')
        self.objects = [CheckboxInput(x) for x in tags]
        self.value_options = [x.value for x in self.objects]
        self.is_hidden = False
        self.is_submit_option = False

        temp = [i for i,x in enumerate(self.objects) if x.is_checked]
        if len(temp) > 0:
            self._value = self.value_options[temp[0]]
        else:
            self._value = None        

        self.options_display_str = self.value_options.__repr__()

    @encode_if_py2
    def __repr__(self):
        #TODO: This needs work ...
    
        str = u''
        str += 'tags: <bs4 tags>\n'
        str += 'objects: <field objects>\n'
        str += 'is_hidden: %s\n' % self.is_hidden
        str += '----Checkboxes----\n'
    
        for i,tag_object in enumerate(self.objects):
            if i < 10: #Let's not show too much ...
                if tag_object.label == '' or tag_object.label is None:
                    label_str = ''
                else:
                    label_str = tag_object.label
                    
                if self._value is not None and self.value_options[i] in self._value:
                    checked = '[x]'
                else:
                    checked = '[ ]'
                    
                str += '%s Value:"%s" (Label:"%s")\n' % (checked,tag_object.value,label_str)
            elif i == 10:
                str += '... and more ...\n'
        
        return str

    @property
    def value(self):
        return self._value          

    @value.setter
    def value(self,value):
        if value is None:
            self._value = None
            return
        
        if not isinstance(value, list):
            value = [value]        
        
        #TODO: make this into a loop with an explicit failure
        
        #This check is verifying 
        if all([value_element in self.value_options for value_element in value]):
            self._value = value
        else:
            ValueError

    def get_final_values(self):
        all_values = []
        for obj in self.objects:
            if obj.is_checked:
                all_values += obj.get_final_values()
        return all_values

    def resolve_label(self):
        self.label = ''      
        for obj in self.objects:
            obj.resolve_label()
            #import pdb
            #pdb.set_trace()

    @property
    def tag_type_str(self):
        return u'<input type="checkbox"'
       
class CheckboxInput(Input):

    """
    
    See Also
    --------
    CheckboxInputGroup
    
    ** The value here currently represents the name that should be used
    when submitting. Whether or not to submit this entry is indicated by
    the "is_checked" status.     
    
    """
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)
        self.is_checked = tag.get('checked') is not None

class ColorInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#color-state-(type=color)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class DateInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#date-state-(type=date)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)
    
class DateTimeInput(Input):
    
    """
    I can't find this on wwww.w3.org
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class DateTimeLocalInput(Input):

    """
    I can't find this on wwww.w3.org
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class EmailInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#e-mail-state-(type=email)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class FileInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#file-upload-state-(type=file)
    """

    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)    
    
class HiddenInput(Input):

    """
    http://www.w3.org/TR/html5/forms.html#hidden-state-(type=hidden)
    """

    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)
        self.is_hidden = True

class ImageInput(SubmitField):
    
    """
    http://www.w3.org/TR/html5/forms.html#image-button-state-(type=image)
    """

    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class MonthInput(Input):

    """
    I can't find this on wwww.w3.org
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class NumberInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#number-state-(type=number)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class PasswordInput(Input):

    """
    http://www.w3.org/TR/html5/forms.html#password-state-(type=password)
    
    <input class="" id="Passwd" name="Passwd" placeholder="Password" type="password"/>
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class RadioInputGroup(Field):
    
    """
    http://www.w3.org/TR/html5/forms.html#radio-button-state-(type=radio)

    http://www.w3schools.com/html/tryit.asp?filename=tryhtml_input_radio

    Notes
    -----
    1) Multiple values are not allowed (TODO: Check for multiple on value set)
    2) No elements checked is allowed
        TODO: test if an unchecked set is submitted ...

    Example:
    --------
    <input type="radio" name="sex" value="male" checked>Male
    <input type="radio" name="sex" value="female">Female

    Attributes:
    -----------
    value : 
        A singular value

    """
    
    def __init__(self,tags):
        self.tags = tags
        self.name = tags[0].get('name')
        self.objects = [RadioInput(x) for x in tags]
        self.value_options = [x.value for x in self.objects]
        self.is_hidden = False        
        self.is_submit_option = False

        temp = [i for i,x in enumerate(self.objects) if x.is_selected]
        if len(temp) > 0:
            self._value = self.value_options[temp[0]]
        else:
            self._value = None

        self.options_display_str = self.value_options.__repr__()

    @encode_if_py2
    def __repr__(self):
        str = u''
        str += 'RadioInputGroup Object:\n'
        str += '     .name: "%s"\n' % self.name
        str += '     .tags: <bs4 tags>\n'
        str += '  .objects: <field objects>\n'
        str += '.is_hidden: %s\n' % self.is_hidden
        str += '----Options----\n'
    
        for i,tag_object in enumerate(self.objects):
            if i < 10: #Let's not show too much ...
                if tag_object.label == '' or tag_object.label is None:
                    label_str = ''
                else:
                    label_str = tag_object.label
                    
                if self._value is not None and self.value_options[i] in self._value:
                    selected = '(x)'
                else:
                    selected = '( )'
                    
                str += '%s Value:"%s" (Label:"%s")\n' % (selected,tag_object.value,label_str)
            elif i == 10:
                str += '... and more ...\n'
                
        return str

    def get_final_values(self):
        #TODO: This could presumably be optimized given that only
        #one value is selected
        #Even here a list comprehension 
        #http://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python
        all_values = []
        for obj in self.objects:
            if obj.is_selected:
                all_values += obj.get_final_values()
        return all_values

    def resolve_label(self):
        self.label = ''      
        for obj in self.objects:
            obj.resolve_label()

    @property
    def value(self):
        return self._value          
            
    @value.setter
    def value(self,value):
        #TODO: Update all objects ...
        if value is None:
            self._value = None
        elif isinstance(value,list):
            raise ValueError('Only a single value may be selected, please input a string')
        elif value in self.value_options:
            self._value = value
        else:
            raise ValueError('Invalid value type')

    @property
    def tag_type_str(self):
        return u'<input type="radio"'
        
        
class RadioInput(Input):

    """    
    See Also
    --------
    RadioInputGroup
    
    """
    
    def __init__(self,tag):
        #TODO: Hold onto parent
        #TODO: Allow value setting but then unset the group
        super(self.__class__, self).__init__(tag)  
        self.is_selected = tag.get('checked') is not None


class RangeInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#range-state-(type=range)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class ResetInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#reset-button-state-(type=reset)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)    

class SearchInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#text-(type=text)-state-and-search-state-(type=search)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class Select(SimpleField):
    """

    Relevant documenation links:
    http://www.w3.org/TR/html5/forms.html#the-option-element
    
    Some Rules
    ----------    
    1) If the 'multiple' attribute is present, then no options may be returned.
        In this case the name is not sent.
    2) If no name is present for select, then it is not submitted.
        This may be a general rule ...
    3) If no value is present for an option, then the text is used
        <option label="saab">My Saab</option>  => 'My Saab' is the 'value'    
   
    
    HTML Example
    ------------    
    <select name="carlist" form="carform" multiple>
        <option value="volvo">Volvo</option>
        <option value="saab">Saab</option>
        <option value="opel">Opel</option>
        <option value="audi" selected>Audi</option>
    </select>
    
    Multiple Return Type
    --------------------
    cars=volvo&cars=saab&cars=audi
    
    """
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)
        self.allow_multiple = self.tag.get('multiple',None) is not None
        option_tags = tag.find_all('option')
        if len(option_tags) == 0:
            self._value = None
            self.value_options = []
            self.label_options = []
            self.text_options = []
        else:
            temp_values = [x.get('value',None) for x in option_tags]
            self.label_options = [x.get('label',None) for x in option_tags]
            #TODO: Do we want to deblank?
            self.text_options = [x.text for x in option_tags]
            #This implements using text if the value attribute is missing
            #TODO: What if the value attribute is empty?
            self.value_options = [x if y is None else y for x,y in zip(self.text_options,temp_values)]
                    
            self._value = [value for value,option_tag in zip(self.value_options,option_tags) if option_tag.get('selected',None) is not None]      
    
        self.options_display_str = self.value_options.__repr__()   
        
    @property
    def value(self):
        #TODO: This needs to be changed ...
        self._value

    @value.setter
    def value(self,value):
        #TODO: We need to check if this is ok ...
        #We can also allow setting based on the label or text ...
        self._value = value

class SubmitInput(SubmitField):
    
    """
    http://www.w3.org/TR/html5/forms.html#submit-button-state-(type=submit)
    
    http://www.w3schools.com/html/tryit.asp?filename=tryhtml_input_submit
    
    HTML Attributes
    ---------------
    formaction
    formenctype
    formmethod
    formnovalidate
    IGNORE formtarget
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)


        

class TextArea(SimpleField):
    
    """
    http://www.w3.org/TR/html5/forms.html#the-textarea-element
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)
        #Carp had: self.value = self._parsed.text.rstrip('\r').rstrip('\n')
        self._value = self.tag.text


    @property
    def value(self):
        return self._value
        
    @value.setter
    def value(self,value):
        #TODO: Need to implement checks ...
        self._value = value
        

class TelInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#telephone-state-(type=tel)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)


class TextInput(Input):

    """
    http://www.w3.org/TR/html5/forms.html#text-(type=text)-state-and-search-state-(type=search)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)  

class TimeInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#time-state-(type=time)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)
    
class URLInput(Input):
    
    """
    http://www.w3.org/TR/html5/forms.html#url-state-(type=url)
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

class WeekInput(Input):

    """
    I can't find this on wwww.w3.org
    """
    
    def __init__(self,tag):
        super(self.__class__, self).__init__(tag)

#TODO:
#Still missing
#datalist, 
#keygen
#   http://www.w3.org/TR/html5/forms.html#the-keygen-element
#   https://bug474958.bugzilla.mozilla.org/attachment.cgi?id=380749

#output, 
#progress, 
#meter, 

#This needs to move
#------------------

def resolve_label(tag):

    """
    
    The goal is     
    
    See: http://www.w3schools.com/tags/tag_label.asp
        
    
    Returns
    -------
    label: string
        If no label is found an empty string is returned    
    
    Labels can be linked either:
    1) via "id" and "for"
    2) by surrounding the tag, e.g. (I think) <label><input></label>
    """
    
    #This is called in the Field factory
    
    #Twitter - placeholder?????
    
    #1) Check aria_label
    #--------------------------------------------    
    aria_label = tag.get('aria-label',None)
    if aria_label is not None:
        return aria_label
        
        
    tag_id = tag.get('id',None)

  

    if tag_id is not None:
        #2) Check within the input tag
        #------------------------------------------
        #   i.e. <input><label></label></input>
        #        
        #Do we need the 'for' if it is inside the input?
        label_tag = tag.find('label',{ "for" : tag_id })
        if label_tag is not None:
            return label_tag.text
        
        #3) Check siblings
        #-------------------------------------------
        #I was having trouble consistently getting a tag for the next sibling 
        #where I could check it's "for" attribute. In retrospect I might not
        #have been properly shortcircuiting on the 'label' test
        #
#        next_sibling = tag.next_sibling
#        if next_sibling is not None:
#            #Get's thrown with Twitter but we are
## getting a bs4.element.NavigableString
#             if w1.name == 'label' and w1.get('for',None) == tag_id
#            import pdb
#            pdb.set_trace()
#            raise CodeError('Case not yet handled')
 
    
             
    #TODO: This could be a potential bottleneck                
    #This is a mess
    #Parents fail

    last_p = None
    for p in tag.parents:
        if p.name is 'label':
            #In this case we are looking for a label that
            #wraps the input
            raise Exception("Case not yet handled")
        if p is not None:
            last_p = p

    label = ''
    if last_p is not None:
        label_tag = last_p.find('label',{ "for" : tag_id })
        
        if label_tag is not None:
            label = label_tag.text  
        
    return label
            


