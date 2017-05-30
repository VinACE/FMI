from datetime import datetime
from datetime import time
from datetime import timedelta
import re
from pandas import Series, DataFrame
import pandas as pd
import collections

import seeker
import seeker.models
import elasticsearch_dsl as dsl

import app.models as models
import app.survey as survey


# A guide consists of routes and a route consists of steps. A route leads to the destination.
# A step is selection or decision that has to be made to lead to the end resulst.


charts = {
    "country_map" : {
        'chart_type'  : "GeoChart",
        #'chart_data'  : 'aggr',
        'chart_data'  : 'facet',
        'chart_title' : "Country Resp Count",
        'listener'    : {'select' : {'select_event': 'country.keyword'}},
        'X_facet'     : {
            'field'   : "country.keyword",
            'total'   : True,
            'label'   : "Country" },
        },
    }

dashboard_country = {
    'rows' : [['country_map']]
    }

storyboard = {
    'country_sel' : {
        'layout'    : dashboard_country,
        'active'    : True,
        },
    }

country2geochart = {
    'UK'    : 'GB',
    'USA'   : 'United States'
    }

gender_gallery = [
    ('Female', '/static/app/media/female.jpg'),
    ('Male', '/static/app/media/male.jpg'),
    ]


dataset_gallery = [
    ('CI Survey', '/static/app/media/CI2.jpg'),
    ('SE Studies', '/static/app/media/CFT_CI.jpg'),
    ('SDM', '/static/app/media/SDM.jpg'),
    ]

steps = {
    'country_sel' : {
        'type'      : 'selection',
        'facet'     : 'country.keyword',
        'selection' : ('graph', 'country_sel'),
        'selsize'   : '0-n',
        },
    'gender_sel' : {
        'type'      : 'selection',
        'facet'     : 'gender.keyword',
        'selection' : ('gallery', gender_gallery),
        'selsize'   : '0-1',
        },
    'age_sel' : {
        'type'      : 'selection',
        'facet'     : 'age.keyword',
        'selection' : ('facet', 'terms'),
        'selsize'   : '0-1',
        },
    'dataset_dec' : {
        'type'      : 'decision',
        'select'    : 'dataset_dec',
        'selection' : ('gallery', dataset_gallery),
        'selsize'   : '1',
        'decisionstep' : {
            'CI Survey' : 'survey_profile_dest', 'SE Studies': 'studies_profile_dest', 'SDM' : 'SDM_storyboard_dest'}
        },
    'studies_profile_dest'   : {
        'type'      : 'destination',
        'url'       : '/search_studies',
        'seeker'    : 'StudiesSeekerView',
        'tab'       : 'storyboard',
        'dashboard' : 'profile',
        },
    'survey_profile_dest'   : {
        'type'      : 'destination',
        'url'       : '/search_survey',
        'seeker'    : 'SurveySeekerView',
        'tab'       : 'storyboard',
        'dashboard' : 'profile',
        },
    'SDM_storyboard_dest'   : {
        'type'      : 'destination',
        'url'       : '/search_survey',
        'seeker'    : 'SurveySeekerView',
        'tab'       : 'AJAX',
        'dashboard' : 'profile',
        },
    }

routes = {
    'route_sdm' : ('SurveySeekerView',
                  ['country_sel', 'gender_sel', 'age_sel', 'dataset_dec']),
    'route_ci' : ('SurveySeekerView',
                   ['survey_profile_dest']),
    }

route2seeker = {
    'route_ci'  : models.SurveySeekerView,
    'route_sdm' : models.SurveySeekerView,
    'SurveySeekerView' : models.SurveySeekerView,
    'StudiesSeekerView' : models.StudiesSeekerView,
    }

guide = {
    'routes'        : routes,
    'steps'         : steps,
    'storyboard'    : storyboard,
    }

def country_map_geochart(country):
    global country2geochart

    if country in country2geochart:
        geo_country = country2geochart[country]
    else:
        geo_country = country
    return geo_country


def step_filter(search, facets, step):
    facet_field = step['facet']
    for facet in facets:
        if facet.field == facet_field:
            break
    values = facets[facet]
    search = facet.filter(search, values)
    return search

def step_aggr(search, facets, step):
    facet_field = step['facet']
    for facet in facets:
        if facet.field == facet_field:
            break
    aggr_stack = {}
    search = facet.apply(search, facet.name, aggr_stack)
    return search

# prepare the data for the selected route
def route_step(request, route_name, step_name):
    route = routes[route_name]
    route_steps = route[1]
    seekerview = route2seeker[route_name]()
    seekerview.request = request
    facets = seekerview.get_facet_data()
    using = seekerview.using
    index = seekerview.index
    search = seekerview.document.search().index(index).using(using).extra(track_scores=True)

    stepnr = 0;
    while step_name != route_steps[stepnr] and stepnr < len(route_steps):
        step = steps[route_steps[stepnr]]
        if step['type'] == 'selection':
            search = step_filter(search, facets, step)
            search = step_aggr(search, facets, step)
        stepnr = stepnr + 1

    results = {}
    step = steps[step_name]
    if step['type'] == 'selection':
        search = step_aggr(search, facets, step)
        results = search.execute(ignore_cache=True)
        route_charts = {}
        if step['selection'][0] == 'graph':
            storyboard_name = step['selection'][1]
            dashboard = storyboard[storyboard_name]['layout']
            for key, map in dashboard.items():
                for row in map:
                    for chart_name in row:
                        chart = charts[chart_name]
                        route_charts[chart_name] = seeker.dashboard.Chart(chart_name, charts, None)
                        chart_data = chart['chart_data']
                        if chart_data == 'facet':
                            route_charts[chart_name].bind_facet(results.aggregations)
                        if chart_data == 'aggr':
                            route_charts[chart_name].bind_aggr(results.aggregations)
                        if chart['chart_type'] == 'GeoChart':
                            for row in chart['data']:
                                row[0] = country_map_geochart(row[0])
    if step['type'] == 'decision':
        results = search.execute(ignore_cache=True)
    if step['type'] == 'destination':
        results = search.execute(ignore_cache=True)

    for facet in list(facets):
        stepix = 0;
        found = False
        while stepix <= stepnr and stepix < len(route_steps):
            step = steps[route_steps[stepix]]
            if step['type'] == 'selection':
                if step['facet'] == facet.field:
                    found = True
            stepix = stepix + 1
        if not found :
            del facets[facet]

    return results, facets

# destination reached
def route_dest(request, route_name, step_name):
    route = routes[route_name]
    route_steps = route[1]
    step = steps[step_name]
    if step['type'] == 'decision':
        decision = request.GET[step_name]
        dest_step_name = step['decisionstep'][decision]
        step_name = dest_step_name
    return step_name



