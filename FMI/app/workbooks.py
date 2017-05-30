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
from pandas import DataFrame

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl import DocType, Date, Double, Long, Integer, Boolean
from elasticsearch_dsl.connections import connections
import seeker

from django.utils.encoding import python_2_unicode_compatible

# A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
# in the template this is translated into HTML tables, rows, cells and div elements  

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

    dashboard_fresh_layout = {
        'rows' : [["emotion_ans_col"],["suitable_stage_ans_col", "suitable_product_ans_col"]]
        }

    dashboard_fresh_hedonics = {
        'rows' : [["liking_blindcode_col"],["freshness_blindcode_col"], ["cleanliness_blindcode_col"]]
        }
    dashboard_fresh_topline = {
        'rows' : [["topline_liking_table"],["topline_freshness_table"],["cand_emotion_col"]]
        }
    dashboard_fresh_profile = {
        'columns' : [["topline_liking_table"],["topline_liking_combo"],["cand_concept_radar", "cand_emotion_radar"],["cand_mood_radar"]]
        }

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

    dashboard_orange_hedonics = {
        'rows' : [["liking_blindcode_col"],["strength_blindcode_col"]]
        }
    dashboard_orange_profile = {
        'columns' : [["topline_liking_table"],["cand_affective_radar", "cand_behavioral_radar"],["cand_ballot_radar", "cand_descriptors_radar"]]
        }

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
            'charts'        : dashboard_fresh,
            'storyboard'    : storyboard_fresh,
            },
        "orange beverages" : {
            'charts'        : dashboard_orange,
            'storyboard'    : storyboard_orange,
            },
    }

    ### GLOBAL VARIABLES
             
scrape_li = []
posts_df = DataFrame()
search_keywords = {}

scrape_q = queue.Queue()



