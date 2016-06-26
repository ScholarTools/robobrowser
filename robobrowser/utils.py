# -*- coding: utf-8 -*-
    
def get_opening_tag_text(tag,attrs_to_include=None):
    
    """
    This returns the text for an opening tag.
    e.g. if the opening tag was <a href="etc">
    This would literally retun that tag string, 
    rather than an "anchor" tag with a "href" attribute
    
    I couldn't find out how to do this throuh Beautifulsoup
    """
    
    if attrs_to_include is None:
        return '<%s %s>' % (tag.name,' '.join(['%s="%s"'%(key,value) for key,value in tag.attrs.items()]))
    else:
        return '<%s %s>' % (tag.name,' '.join(['%s="%s"'%(key,value) for key,value in tag.attrs.items() if key in attrs_to_include]))