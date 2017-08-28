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


# A site consists of tree of menu items pointing to a site item.
# A site item can be a data selecter: 

site_views = {
    'portfolio-olfactive-map' : {
        'type'  : 'image',
        'descr' : "Portfolio Olfactive Map",
        'image' : "PORTFOLIO OLFACTIVE MAP_FABRIC CLEANING.jpg"},
    'fragrance-passport' : {
        'type'  : 'carousels',
        'descr' : "Fragrance Pasport",
        'carousels' : [
            ("Aragon", ["ARAGON INFORMATION.jpg", "ARAGON PERFORMANCE.jpg", "ARAGON THEME.jpg"]),
            ("Blue Legend", ["BLUE LEGEND INFORMATION.jpg", "BLUE LEGEND PERFORMANCE.jpg", "BLUE LEGEND THEME.jpg"]),
            ]},
    'fabric_conditioners' : {
        'type'  : 'facets_image',
        'descr' : "Fabric Conditioners",
        'facets': ['country', 'brand']},
    'powder_detergents' : {
        'type'  : 'facets_image',
        'descr' : "Powder Detergents",
        'facets': ['country', 'brand']},
    'liquid_detergents' : {
        'type'  : 'facets_image',
        'descr' : "Liquid Detergents",
        'facets': ['country', 'brand']},
    'hedonics_overall' : {
        'type'  : 'charts',
        'descr' : "Hedonics Overall",
        'url'   : '/search_survey?workbook=link&view_name=hedonics_overall',
        'tiles' : [],
        'storyboard': [{'name'  : 'Topline',
                       'layout' : {'rows' : [['topline_liking_table']]},
                       'active' : True,
                       }]},
    'hedonics_per_format' : {
        'type'  : 'charts',
        'descr' : "Hedonics Per Format",
        'url'   : '/search_survey?workbook=link&view_name=hedonics_per_format&age.keyword_tile=on',
        'tiles' : ['age.keyword'],
        'storyboard': [{'name'  : 'Hedonics',
                       'layout' : {'rows' : [['liking_blindcode_col']]},
                       'active' : True,
                       }]},
    'driver_of_liking' : {
        'type'  : 'charts',
        'descr' : "Driver of Liking",
        'charts': ['cand_hedonics_col']},
    'intensity' : {
        'type'  : 'charts',
        'descr' : "Intensiy",
        'charts': ['cand_hedonics_col']},
    'fresh' : {
        'type'  : 'drivers',
        'descr' : "Fresh",
        'drivers': ['freshness', 'method']},
    'superior_fresh' : {
        'type'  : 'drivers',
        'descr' : "Superior Fresh",
        'drivers': ['freshness''method']},
    'clean' : {
        'type'  : 'drivers',
        'descr' : "Clean",
        'drivers': ['cleanness''method']},
    'long_lasting' : {
        'type'  : 'drivers',
        'descr' : "Long Lasting",
        'drivers': ['lastingness''method']},
    'cluster' : {
        'type'  : 'cluster',
        'descr' : "Cluster",
        'drivers': ['lastingness''method']},
    'fresh_sensorial_revitalizing' : {
        'type'  : 'charts',
        'descr' : "Freshness Model Sensorial And Revitalizing",
        'charts': ['sensorial_freshness_bar', 'revitalizing_freshness_bar']},
    'fresh_essential_confident' : {
        'type'  : 'charts',
        'descr' : "Freshness Model Essential And Confident",
        'charts': ['essential_freshness_bar', 'confident_freshness_bar']},
    'newness' : {
        'type'  : 'quadrant',
        'descr' : "Newness Model",
        'quadrants':[('Cult', 'complex/familair'), ('Intrigue', 'complex/unfamilair'),
                     ('Legend','simple/familair'), ('Broad Appeal''simple/unfamilair')],
        'facets': ['uniqueness', 'complexity']},
    'most_often_users' : {
        'type'  : 'top-n',
        'descr' : "Most Often Users",
        'n'     : "8",
        'tile'  : 'format',
        'facets': ['freshness''superior', 'cleanness', 'lastingness']},
    'chart' : {
        'type'  : 'charts',
        'descr' : "Chart",
        'charts': ['ness_line']},
    'summary' : {
        'type'  : 'image',
        'descr' : "Portfolio Olfactive Map",
        'image' : ""},
    'format_total' : {
        'type'  : 'tiled_chart',
        'descr' : "Total",
        'tile'  : 'format',
        'chart' : 'cand_hedonics_col'},
    'format_brand' : {
        'type'  : 'top-n',
        'descr' : "Brand",
        'n'     : "5",
        'tiles' : ['method', 'suitability', 'brand'],
        'facets': ['candidates']},
    'format_split' : {
        'type'  : 'top-n',
        'descr' : "User Split",
        'n'     : "5",
        'tiles' : ['method', 'suitability', 'brand'],
        'facets': ['candidates']},
    'perfume_driven' : {
        'type'  : 'top-n',
        'descr' : "Perfume Driven",
        'n'     : "4",
        'tiles' : ['method', 'suitability', 'brand'],
        'facets': ['candidates']},
    'sensitive_care' : {
        'type'  : 'top-n',
        'descr' : "Sensitive Care",
        'n'     : "4",
        'tiles' : ['method', 'suitability', 'brand'],
        'facets': ['candidates']},
    'functionailty' : {
        'type'  : 'top-n',
        'descr' : "Functionailty",
        'n'     : "4",
        'tiles' : ['method', 'suitability', 'brand'],
        'facets': ['candidates']},
    'extra_benefits' : {
        'type'  : 'top-n',
        'descr' : "Extra_Benefits",
        'n'     : "4",
        'tiles' : ['method', 'suitability', 'brand'],
        'facets': ['candidates']},
    'cross_fabrics' : {
        'type'  : 'metric_chart',
        'descr' : "Cross Fabrics",
        'metrics': ['hedonics', 'freshness', 'cleanness', 'lastingness'],
        'chart' : 'globe_chart'},
    'fabric_conditioner' : {
        'type'  : 'metric_chart',
        'descr' : "Fabric Conditioner",
        'metrics': ['hedonics', 'freshness', 'cleanness', 'lastingness'],
        'chart' : 'globe_chart'},
    'detergents' : {
        'type'  : 'metric_chart',
        'descr' : "Detergents",
        'metrics': ['hedonics', 'freshness', 'cleanness', 'lastingness'],
        'chart' : 'globe_chart'},
    'topline_tables' : {
        'type'  : 'metric_chart',
        'descr' : "Top Line Tables",
        'metrics': ['hedonics', 'freshness', 'cleanness', 'lastingness'],
        'chart' : 'globe_chart'},
    }

menu_items = {
    'Globe' : {
        'type'  : 'data-selector',
        'step'  : ('route_sdm', 'country_sel')
        },
    'Gender' : {
        'type'  : 'data-selector',
        'step'  : ('route_sdm', 'gender_sel')
        },
    'Fragrance Passport' : {
        'type'  : 'view-selector',
        'views' : ['portfolio-olfactive-map', 'fragrance-passport'],
        'style' :  "background-image: url('/static/app/media/link/correlation.jpg'); background-size: cover;"},
    'Washing Habits' : {
        'type'  : 'wip'},
    'Performance' : {
        'type'  : 'wip'},
    'Brands' : {
        'type'  : 'view-selector',
        'views' : ['fabric_conditioners', 'powder_detergents', 'liquid_detergents'],
        'style' :  "background-image: url('/static/app/media/link/correlation.jpg'); background-size: cover;"},
    'Liking' : {
        'type'  : 'view-selector',
        'views' : ['hedonics_overall', 'hedonics_per_format', 'intensity', 'driver_of_liking'],
        'style' :  "background-image: url('/static/app/media/link/likingbg.jpg'); background-size: cover;"},
    'Freshness' : {
        'type'  : 'view-selector',
        'views' : ['fresh', 'superior_fresh', 'clean', 'long_lasting', 'cluster',
                   'fresh_sensorial_revitalizing', 'fresh_essential_confident',
                   'newness', 'most_often_users', 'chart', 'summary']},
    'Format Suitability' : {
        'type'  : 'view-selector',
        'views' : ['format_total', 'format_brand', 'format_split']},
    'Benefits' : {
        'type'  : 'view-selector',
        'views' : ['perfume_driven', 'sensitive_care', 'functionailty', 'extra benefits']},
    'Correlation' : {
        'type'  : 'view-selector',
        'views' : ['cross_fabrics', 'fabric_conditioner', 'detergents']},
    'Top Line Tables' : {
        'type'  : 'site_view',
        'view'  : 'topline_tables'},
    }

link_menu = {
    'menu'  : ['Globe', 'Gender', 'Fragrance Passport', 'Washing Habits', 'Performance', 'Brands', 'Liking',
               'Freshness', 'Format Suitability', 'Benefits', 'Correlation', 'Top Line Tables'],
    'menu_items'    : menu_items
    }


sites = {
    'Link' : {
        'type'  : 'site',
        'descr' : 'LiNK',
        'site_menu': link_menu
        }
    }

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
        'selection' : ('graph', storyboard['country_sel'], charts),
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
            'Fresh and Clean'   : 'fresh_and_clean_profile_dest',
            'Orange Beverages'  : 'orange_bevarages_profile_dest',
            'SE Studies'        : 'studies_profile_dest',
            'SDM'               : 'SDM_storyboard_dest'}
        },
    'fresh_and_clean_profile_dest'   : {
        'type'      : 'destination',
        'url'       : '/search_survey?workbook=fresh+and+clean&survey.keyword=fresh+and+clean',
        'seeker'    : 'SurveySeekerView',
        'tab'       : 'storyboard',
        'dashboard' : 'profile',
        },
    'orange_bevarages_profile_dest'   : {
        'type'      : 'destination',
        'url'       : '/search_survey?workbook=orange+beverages&survey.keyword=orange+beverages',
        'seeker'    : 'SurveySeekerView',
        'tab'       : 'storyboard',
        'dashboard' : 'profile',
        },
    'studies_profile_dest'   : {
        'type'      : 'destination',
        'url'       : '/search_studies',
        'seeker'    : 'StudiesSeekerView',
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
    'route_ci_fresh' : ('SurveySeekerView',
                   ['fresh_and_clean_profile_dest']),
    'route_ci_oranges' : ('SurveySeekerView',
                   ['orange_bevarages_profile_dest']),
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
            dashboard_layout = step['selection'][1]['layout']
            for key, map in dashboard_layout.items():
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


# prepare the data for the selected menu for the site
def site_menu(request, site_name, menu_name, view_name):
    results = {}
    facets = {}
    site = sites[site_name]
    site_menu = site['site_menu']
    menu_items = site_menu['menu_items']
    for name, item in menu_items.items():
        menu_item = menu_items[name]
        if menu_item['type'] == 'data-selector':
            route_name = menu_item['step'][0];
            step_name = menu_item['step'][1];
            results, facets = route_step(request, route_name, step_name);
        elif menu_item['type'] == 'view-selector':
            if view_name != '':
                pass
        elif menu_item['type'] == 'site-view':
            pass
        else:
            pass

    return results, facets

