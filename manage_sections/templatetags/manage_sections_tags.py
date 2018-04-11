from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(is_safe=True)
@stringfilter
def to_letter_range(name, args):
    """
    Return the letter range for a given string where the range is given as a comma separated string.  For
    example, passing 'Doe, John' to the filter with arguments of 'A-C,D-F,G-Z' would return
    'D-F'.  Ranges can either be in the form 'A-D' or can be single letters like 'S'.
    """
    try:
        ord_val = ord(name[0].upper())
        letter_ranges = [arg.strip().upper() for arg in args.split(',')]
        for letter_range in letter_ranges:
            range_len = len(letter_range)
            if ord(letter_range[0]) <= ord_val <= ord(letter_range[range_len - 1]):
                return letter_range
    except IndexError:
        # Either the name passed in was empty, or one of the ranges was passed in as an empty string, so
        # just return an empty string in this case.
        return ''


@register.filter
def list_comp(lst):
    """
    Build a list comprehension by iterating over the GroupedResult list
    """
    comp = [x[0] for x in lst]
    return comp


@register.filter(is_safe=True)
def enrollment_lname(enrollment):
    try:
        lname_first = enrollment['user']['sortable_name']
    except KeyError:
        return ''
    return lname_first.split(',')[0]

