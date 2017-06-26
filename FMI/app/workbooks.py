"""
Definition of models.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.views.generic.base import TemplateView

# Create your models here.
import queue
import collections
import datetime
import FMI.settings
from pandas import DataFrame

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl import DocType, Date, Double, Long, Integer, Boolean
from elasticsearch_dsl.connections import connections
import seeker

from django.utils.encoding import python_2_unicode_compatible

# A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
# in the template this is translated into HTML tables, rows, cells and div elements  


class PostWorkbook:
    # A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
    # in the template this is translated into HTML tables, rows, cells and div elements
    dashboard = {
        'category_keyword_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Category / Keyword Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "post_category_id.keyword",
                'label'   : "Category" },
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "subject_keyword_table" : {
            'chart_type': "Table",
            'chart_title' : "Subject / Keyword Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "subject.keyword",
                'label'   : "Subject" },
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "facet_keyword_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Keyword Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "facet_cust_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Customers Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_cust",
                'label'   : "Customers" },
            },
        "facet_comp_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Competitors Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_comp",
                'label'   : "Competitors" },
            },
        "published_keyword_line" : {
            'chart_type'  : "LineChart",
            'chart_title' : "Published Month Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "published_date",
                'label'   : "Published",
                'key'     : 'key_as_string',
                'total'   : False},
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        }

    dashboard_layout = collections.OrderedDict()
    dashboard_layout['rows1'] = [["published_keyword_line"]]
    dashboard_layout['rows2'] = [["facet_keyword_pie", "facet_cust_pie", "facet_comp_pie"]]
    dashboard_layout['rows3'] = [["category_keyword_table", "subject_keyword_table"]]

    storyboard = [
        {'name' : 'initial',
         'layout'   : dashboard_layout,
         'active'   : True,
         }
    ] 

    workbooks = {
        "initial" : {
            'charts'        : dashboard,
            'storyboard'    : storyboard,
            }
        }

class ScentemotionWorkbook:

    dashboard = {
        'region_olfactive_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Region / Olfactive Ingr Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "region.keyword",
                'label'   : "Region" },
            'Y_facet'     : {
                'field'   : "olfactive.keyword",
                'label'   : "Olfactive" },
            },
        "olfactive_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Olfactive Ingr Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "olfactive.keyword",
                'label'   : "Olfactive" },
            },
        "olfactive_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Olfactive Ingr Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "olfactive.keyword",
                'label'   : "Olfactive" },
            },
        "cand_mood_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Mood Top Candidates",
            'chart_data'  : "hits",
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "mood",
                'question': "Mood",
                "answers" : ["Happy","Relaxed"],
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Mood"
                },
            'options'     : {
                "seriesType" : 'bars',
                "series"  : {2: {"type": 'line'}, 3: {"type": 'line'}}
                },
            },
        "cand_smell_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Smell Top Candidates",
            'chart_data'  : "hits",
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "smell",
                'question': "Smell",
                "answers" : ["Clean","Natural"],
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Mood"
                },
            'options'     : {
                "seriesType" : 'bars',
                "series"  : {2: {"type": 'line'}, 3: {"type": 'line'}}
                },
            },
        "cand_intensity_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Intensity Top Candidates",
            'chart_data'  : "hits",
            'controls'    : ['CategoryFilter', 'NumberRangeFilter'],
            'help'        : "Select Row for sorting, Select Column Header for filter",
            'listener'    : {'select' : {'colsort': None, 'rowcolfilter': ["mood_cand_radar", "smell_cand_radar", "negative_cand_radar", "descriptor_cand_radar"]}},
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "intensity",
                "q-mean"  : True,
                'label'   : "Intensity" },
            'options'     : {
                "seriesType" : 'bars',
                "series"  : {1: {"type": 'line'}, 2: {"type": 'line'}}
                },
            },
        "mood_cand_radar" : {
            'chart_type'  : "RadarChart",
            'chart_title' : "Mood",
            'chart_data'  : "hits",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "mood",
                'question': "Mood",
                "answers" : [], # All
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Mood"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "smell_cand_radar" : {
            'chart_type'  : "RadarChart",
            'chart_title' : "Smell",
            'chart_data'  : "hits",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "smell",
                'question': "Smell",
                "answers" : [], # All
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Smell"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "negative_cand_radar" : {
            'chart_type'  : "RadarChart",
            'chart_title' : "Negative",
            'chart_data'  : "hits",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "negative",
                'question': "Negative",
                "answers" : [], # All
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Negative"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "descriptor_cand_radar" : {
            'chart_type'  : "RadarChart",
            'chart_title' : "Descriptor",
            'chart_data'  : "hits",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "descriptor",
                'question': "Descriptor",
                "answers" : [], # All
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Descriptor"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        }
    dashboard_olfactive = collections.OrderedDict()
    dashboard_olfactive['rows'] = [["region_olfactive_table"], ["olfactive_pie", "olfactive_col"]]

    dashboard_candidates = collections.OrderedDict()
    dashboard_candidates['rows'] = [["cand_mood_col"],["cand_smell_col"],["cand_intensity_col"]]

    dashboard_profile = collections.OrderedDict()
    dashboard_profile['columns'] = [["cand_intensity_col"], ["mood_cand_radar", "smell_cand_radar"], ["negative_cand_radar", "descriptor_cand_radar"]]

    storyboard = [
        {'name' : 'Olfactive',
         'layout'   : dashboard_olfactive,
         'active'   : False,
         },
        {'name' : 'Candidates',
         'layout'   : dashboard_candidates,
         'active'   : True,
         },
        {'name' : 'Profile',
         'layout'   : dashboard_profile,
         'active'   : False,
         },
    ]

    workbooks = {
        "initial" : {
            'charts'        : dashboard,
            'storyboard'    : storyboard,
            }
        }


class StudiesWorkbook:

    # A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
    # in the template this is translated into HTML tables, rows, cells and div elements
    dashboard = {
        #'region_olfactive_table' : {
        #    'chart_type'  : "Table",
        #    'chart_title' : "Region / Olfactive Ingr Count",
        #    'chart_data'  : "facet",
        #    'X_facet'     : {
        #        'field'   : "region.keyword",
        #        'label'   : "Region" },
        #    'Y_facet'     : {
        #        'field'   : "olfactive.keyword",
        #        'label'   : "Olfactive" },
        #    },
        #"olfactive_pie" : {
        #    'chart_type': "PieChart",
        #    'chart_title' : "Olfactive Ingr Count",
        #    'chart_data'  : "facet",
        #    'X_facet'     : {
        #        'field'   : "olfactive.keyword",
        #        'label'   : "Olfactive" },
        #    },
        #"olfactive_col" : {
        #    'chart_type': "ColumnChart",
        #    'chart_title' : "Olfactive Ingr Count",
        #    'chart_data'  : "facet",
        #    'X_facet'     : {
        #        'field'   : "olfactive.keyword",
        #        'label'   : "Olfactive" },
        #    },
        "cand_emotion_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Emotion Top Candidates",
            'chart_data'  : "hits",
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "emotion",
                'question': "Emotion",
                "answers" : ["Addictive","Classic", "Cheap"],
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Emotion"
                },
            'options'     : {
            #      #title   : 'Monthly Coffee Production by Country',
            #      #vAxis   : {title: 'Cups'},
            #      #hAxis   : {title: 'Month'},
                "seriesType" : 'bars',
                "series"  : {3: {"type": 'line'}, 4: {"type": 'line'}}
                },
            },
        "cand_freshness_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Freshness Top Candidates",
            'chart_data'  : "hits",
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "freshness",
                "metric"  : "prc",
                "q-mean"  : True,
                'label'   : "Freshness" },
            'options'     : {
                "seriesType" : 'bars',
                "series"  : {1: {"type": 'line'}, 2: {"type": 'line'}}
                },
            },
        "cand_hedonics_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Hedonics Top Candidates",
            'chart_data'  : "hits",
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "hedonics",
                'question': "Hedonics",
                'metric'  : "prc",
                "q-mean"  : True,
                'label'   : "Hedonics"
                },
            'options'     : {
                "seriesType" : 'bars',
                "series"  : {1: {"type": 'line'}, 2: {"type": 'line'}}
                },
            },
        "hedonics_cand_table" : {
            'chart_type': "Table",
            'chart_title' : "Topline",
            'chart_data'  : "topline",
            'controls'    : [],
            'help'        : "Select Row for sorting, Select Column Header for filter",
            'listener'    : {'sort' : ["suitable_stage_cand_bar", "suitable_stage_cand_radar"], 'select' : {'rowsort': None}},
            'X_facet'     : {
                'fields'  : {
                    "hedonics" : {
                            'lines'   : {"liking.keyword" : {'0-Mean':['mean'], '1-Excellent':[7], '2-Top2':[7,6], '3-Bottom2':[2,1]}},
                        },
                    },
                },
            'Y_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'options'     : {
                'sort'    : 'event',
                "allowHtml" : True,
                'frozenColumns' : 2,
                },
            #'formatter'  : {
            #    'NumberFormat' : {},
            #    'setColumnProperties'   : {},
            #    'setProperty'   : [],
            #    },
            },
        "suitable_stage_cand_bar" : {
            'chart_type': "BarChart",
            'chart_title' : "Suitable Stage",
            'chart_data'  : "hits",
            'transpose'   : True,
            'controls'    : ['CategoryFilter'],
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "suitable_stage",
                'question': "Stage",
                "answers" : [], # All
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Stage"
                },
            },
        "suitable_stage_cand_radar" : {
            'chart_type': "RadarChart",
            'chart_title' : "Suitable Stage",
            'chart_data'  : "hits",
            'transpose'   : True,
            'controls'    : ['CategoryFilter'],
            'X_facet'     : {
                'field'   : "IPC",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "suitable_stage",
                'question': "Stage",
                "answers" : [], # All
                "metric"  : "prc",
                "a-mean"  : True,
                'label'   : "Stage"
                },
            },
        }
    dashboard_olfactive = collections.OrderedDict()
    dashboard_olfactive['rows'] = [["region_olfactive_table"], ["olfactive_pie", "olfactive_col"]]

    dashboard_candidates = collections.OrderedDict()
    dashboard_candidates['rows'] = [["cand_emotion_col"],["cand_freshness_col"],["cand_hedonics_col"]]

    dashboard_profile = collections.OrderedDict()
    dashboard_profile['columns'] = [["hedonics_cand_table"], ["suitable_stage_cand_bar"],["suitable_stage_cand_radar"]]

    storyboard = [
        {'name' : 'Candidates',
         'layout'   : dashboard_candidates,
         'active'   : True,
         },
        {'name' : 'Profile',
         'layout'   : dashboard_profile,
         'active'   : False,
         },
        #{'name' : 'Olfactive',
        # 'layout'   : dashboard_olfactive,
        # 'active'   : False,
        # },
    ]

    workbooks = {
        "initial" : {
            'charts'        : dashboard,
            'storyboard'    : storyboard,
            }
        }

class SurveyWorkbook:

    dashboard_fresh = {
        #"liking_col" : {
        #    'chart_type': "Table",
        #    'chart_title' : "Liking/Hedonics Blindcode Count",
        #    'chart_data'  : "facet",
        #    'X_facet'     : {
        #        'field'   : "liking.keyword",
        #        'label'   : "Liking/Hedonics" },
        #    },
        "cand_emotion_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Candidates / Emotion",
            'chart_data'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "emotion",
                'question': "Emotion",
                "answers" : ["Addictive","Classic"],
                "values"  : ["Yes"],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Emotion"
                },
            'options'     : {
            #      #title   : 'Monthly Coffee Production by Country',
            #      #vAxis   : {title: 'Cups'},
            #      #hAxis   : {title: 'Month'},
                "seriesType" : 'bars',
                "series"  : {2: {"type": 'line'}, 3: {"type": 'line'}}
                },
            },
        "liking_blindcode_col" : {
            'chart_type': "Table",
            'chart_title' : "Liking/Hedonics Candidate Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Liking/Hedonics",
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate" },
            },
        "topline_liking_table" : {
            'chart_type'  : "Table",
            'chart_title' : "Topline Liking - Candidate",
            'chart_data'  : "topline_base",
            'base'        : "liking_blindcode_col",
            'controls'    : ['CategoryFilter'],
            'help'        : "Select Row for sorting, Select Column Header for filter",
            'listener'    : {'sort' : ["cand_emotion_col", "cand_concept_radar", "cand_emotion_radar", "cand_mood_radar"], 'select' : {'rowsort': None}},
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Hedonics_",
                'lines'   : {"liking.keyword" : {'0-Mean':['mean'], '1-Excellent':[7], '2-Top2':[7,6], '3-Bottom2':[2,1]}},
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate"
                },
            'options'     : {
                'sort'    : 'event',
                "allowHtml" : True,
                'frozenColumns' : 2,
                },
            'formatter'  : {
                #'NumberFormat' : {1 : {'pattern' : '#.##'},2 : {'pattern' : '#.#'}},
                #'setColumnProperties'   : {1 : {'style': 'font-style:bold; font-size:22px;'}},
                'setProperty'   : [],
                #'setProperty'   : [[2, 1, 'style', 'font-style:bold;'],
                #                   [3, 3, 'background-color', 'red' ],
                #                   [0, 1, 'className', 'benchmark'],
                #                   [1, 1, 'className', 'benchmark'],
                #                   [2, 1, 'className', 'benchmark'],
                #                   [3, 1, 'className', 'benchmark'],
                #                   [4, 1, 'className', 'benchmark'],
                #                   ],
                },
            },
        "freshness_blindcode_col" : {
            'chart_type': "Table",
            'chart_title' : "Freshness Candidate Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "freshness",
                'label'   : "Freshness" },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate" },
            },
        "topline_freshness_table" : {
            'chart_type'  : "Table",
            'chart_title' : "Topline Liking - Candidate",
            'chart_data'  : "topline_base",
            'base'        : "freshness_blindcode_col",
            'controls'    : ['CategoryFilter'],
            'listener'    : {'select' : {'rowsort': None}},
            'X_facet'     : {
                'field'   : "freshness",
                'label'   : "Freshness",
                'lines'   : {"freshness" : {'0-Mean':['mean'], '1-Excellent':[7], '2-Top2':[7,6], '3-Bottom2':[2,1]}},
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate"
                },
            'options'     : {
                "allowHtml" : True,
                'frozenColumns' : 2,
                },
            'formatter'  : {
                'setProperty'   : [],
                },
            },
        "cleanliness_blindcode_col" : {
            'chart_type': "Table",
            'chart_title' : "Cleanliness Candidate Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "cleanliness",
                'label'   : "Cleanliness" },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate" },
            },
        "suitable_stage_ans_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Suitable Stage Resp Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "suitable_stage",
                'total'   : False,
                'label'   : "Suitable Stage" },
            'Y_facet'     : {
                'field'   : "answer",
                "axis"    : 0,
                'label'   : "Answer" },
            },
        "suitable_product_ans_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Suitable Product Resp Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "suitable_product",
                'total'   : False,
                'label'   : "Suitable Product" },
            'Y_facet'     : {
                'field'   : "answer",
                "axis"    : 0,
                'label'   : "Answer" },
            },
        "emotion_ans_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Emotion Resp Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "emotion",
                'total'   : False,
                'label'   : "Emotion" },
            'Y_facet'     : {
                'field'   : "answer",
                "axis"    : 0,
                'label'   : "Answer" },
            },
        #"country_map" : {
        #    'chart_type': "GeoMap",
        #    'chart_title' : "Country Resp Count",
        #    'X_facet'     : {
        #        'field'   : "country.keyword",
        #        'total'   : True,
        #        'label'   : "Country" },
        #    },
        "cand_concept_radar" : {
            'chart_type': "RadarChart",
            'chart_title' : "Concept",
            'chart_data'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "concept",
                'question': "Concept",
                "answers" : [],
                "values"  : ["Yes"],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Concept"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "cand_emotion_radar" : {
            'chart_type': "RadarChart",
            'chart_title' : "Emotion",
            'chart_data'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "emotion",
                'question': "Emotion",
                "answers" : [],
                "values"  : ["Yes"],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Emotion"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "cand_mood_radar" : {
            'chart_type'  : "RadarChart",
            'chart_title' : "Mood",
            'chart_data'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "mood",
                'question': "Mood",
                "answers" : [],
                "values"  : ["Yes"],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Mood"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "topline_liking_combo" : {
            'chart_type'  : "ComboChart",
            'chart_title' : "Topline Liking - Candidate",
            'chart_data'  : "topline_base",
            'base'        : "liking_blindcode_col",
            'controls'    : ['CategoryFilter'],
            'help'        : "Select Row for sorting, Select Column Header for filter",
            'listener'    : {'sort' : ["cand_emotion_col", "cand_concept_radar", "cand_emotion_radar", "cand_mood_radar"], 'select' : {'rowsort': None}},
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Hedonics_",
                'lines'   : {"liking.keyword" : {'0-Mean':['mean']}},
                "q-mean"  : True,
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate"
                },
            'options'     : {
                'sort'    : 'event',
                'legend'  : {'position': 'none'},
                "seriesType" : 'bars',
                "series"  : {1: {"type": 'line'}}
                },
            },
        } 


    dashboard_fresh_layout = collections.OrderedDict()
    dashboard_fresh_layout['rows'] = [["emotion_ans_col"],["suitable_stage_ans_col", "suitable_product_ans_col"]]

    dashboard_fresh_hedonics = collections.OrderedDict()
    dashboard_fresh_hedonics['rows'] = [["liking_blindcode_col"],["freshness_blindcode_col"], ["cleanliness_blindcode_col"]]

    dashboard_fresh_topline = collections.OrderedDict()
    dashboard_fresh_topline['rows'] = [["topline_liking_table"],["topline_freshness_table"],["cand_emotion_col"]]

    dashboard_fresh_profile = collections.OrderedDict()
    dashboard_fresh_profile['columns'] = [["topline_liking_table"],["topline_liking_combo"],["cand_concept_radar", "cand_emotion_radar"],["cand_mood_radar"]]


    storyboard_fresh = [
        {'name'     : "Topline",
         'layout'   : dashboard_fresh_topline,
         'active'   : True,
        },
        {'name'     : "Hedonics / Candidates",
         'layout'   : dashboard_fresh_hedonics,
         'active'   : False,
        },
        {'name'     : "Profile",
         'layout'   : dashboard_fresh_profile,
         'active'   : False,
        },
        {'name'     : "Questions / Answers",
         'layout'   : dashboard_fresh_layout,
         'active'   : False,
        },
        #{'name'     : "Candidates / Hedonics",
        # 'layout'   : dashboard_candidates,
        # 'active'   : True,
        #},
        ]

    dashboard_orange = {
        "liking_blindcode_col" : {
            'chart_type': "Table",
            'chart_title' : "Liking/Hedonics Candidate Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Liking/Hedonics",
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate" },
            },
        "strength_blindcode_col" : {
            'chart_type': "Table",
            'chart_title' : "Strength Candidate Count",
            'chart_data'  : "aggr",
            'X_facet'     : {
                'field'   : "hedonics",
                'question': "Strength",
                "answers" : ["strength"],
                "values"  : [],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Strength"
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate" },
            },
        "topline_liking_table" : {
            'chart_type'  : "Table",
            'chart_title' : "Topline Liking - Candidate",
            'chart_data'  : "topline_base",
            'base'        : "liking_blindcode_col",
            'controls'    : ['CategoryFilter'],
            'help'        : "Select Row for sorting, Select Column Header for filter",
            'listener'    : {'sort' : ["cand_affective_radar", "cand_behavioral_radar", "cand_ballot_radar", "cand_descriptors_radar"], 'select' : {'rowsort': None}},
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Hedonics_",
                'lines'   : {"liking.keyword" : {'0-Mean':['mean'], '1-Excellent':[9], '2-Top2':[9,8], '3-Top3':[9,8,7], '4-Bottom3':[3,2,1],'5-Bottom2':[2,1]}},
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate"
                },
            'options'     : {
                'sort'    : 'event',
                "allowHtml" : True,
                'frozenColumns' : 2,
                },
            'formatter'  : {
                #'NumberFormat' : {1 : {'pattern' : '#.##'},2 : {'pattern' : '#.#'}},
                #'setColumnProperties'   : {1 : {'style': 'font-style:bold; font-size:22px;'}},
                'setProperty'   : [],
                #'setProperty'   : [[2, 1, 'style', 'font-style:bold;'],
                #                   [3, 3, 'background-color', 'red' ],
                #                   [0, 1, 'className', 'benchmark'],
                #                   [1, 1, 'className', 'benchmark'],
                #                   [2, 1, 'className', 'benchmark'],
                #                   [3, 1, 'className', 'benchmark'],
                #                   [4, 1, 'className', 'benchmark'],
                #                   ],
                },
            },
        "cand_affective_radar" : {
            'chart_type': "RadarChart",
            'chart_title' : "Affective",
            'chart_data'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "affective",
                'question': "Affective",
                "answers" : [],
                "values"  : ["Yes"],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Affective"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "cand_behavioral_radar" : {
            'chart_type': "RadarChart",
            'chart_title' : "Behavioral",
            'chart_data'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "behavioral",
                'question': "Behavioral",
                "answers" : [],
                "values"  : ["Yes"],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Behavioral"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "cand_ballot_radar" : {
            'chart_type': "RadarChart",
            'chart_title' : "Ballot",
            'chart_data'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "ballot",
                'question': "Ballot",
                "answers" : [],
                "values"  : ["Yes"],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Ballot"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        "cand_descriptors_radar" : {
            'chart_type': "RadarChart",
            'chart_title' : "Descriptors",
            'chart_data'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'transpose'   : True,
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "descriptors",
                'question': "Descriptors",
                "answers" : [],
                "values"  : ["Yes"],
                "metric"  : "doc_count",
                "a-mean"  : True,
                'label'   : "Descriptors"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        }

    dashboard_orange_hedonics = collections.OrderedDict()
    dashboard_orange_hedonics['rows'] = [["liking_blindcode_col"],["strength_blindcode_col"]]

    dashboard_orange_profile = collections.OrderedDict()
    dashboard_orange_profile['columns'] = [
            ["topline_liking_table"],["cand_affective_radar", "cand_behavioral_radar"],
            ["cand_ballot_radar", "cand_descriptors_radar"]
        ]

    storyboard_orange = [
        {'name'     : "Hedonics",
         'layout'   : dashboard_orange_hedonics,
         'active'   : True,
        },
        {'name'     : "Profile",
         'layout'   : dashboard_orange_profile,
         'active'   : False,
        }
        ]

    workbooks = {
        "fresh and clean" : {
            'display'       : ["gender", "age", 'brand', "blindcode", "freshness"],
            'facets'        : ["survey.keyword", "country.keyword", "gender.keyword", "age.keyword", "cluster.keyword", "brand.keyword", "product_form.keyword",
                               "method.keyword", "blindcode.keyword", "olfactive.keyword", "perception.keyword", "liking.keyword"],
            'charts'        : dashboard_fresh,
            'storyboard'    : storyboard_fresh,
            },
        "orange beverages" : {
            'display'       : ["gender", "age", 'brand', "blindcode", "liking"],
            'facets'        : ["survey.keyword", "gender.keyword", "age.keyword", "blindcode.keyword", "liking.keyword",
                               "hedonics", "affective", "ballot", "behavioral", "physical"],
            'charts'        : dashboard_orange,
            'storyboard'    : storyboard_orange,
            },
    }

    ### GLOBAL VARIABLES
             
scrape_li = []
posts_df = DataFrame()
search_keywords = {}

scrape_q = queue.Queue()



