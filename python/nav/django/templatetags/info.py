"""Template tags used in info subsystem"""
import time
from django import template
from datetime import datetime, timedelta
from django.utils.timesince import timesince

register = template.Library()

@register.filter
def time_since(timestamp):
    """Convert a timestamp to human readable time since"""

    mapping = {'minute': 'min',
               'hour': 'hr',
               'week': 'wk',
               'month': 'mo',
               'year': 'yr'}

    if timestamp is None:
        return "Never"

    if timestamp == datetime.max or timesince(timestamp) == "0 minutes":
        return "Now"
    else:
        text = timesince(timestamp)
        for key in mapping.keys():
            text = text.replace(key, mapping[key])

        return text


@register.filter
def days_since(timestamp):
    """Convert a timestamp to human readable time using days"""
    if timestamp is None:
        return "Never"

    if timestamp == datetime.max or timesince(timestamp) == "0 minutes":
        return "Now"
    elif timestamp.date() == datetime.now().date():
        return "Today"
    elif timestamp.date() == datetime.now().date() - timedelta(days=1):
        return "Yesterday"
    else:
        return "%s days" % (datetime.now().date() - timestamp.date()).days


@register.filter
def is_max_timestamp(timestamp):
    """Check if timestamp is max"""
    if timestamp == datetime.max:
        return True
    else:
        return False


@register.filter
def run(function, arg):
    """Run a function with given argument"""
    return function(arg)


@register.filter
def lookup(value, key):
    """Lookup key in a dictionary"""
    return value.get(key, value)


@register.filter
def interval(value):
    """Create a human readable interval

    Arguments:
    value -- a number of seconds

    """
    return time.strftime('%H:%M:%S', time.gmtime(value))


@register.filter
def add_interval(value, interval):
    """Create a new timestamp based on value and interval

    Arguments:
    value -- a datetime object
    interval -- interval in seconds

    """
    return value + timedelta(seconds=interval)
