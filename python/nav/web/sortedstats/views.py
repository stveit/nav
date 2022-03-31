#
# Copyright (C) 2011 Uninett AS
#
# This file is part of Network Administration Visualized (NAV)
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""Sorted statistics views."""

import logging
import shutil
import requests
import os

from django.shortcuts import render
from django.core.cache import caches
from django.core.files.storage import default_storage
from django.core.files.images import ImageFile
from django.core.files.base import ContentFile
from django.conf import settings

from nav.metrics import CONFIG

from .forms import ViewForm
from . import CLASSMAP

_logger = logging.getLogger(__name__)


def index(request):
    """Sorted stats search & result view"""
    result = None
    line_graph_path = None
    pie_graph_path = None
    if 'view' in request.GET:
        form = ViewForm(request.GET)
        if form.is_valid():
            collector = SortedstatsCollector(
                form.cleaned_data['view'],
                form.cleaned_data['timeframe'],
                form.cleaned_data['rows'],
            )
            collector.collect(form.cleaned_data['use_cache'])
            result = collector.result
            line_graph_path = collector.line_graph_path
            pie_graph_path = collector.pie_graph_path
    else:
        form = ViewForm()

    context = {
        'title': 'Statistics',
        'navpath': [('Home', '/'), ('Statistics', False)],
        'result': result,
        'form': form,
        'graph_path': line_graph_path,
    }
    request.META['SERVER_PORT']

    return render(request, 'sortedstats/sortedstats.html', context)


class SortedstatsCollector:
    _cache = caches['sortedstats']
    result = None
    line_graph_path = None
    pie_graph_path = None

    def __init__(self, view, timeframe, rows):
        self._cache_key = f"{view}_{timeframe}_{rows}"
        self._view = view
        self._timeframe = timeframe
        self._rows = rows

    def collect(self, read_cache):
        if read_cache:
            try:
                cache_blob = self._load_cache()
                result = cache_blob['result']
                line_graph = cache_blob['line_graph']
                pie_graph = cache_blob['pie_graph']
            except LookupError:
                read_cache = False
        if not read_cache:
            result = self._get_result()
            line_graph = self._download_graph(result.graph_url, 'line')
            pie_graph = self._download_graph(result.graph_url, 'pie')
            self._save_cache(result, line_graph, pie_graph)
        if line_graph:
            self.line_graph_path = self._write_graph(line_graph, 'line')
        else:
            self._delete_graph('line')
            self.line_graph_path = None
        if pie_graph:
            self.pie_graph_path = self._write_graph(pie_graph, 'pie')
        else:
            self._delete_graph('pie')
            self.pie_graph_path = None
        self.result = result

    def _save_cache(self, result, line_graph, pie_graph):
        cache_blob = {
            'result': result,
            'line_graph': line_graph,
            'pie_graph': pie_graph,
        }
        self._cache.set(self._cache_key, cache_blob, 600)

    def _load_cache(self):
        cache_blob = self._cache.get(self._cache_key)
        if not cache_blob:
            raise LookupError(
                f"Cache key '{self._cache_key}' not found in cache 'sortedstats'"
            )
        return cache_blob

    def _get_result(self):
        cls = CLASSMAP[self._view]
        result = cls(self._timeframe, self._rows)
        result.collect()
        return result

    def _download_graph(self, graph_url, graph_type):
        format_ = CONFIG.get('graphiteweb', 'format')
        base = CONFIG.get('graphiteweb', 'base')
        stripped_graph_url = graph_url.split("/graphite/")[1]
        url = f"{base}{stripped_graph_url}&format={format_}&tz={settings.TIME_ZONE}&graphType={graph_type}"
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return ContentFile(r.content)

    def _write_graph(self, graph, graph_type):
        graph_name = self._get_graph_name(graph_type)
        self._delete_graph(graph_type)
        default_storage.save(graph_name, graph)
        return self._get_graph_path(graph_type)

    def _delete_graph(self, graph_type):
        graph_name = self._get_graph_name(graph_type)
        if default_storage.exists(graph_name):
            default_storage.delete(graph_name)

    def _get_graph_name(self, graph_type):
        format_ = CONFIG.get('graphiteweb', 'format')
        graph_name = f'sortedstats_graphs/{self._cache_key}_{graph_type}.{format_}'
        return graph_name

    def _get_graph_path(self, graph_type):
        graph_name = self._get_graph_name(graph_type)
        return default_storage.url(graph_name)
