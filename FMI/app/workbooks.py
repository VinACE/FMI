"""
Definition of models.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.views.generic.base import TemplateView

# Create your models here.
import queue
import datetime
import FMI.settings
from collections import OrderedDict
from pandas import DataFrame

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl import DocType, Date, Double, Long, Integer, Boolean
from elasticsearch_dsl.connections import connections
import seeker

from django.utils.encoding import python_2_unicode_compatible

# A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
# in the template this is translated into HTML tables, rows, cells and div elements


# Chart Syntax
# "chart_name"          : <chart_properties>
# <chart_properties>    : <chart_type> <chart_title> <data_type> <controls>? <help>? <listener>? <transpose>? <X_facet> <Y_facet>? <Z_facet>? <options>?
# <chart_type>          : 'chart_type' : <google chart types> | <d3.js chart types>
# <chart_title>         : 'chart_title' : "chart title"
# <data_type>           : 'facet' | 'aggr' | 'hits' | 'topline'
# <controls>            : [ <google chart controls> | 'tile_layout_select' ]
# <google chart controls> : 'CategoryFilter', 'ChartRangeFilter', 'DateRangeFilter', 'NumberRangeFilter', 'StringFilter'
# <options>             : <google chart options>
# <google chart options> : 'width', 'height', 'colors', 'legend', 'bar', <vAxis>, <hAxis>, 'seriesType', <series>
# <transpose>           : True | False
# <X_facet>, <Y-facet> < Z_facet> : <facet>
#
# <facet>               : <field> <label> <total> <type> <question> <answers> <values> <metric> <mean> <order>
# <type>                : 'date'
# <metric>              : <ElasticSearch metric>
# <ElasticSearch metric>: 'doc_count', 'prc'
# <order>               : <ElasticSearch order>
# <ElasticSearch order> : '_count'|'_term' 'asc'|'desc'
#
# <answers>             : [ <answer>* ]
# <answer>              : <string> | <number> (<range>) | {<mapping>*}
# <range>               : <sign>, <string>|<number>
# <mapping>             : <to value> : [<from value>*] | 'single' | 'a-mean' : *|+ | 'a-wmean' : *|+ 'a-sum': x|+|- | 'q-mean' : *|+
# <aggr_type>           : * answer mean replace single, ** question+answer mean replace single, '+' means add                       
#
# <values>              : [ <value>* ]
# <value>               : <string> | <number> (<range>) | {<mapping>*}
# <range>               : <sign>, <string>|<number>
# <mapping>             : <to value> : [<from value>*] | 'single' | 'v-mean' : *|+ | 'v-wmean' : *|+ 'v-sum': *|+
#
# Mean can be the average of the different series within a category, type=answer
# Mean can be the average of a serie of all categores, type=question
# The mean can be shown as its own serie, layout=serie
# The mean can be shown as its own category, layout=category
# The mean can be catured as meta_data and shown in the header, layout=header
# <mean>                : <type>, <layout>
# <type>                : 'answer', 'question'
# <layout>              : 'category', 'serie', 'header'
# 

class ExcelEcoSystemWorkbook:

    dashboard = {
        'company_keyword_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Company / Keyword Doc Count",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "company.keyword",
                'label'   : "Company" },
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "aop_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Area of Potential",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "aop.keyword",
                'label'   : "Area of Potential" },
            },
        "role_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Role",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "role.keyword",
                'label'   : "Role" },
            },
        "keyword_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Keyword Doc Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        }
    dashboard_layout = OrderedDict()
    dashboard_layout['table1'] = [["aop_pie", "keyword_pie"], ["role_col"]]
    dashboard_layout['table2'] = [["company_keyword_table"]]

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

class ExcelPatentsWorkbook:

    dashboard = {
        'assignee_keyword_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Assignee / Keyword Hits",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "assignee.keyword",
                'label'   : "Assignee" },
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "facet_comp_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Competitors Hits",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_comp",
                'label'   : "Competitors" },
            },
        "published_keyword_line" : {
            'chart_type'  : "LineChart",
            'chart_title' : "Published Month Hits",
            'data_type'  : "aggr",
            'controls'    : ['ChartRangeFilter'],
            'X_facet'     : {
                'field'   : "published_date",
                'label'   : "Published",
                'total'   : False,
                'type'    : 'date'},
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            'options'     : {
                "hAxis"   : {'format': 'yy/MMM'},
                },
            },
        "keyword_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Keyword Doc Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        }
    dashboard_layout = OrderedDict()
    dashboard_layout['table1'] = [["published_keyword_line"]]
    dashboard_layout['table2'] = [["facet_comp_pie", "keyword_pie"], ["assignee_keyword_table"]]

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

class PostWorkbook:
    dashboard = {
        'category_keyword_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Category / Keyword Doc Count",
            'data_type'  : "aggr",
            'controls'    : ['CategoryFilter'],
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
            'data_type'  : "aggr",
            'controls'    : ['CategoryFilter'],
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
            'data_type'  : "facet",
            'controls'    : ['CategoryFilter'],
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "facet_cust_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Customers Doc Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_cust",
                'label'   : "Customers" },
            },
        "facet_comp_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Competitors Doc Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_comp",
                'label'   : "Competitors" },
            },
        "published_keyword_line" : {
            'chart_type'  : "LineChart",
            'chart_title' : "Published Month Doc Count",
            'data_type'  : "aggr",
            'controls'    : ['ChartRangeFilter'],
            'X_facet'     : {
                'field'   : "published_date",
                'label'   : "Published",
                'total'   : False,
                'type'    : 'date'},
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            'options'     : {
                "hAxis"   : {'format': 'yy/MMM'},
                },
            },
        }

    dashboard_layout = OrderedDict()
    dashboard_layout['rows1'] = [["published_keyword_line"]]
    dashboard_layout['rows2'] = [["facet_cust_pie", "facet_comp_pie", "facet_keyword_pie"]]
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
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "region.keyword",
                'label'   : "Region"},
            'Y_facet'     : {
                'field'   : "olfactive.keyword",
                'label'   : "Olfactive"},
            },
        "olfactive_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Olfactive Ingr Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "olfactive.keyword",
                'label'   : "Olfactive" },
            },
        "olfactive_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Olfactive Ingr Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "olfactive.keyword",
                'label'   : "Olfactive" },
            },
        "cand_mood_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Mood Top Candidates",
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
    dashboard_olfactive = OrderedDict()
    dashboard_olfactive['rows'] = [["region_olfactive_table"], ["olfactive_pie", "olfactive_col"]]

    dashboard_candidates = OrderedDict()
    dashboard_candidates['rows'] = [["cand_mood_col"],["cand_smell_col"],["cand_intensity_col"]]

    dashboard_profile = OrderedDict()
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

    dashboard = {
        #'region_olfactive_table' : {
        #    'chart_type'  : "Table",
        #    'chart_title' : "Region / Olfactive Ingr Count",
        #    'data_type'  : "facet",
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
        #    'data_type'  : "facet",
        #    'X_facet'     : {
        #        'field'   : "olfactive.keyword",
        #        'label'   : "Olfactive" },
        #    },
        #"olfactive_col" : {
        #    'chart_type': "ColumnChart",
        #    'chart_title' : "Olfactive Ingr Count",
        #    'data_type'  : "facet",
        #    'X_facet'     : {
        #        'field'   : "olfactive.keyword",
        #        'label'   : "Olfactive" },
        #    },
        "cand_emotion_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Emotion Top Candidates",
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
            'data_type'  : "topline",
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
            'data_type'  : "hits",
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
            'data_type'  : "hits",
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
    dashboard_olfactive = OrderedDict()
    dashboard_olfactive['rows'] = [["region_olfactive_table"], ["olfactive_pie", "olfactive_col"]]

    dashboard_candidates = OrderedDict()
    dashboard_candidates['rows'] = [["cand_emotion_col"],["cand_freshness_col"],["cand_hedonics_col"]]

    dashboard_profile = OrderedDict()
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
        #    'data_type'  : "facet",
        #    'X_facet'     : {
        #        'field'   : "liking.keyword",
        #        'label'   : "Liking/Hedonics" },
        #    },
        "cand_emotion_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Candidates / Emotion",
            'data_type'  : "aggr",
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
                "values"  : ["Yes", {'v-sum':'*'}],
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
            'chart_title' : "Liking Candidate #",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Liking/Hedonics",
                'answers' : [('=', '*'), ('!', [0,'','0'])],
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate" },
            },
        "topline_liking_table" : {
            'chart_type'  : "Table",
            'chart_title' : "Topline Liking - Candidate #",
            'data_type'   : "aggr",
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
            'chart_title' : "Freshness Candidate #",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "freshness",
                'label'   : "Freshness" },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate" },
            },
        "topline_freshness_table" : {
            'chart_type'  : "Table",
            'chart_title' : "Topline Freshness - Candidate #",
            'data_type'   : "aggr",
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
            'chart_title' : "Cleanliness Candidate #",
            'data_type'  : "aggr",
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
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "suitable_stage",
                "answers" : [],
                "values"  : [],
                'total'   : False,
                'label'   : "Suitable Stage" },
            },
        "suitable_product_ans_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Suitable Product #",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "suitable_product",
                "answers" : [],
                "values"  : [],
                'total'   : False,
                'label'   : "Suitable Product" },
            },
        "emotion_ans_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Emotion #",
            'data_type'  : "aggr",
            'listener'    : {'select' : {'colsort': None}},
            'X_facet'     : {
                'field'   : "emotion",
                "answers" : [],
                "values"  : ["Yes", "No"],
                'total'   : False,
                'label'   : "Emotion" },
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
            'data_type'  : "aggr",
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
                "values"  : ["Yes", {'v-sum':'*'}],
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
            'data_type'  : "aggr",
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
                "values"  : ["Yes", {'v-sum':'*'}],
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
            'data_type'  : "aggr",
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
                "values"  : ["Yes", {'v-sum':'*'}],
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
            #'chart_type'  : "Table",
            'chart_title' : "Topline Liking - Candidate",
            'data_type'   : "aggr",
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


    dashboard_fresh_layout = OrderedDict()
    dashboard_fresh_layout['rows'] = [["emotion_ans_col"],["suitable_stage_ans_col", "suitable_product_ans_col"]]

    dashboard_fresh_hedonics = OrderedDict()
    dashboard_fresh_hedonics['rows'] = [["liking_blindcode_col"],["freshness_blindcode_col"], ["cleanliness_blindcode_col"]]

    dashboard_fresh_topline = OrderedDict()
    dashboard_fresh_topline['rows'] = [["topline_liking_table"],["topline_freshness_table"],["cand_emotion_col"]]

    dashboard_fresh_profile = OrderedDict()
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

    dashboard_link = {
        'liking_blindcode_col'      : dashboard_fresh['liking_blindcode_col'],
        'topline_liking_table'      : dashboard_fresh['topline_liking_table'],
        'freshness_blindcode_col'   : dashboard_fresh['freshness_blindcode_col'],
        'topline_freshness_table'   : dashboard_fresh['topline_freshness_table'],
        "cand_liking_col" : {
            'chart_type': "ComboChart",
            'chart_title' : "Liking Candidates #",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate",
                'total'   : False
                },
            'Y_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Liking/Hedonics",
                'answers' : [('!', [0,'','0']), {'a-wmean' : '**', 'q-mean' : '*'}],
                },
            'options'     : {
                "seriesType" : 'bars',
                "series"  : {1: {"type": 'line'}, 2: {"type": 'line'}}
                },
            },
        "liking_blindcode_perc_col" : {
            'chart_type': "Table",
            'chart_title' : "Liking Candidate %",
            'data_type'  : "aggr",
            'listener'    : {'select' : {'rowsort': None}},
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Liking/Hedonics",
                'answers' : [('!', [0,'','0']), {'a-mean' : '+'}],
                'calc'    : 'percentile',
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate"},
            'options'     : {
                'sort'    : 'event',
                'frozenColumns' : 2,
                }
            },
        "topline_liking_perc_table" : {
            'chart_type'  : "Table",
            'chart_title' : "Topline Liking - Candidate %",
            'data_type'   : "aggr",
            'base'        : "liking_blindcode_perc_col",
            'controls'    : ['CategoryFilter', 'tile_layout_select'],
            'help'        : "Select Row for sorting, Select Column Header for filter",
            'listener'    : {'sort' : ["cand_emotion_col", "cand_concept_radar", "cand_emotion_radar", "cand_mood_radar"], 'select' : {'rowsort': None}},
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Hedonics_",
                'answers' : [('!', [0,'','0'])],
                'calc'    : 'percentile',
                'lines'   : {"liking.keyword" : {'0-Mean':['mean'], '1-Excellent':[7], '2-Top2':[7,6], '3-Bottom2':[2,1]}},
                },
            'Y_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate"
                },
            'Z_facet'     : {
                'field'   : "product_form.keyword",
                'label'   : "Product Form",
                'order'   : { "_term" : "asc" },
                'tiles'   : 'grid-2x1',
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
        "emotion_perc_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Emotion %",
            'data_type'  : "aggr",
            'listener'    : {'select' : {'colsort': None}},
            'X_facet'     : {
                'field'   : "emotion",
                'label'   : "Emotion",
                'calc'    : 'percentile',
                "answers" : [],
                "values"  : ["Yes", {'v-sum':'*'}],
                'total'   : False },
            },
        "liking_perc_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Liking %",
            'data_type'  : "facet",
            'controls'    : ['CategoryFilter', 'tile_layout_select'],
            'help'        : "Select Legend for sorting Categories",
            'listener'    : {'select' : {'colsort': 'categories'}},
            'X_facet'     : {
                'field'   : "liking.keyword",
                'label'   : "Liking with Mean ",
                #'answers' : [('=', '*'), ('!', [0,'','0']), {'a-mean' : '*'}, {'q-mean' : '+'}],
                'answers' : [('!', [0,'','0']), {'a-mean' : '+'}],
                'calc'    : 'percentile',
                'order'   : { "_term" : "asc" },
                },
            'Z_facet'     : {
                'field'   : "product_form.keyword",
                'label'   : "Product Form",
                'order'   : { "_term" : "asc" },
                'tiles'   : 'dropdown',
                },
            },
        "freshness_perc_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Freshness %",
            'data_type'  : "aggr",
            'controls'    : ['CategoryFilter', 'tile_layout_select'],
            'help'        : "Select Legend for sorting Categories",
            'listener'    : {'select' : {'colsort': 'categories'}},
            'X_facet'     : {
                'field'   : "freshness",
                'label'   : "Freshness with Mean ",
                'answers' : [('!', [0,'','0']), {'a-mean' : '+'}],
                'calc'    : 'percentile',
                'order'   : { "_term" : "asc" },
                },
            'Z_facet'     : {
                'field'   : "product_form.keyword",
                'label'   : "Product Form",
                'order'   : { "_term" : "asc" },
                'tiles'   : 'dropdown',
                },
            },
        "liking_emotion_corr_table" : {
            'chart_type'  : "Table",
            'chart_title' : "Liking / Emotion Correlation",
            'data_type'   : "correlation",
            'base'        : ["liking_perc_col", "emotion_perc_col", "freshness_perc_col"],
            'controls'    : ['CategoryFilter'],
            'facts'       : {'liking.keyword': {'fact' : 'hedonics', 'value_type' : 'ordinal', 'calc' : 'w-avg'},
                             'freshness': {'fact' : 'hedonics', 'value_type' : 'ordinal', 'calc' : 'w-avg'},
                             'emotion'       : {'fact' : 'emotion',  'value_type' : 'boolean', 'calc' : 'w-avg'}},
            'listener'    : {'select' : {'join': ["liking_emotion_scatterl"]}},
            'X_facet'     : {
                'field'   : 'liking.keyword',
                'stats'   : ['answer', 'liking.keyword', 'mean', 'std', 'min', 'max', '25%', '50%', '75%', 'count'],
                'label'   : {'category' : 'Question',
                             'answer':'Answer', 'liking.keyword': 'Liking', 'mean':'Mean', 'std':'Std', 'min':'Min', 'max':'Max', '25%':'25%', '50%':'50%', '75%': '75%',
                             'count':'Tiles'},
                },
            'Y_facet'     : {
                'field'   : 'emotion',
                'corrs'   : 'emotion',
                'label'   : "Emotion"
                },
            'options'     : {
                "allowHtml" : True,
                'frozenColumns' : 2,
                },
            'formatter'  : {
                'setProperty'   : [],
                },
            },
        "liking_emotion_scatter" : {
            'chart_type'  : "ScatterChart",
            'chart_title' : "Liking / Emotion",
            'data_type'   : "join",
            'base'        : ["liking_perc_col", "emotion_perc_col"],
            'X_facet'     : {
                'field'   : 'liking.keyword',
                'label'   : "Liking/Hedonics",
                },
            'Y_facet'     : {
                'field'   : 'emotion',
                'label'   : "Emotion"
                },
            },
        }

    storyboard_link = [
        {'name'     : 'Topline',
         'layout'   : {'rows' : [['liking_blindcode_col'], ['cand_liking_col'], ['liking_blindcode_perc_col'], ['topline_liking_table'], ['topline_liking_perc_table']]},
         'active'   : False,
        },
        {'name'     : 'Hedonics',
         'layout'   : {'rows' : [['topline_liking_perc_table']]},
         'active'   : False,
        },
        {'name'     : 'Intensity',
         'layout'   : {'rows' : [['freshness_blindcode_col'], ['topline_freshness_table']]},
         'active'   : False,
        },
        {'name'     : 'Driver Liking',
         'layout'   : {'rows' : [['liking_perc_col', 'freshness_perc_col'], ['emotion_perc_col'], ['liking_emotion_corr_table', 'liking_emotion_scatter']]},
         'active'   : False,
        },
        {'name'     : 'Fresh',
         'layout'   : {'rows' : [['freshness_perc_col']]},
         'active'   : False,
        }
        ]

    dashboard_orange = {
        "liking_blindcode_col" : {
            'chart_type': "Table",
            'chart_title' : "Liking Candidate #",
            'data_type'  : "aggr",
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
            'chart_title' : "Strength Candidate #",
            'data_type'  : "aggr",
            'transpose'   : True,
            # USE TRANSPOSE SINCE THE REVERSE_NESTING ON AGGR DOESN'T WORK
            'X_facet'     : {
                'field'   : "blindcode.keyword",
                'label'   : "Candidate" },
            'Y_facet'     : {
                'field'   : "hedonics",
                'question': "Strength",
                "answers" : ["strength"],
                "values"  : [],
                "a-mean"  : True,
                'label'   : "Strength"
                },
            },
        "topline_liking_table" : {
            'chart_type'  : "Table",
            'chart_title' : "Topline Liking - Candidate #",
            'data_type'   : "aggr",
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
            'data_type'  : "aggr",
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
                "values"  : ["Yes", {'v-sum':'*'}],
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
            'data_type'  : "aggr",
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
                "values"  : ["Yes", {'v-sum':'*'}],
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
            'data_type'  : "aggr",
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
                "values"  : ["Yes", {'v-sum':'*'}],
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
            'data_type'  : "aggr",
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
                "values"  : ["Yes", {'v-sum':'*'}],
                "a-mean"  : True,
                'label'   : "Descriptors"
                },
            'options'     : {
                'width'   : 300,
                'height'  : 300
                },
            },
        }

    dashboard_orange_hedonics = OrderedDict()
    dashboard_orange_hedonics['rows'] = [["liking_blindcode_col"],["strength_blindcode_col"]]

    dashboard_orange_profile = OrderedDict()
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

    dashboard_panels = {
        "industry_perc_col" : {
            'chart_type': "ColumnChart",
            'chart_title' : "Industry %",
            'data_type'  : "aggr",
            'listener'    : {'select' : {'colsort': None}},
            'X_facet'     : {
                'field'   : "industry",
                'label'   : "Industry",
                'calc'    : 'percentile',
                "answers" : [],
                "values"  : ["Yes", {'v-sum':'*'}],
                'total'   : False },
            },
        }

    dashboard_panels_industry = OrderedDict()
    dashboard_panels_industry['rows'] = [["industry_perc_col"]]

    storyboard_panels = [
        {'name'     : "Industry",
         'layout'   : dashboard_panels_industry,
         'active'   : True,
        }
        ]

    workbooks = {
        "fresh and clean" : {
            'display'       : ["gender", "age", 'brand', "blindcode", "freshness"],
            'facets'        : ["survey.keyword", "country.keyword", "gender.keyword", "age.keyword", "cluster.keyword", "brand.keyword", "product_form.keyword",
                               "method.keyword", "blindcode.keyword", "olfactive.keyword", "perception.keyword", "liking.keyword"],
            'tiles'         : ["country.keyword", "gender.keyword", "age.keyword", "product_form.keyword", "method.keyword", "blindcode.keyword"],
            'charts'        : dashboard_fresh,
            'storyboard'    : storyboard_fresh,
            'dashboard_data': 'push',
            'filters'       : {'survey.keyword' : ["fresh and clean"]}
            },
        "link" : {
            'display'       : ["gender", "age", 'brand', "blindcode", "freshness"],
            'facets'        : ["survey.keyword", "country.keyword", "gender.keyword", "age.keyword", "cluster.keyword", "brand.keyword", "product_form.keyword",
                               "method.keyword", "blindcode.keyword", "olfactive.keyword", "perception.keyword", "liking.keyword"],
            'tiles'         : ["country.keyword", "gender.keyword", "age.keyword", "product_form.keyword", "method.keyword", "blindcode.keyword"],
            'charts'        : dashboard_link,
            'storyboard'    : storyboard_link,
            'dashboard_data': 'pull',
            'filters'       : {'survey.keyword' : ["fresh and clean"]},
            'qst2fld'       : {},
            },
        "orange beverages" : {
            'display'       : ["gender", "age", 'brand', "blindcode", "liking"],
            'facets'        : ["survey.keyword", "gender.keyword", "age.keyword", "blindcode.keyword", "liking.keyword",
                               "hedonics", "affective", "ballot", "behavioral", "physical"],
            'tiles'         : ["gender.keyword", "age.keyword", "blindcode.keyword"],
            'charts'        : dashboard_orange,
            'storyboard'    : storyboard_orange,
            'dashboard_data': 'push',
            'filters'       : {'survey.keyword' : ["orange beverages"]},
            'qst2fld'       : {},
            },
        "global panels" : {
            'display'       : ["gender", "age", 'brand', "blindcode", "freshness"],
            'facets'        : ["survey.keyword", "country.keyword", "gender.keyword", "age.keyword", "cluster.keyword", "brand.keyword", "product_form.keyword",
                               "method.keyword", "blindcode.keyword", "olfactive.keyword", "perception.keyword", "liking.keyword"],
            'tiles'         : ["country.keyword", "gender.keyword", "age.keyword", "product_form.keyword", "method.keyword", "blindcode.keyword"],
            'charts'        : dashboard_panels,
            'storyboard'    : storyboard_panels,
            'dashboard_data': 'pull',
            'filters'       : {'survey.keyword' : ["global panels"]},
            'qst2fld'       : {
                                "industry"          : (["industry"], 'nested_qst_ans'),
                                "health_condition"  : (["health_condition"], 'nested_qst_ans'),
                                "product"           : (["product"], 'nested_qst_ans'),
                                "format_used"       : (["format_used"], 'nested_qst_ans'),
                                "format_rejected"   : (["format_rejected"], 'nested_qst_ans'),
                                "consumer_nature"   : (["consumer_nature"], 'nested_qst_ans'),
                                "purpose"           : (["purpose"], 'nested_qst_ans'),
                                "ideal_benefits"    : (["ideal_benefits"], 'nested_qst_ans'),
                                "air_emotion"       : (["air_emotion"], 'nested_qst_ans'),
                                "cleaners_emotion"  : (["cleaners_emotion"], 'nested_qst_ans'),
                                "expected_benefits" : (["expected_benefits"], 'nested_qst_ans'),
                              },
            },
    }

    ### GLOBAL VARIABLES
             
scrape_li = []
posts_df = DataFrame()
search_keywords = {}
molecules_d = {}

scrape_q = queue.Queue()



