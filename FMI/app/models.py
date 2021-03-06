﻿"""
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
from elasticsearch_dsl import DocType, Date, Boolean, Text, Nested, Keyword
from elasticsearch_dsl.connections import connections
import seeker
import app.workbooks as workbooks

from django.utils.encoding import python_2_unicode_compatible


client = Elasticsearch(FMI.settings.ES_HOSTS)


import django.db.models.options as options
options.DEFAULT_NAMES = options.DEFAULT_NAMES + (
    'es_index_name', 'es_type_name', 'es_mapping'
)

###
### Excel
###

#
# Based on the headers of an excel file, this ExcelDoc and ExcelSeekerView models are created.
# During Crawl each row of the excel file is turned into a Document and stored in the 'excel' index
# with doc_type the name of the excel file.
# During Search the 'excel' index with the right doc_type is searched.
#

# Class name has to match the name of the mapping in ES (doc_type)
class ecosystem(models.Model):
    subset = models.TextField()
    aop = models.TextField()
    role = models.TextField()
    name = models.TextField()
    url = models.TextField()
    why = models.TextField()
    how = models.TextField()
    what = models.TextField()
    who = models.TextField()
    where = models.TextField()
    country = models.TextField()
    contacts = models.TextField()
    company = models.TextField()

class patents(models.Model):
    category = models.TextField()
    publication = models.TextField()
    title = models.TextField()
    title_DWPI = models.TextField()
    url = models.TextField()
    published_date = models.DateField()
    assignee = models.TextField()
    assignee_DWPI = models.TextField()
    abstract = models.TextField()

class ExcelSeekerView (seeker.SeekerView):
    document = None
    using = client
    index = "excel"
    page_size = 30
    facets = [
        ]
    facets_keyword = [];
    display = [
        ]
    sort = []
    summary = []
    sumheader = []
    SUMMARY_URL="{}"
    urlfields = {
        }
    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}

class ExcelEcoSystemSeekerView (seeker.SeekerView, workbooks.ExcelEcoSystemWorkbook):
    document = None
    using = client
    index = "excel"
    page_size = 30
    facets = [
        seeker.TermsFacet("aop.keyword", label = "Area of Potential"),
        seeker.TermsFacet("role.keyword", label = "Role"),
        seeker.TermsFacet("country.keyword", label = "Country"),
        seeker.TermsFacet("company.keyword", label = "company"),
        ]
    facets_keyword = [seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k")]
    display = [
        "company",
        "aop",
        "role",
        "why",
        "how",
        "what",
        ]
    sort = []
    summary = ['why', 'how', 'what']
    sumheader = ['company']
    SUMMARY_URL="{}"
    urlfields = {
        "company" : ""
        }
    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}


class ExcelPatentsSeekerView (seeker.SeekerView, workbooks.ExcelPatentsWorkbook):
    document = None
    using = client
    index = "excel"
    page_size = 30
    facets = [
        seeker.TermsFacet("category.keyword", label = "Category"),
        seeker.DayHistogram("published_date", label = "Published"),
        seeker.TermsFacet("assignee.keyword", label = "Assignee"),
        ]
    facets_keyword = [seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k"),
                      seeker.KeywordFacet("facet_comp", label = "Competitors", input="keywords_comp",
                            initial="International Flavors & Fragrances, Symrise, Givaudan, Firmenich, Frutarom")]
    display = [
        "title",
        "category",
        "assignee",
        "publication",
        "published_date"
        ]
    sort = []
    summary = ['title', 'abstract']
    sumheader = ['title']
    SUMMARY_URL="{}"
    urlfields = {
        "title" : "",
        "publication" : ""
        }
    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}


###
### Fragrantica
###

# Class name has to match the name of the mapping in ES (doc_type)
class Perfume(models.Model):
    perfume = models.CharField(max_length=200)
    review_date = models.DateField()
    review = models.TextField()
    label = models.CharField(max_length=10)
    accords = models.TextField()
    img_src = models.TextField()

class Review(models.Model):
    reviewid = models.IntegerField()
    perfume = models.CharField(max_length=200)
    review_date = models.DateField()
    review = models.TextField()
    label = models.CharField(max_length=10)
    accords = []
    img_src = models.TextField()

    class Meta:
        es_index_name = 'review'
        es_type_name = 'perfume'
        es_mapping = {
            'properties' : {
                'perfume'       : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'review_date'   : {'type' : 'date'},
                'review'        : {'type' : 'text'},
                'label'         : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'accords'       : {
                    'properties' : {
                        'accord' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'votes'  : {'type' : 'integer'},
                        }
                    },
                'img_src'        : {'type' : 'text'},
                }
            }

    def es_repr(self):
        data = {}
        mapping = self._meta.es_mapping
        data['_id'] = self.reviewid
        for field_name in mapping['properties'].keys():
            data[field_name] = self.field_es_repr(field_name)
        return data
    def field_es_repr(self, field_name):
        config = self._meta.es_mapping['properties'][field_name]
        if hasattr(self, 'get_es_%s' % field_name):
            field_es_value = getattr(self, 'get_es_%s' % field_name)()
        else:
            if config['type'] == 'object':
                related_object = getattr(self, field_name)
                field_es_value = {}
                field_es_value['_id'] = related_object.pk
                for prop in config['properties'].keys():
                    field_es_value[prop] = getattr(related_object, prop)
            else:
                field_es_value = getattr(self, field_name)
        return field_es_value
    def get_es_accords(self):
        return [{'accord': accord, 'votes': votes} for accord, votes in self.accords.items()]

class PerfumeSeekerView (seeker.SeekerView):
    document = None
    using = client
    index = "review"
    page_size = 30
    facets = [
        seeker.TermsFacet("perfume.keyword", label = "Perfume"),
        seeker.YearHistogram("review_date", label = "Reviewed"),
        seeker.TermsFacet("label.keyword", label = "Sentiment"),
        seeker.TermsFacet("accords.accord.keyword", label = "Accords"),
        ]
    facets_keyword = [seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k")];
    display = [
        "perfume",
        "review_date",
        "img_src",
        "review",
        "label",
        ]
    sort = [
        "-review_date"
        ]
    summary = ['review']
    sumheader = ['perfume']
    SUMMARY_URL="{}"

    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}

    dashboard = {
        'perfume_keyword_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Perfume / Keyword Doc Count",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "perfume.keyword",
                'label'   : "Perfume" },
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "keyword_label_table" : {
            'chart_type': "Table",
            'chart_title' : "Keyword / Category Doc Count",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            'Y_facet'     : {
                'field'   : "label.keyword",
                'label'   : "Label" },
            },
        "keyword_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Keyword Doc Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "reviewed_keyword_line" : {
            'chart_type'  : "LineChart",
            'chart_title' : "Reviewed Year Doc Count",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "review_date",
                'label'   : "Reviewed",
                'key'     : 'key_as_string'},
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        }
    dashboard_layout = collections.OrderedDict()
    dashboard_layout['table1'] = [["reviewed_keyword_line"], ["keyword_label_table"]]
    dashboard_layout['table2'] = [["perfume_keyword_table", "keyword_pie"]]

    storyboard = [
        {'name' : 'initial',
         'layout'   : dashboard_layout,
         'active'   : True,
         }
    ]


###
### Market Intelligence
###

class Post(models.Model):
    editor_id = models.CharField(max_length=30)
    published_date = models.DateField()
    post_category_id = models.CharField(max_length=30)
    title = models.CharField(max_length=256)
    relevance = models.TextField()
    subject = models.TextField()
    topline = models.TextField()
    source = models.TextField()
    article = models.TextField()
    average_rating = models.FloatField()
    rating_count = models.IntegerField()
    num_comments_id = models.IntegerField()

class PostMap(models.Model):
    post_id = models.IntegerField()
    editor_id = models.CharField(max_length=30)
    published_date = models.DateField()
    post_category_id = models.CharField(max_length=30)
    title = models.CharField(max_length=256)
    relevance = models.TextField()
    subject = models.TextField()
    topline = models.TextField()
    source = models.TextField()
    article = models.TextField()
    average_rating = models.FloatField()
    rating_count = models.IntegerField()
    num_comments_id = models.IntegerField()
    class Meta:
        es_index_name = 'post'
        es_type_name = 'post'
        es_mapping = {
            'properties' : {
                'editor_id'         : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'published_date'    : {'type' : 'date'},
                'post_category_id'  : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'title'             : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'relevance'         : {'type' : 'text'},
                'subject'           : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'topline'           : {'type' : 'text'},
                'source'            : {'type' : 'text'},
                'article'           : {'type' : 'text'},
                'average_rating'    : {'type' : 'float'},
                'rating_count'      : {'type' : 'integer', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'num_comments_id'   : {'type' : 'integer', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                }
            }
    def es_repr(self):
        data = {}
        mapping = self._meta.es_mapping
        data['_id'] = self.post_id
        for field_name in mapping['properties'].keys():
            data[field_name] = self.field_es_repr(field_name)
        return data
    def field_es_repr(self, field_name):
        config = self._meta.es_mapping['properties'][field_name]
        if hasattr(self, 'get_es_%s' % field_name):
            field_es_value = getattr(self, 'get_es_%s' % field_name)(field_name)
        else:
            if config['type'] == 'object':
                related_object = getattr(self, field_name)
                field_es_value = {}
                field_es_value['_id'] = related_object.pk
                for prop in config['properties'].keys():
                    field_es_value[prop] = getattr(related_object, prop)
            else:
                field_es_value = getattr(self, field_name)
        return field_es_value
    def get_es_article(self, field_name):
        list_es_value = getattr(self, field_name)
        if len(list_es_value) > 32766:
            list_es_value = list_es_value[:32766]
        return list_es_value


class PostSeekerView (seeker.SeekerView, workbooks.PostWorkbook):
    document = None
    using = client
    index = "post"
    page_size = 30
    facets = [
        seeker.TermsFacet("post_category_id.keyword", label = "Category"),
        seeker.TermsFacet("editor_id.keyword", label = "Editor"),
        seeker.TermsFacet("subject.keyword", label = "Subject"),
        #seeker.YearHistogram("published_date", label = "Published Year"),
        seeker.MonthHistogram("published_date", label = "Published Month"),
        #seeker.RangeFilter("rating_count", label = "Rating"),
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k"),
        seeker.KeywordFacet("facet_cust", label = "Customers", input="keywords_cust",
                            initial="unilever, procter & gamble, P&G, sc johnson, johnson & johnson, henkel"),
        seeker.KeywordFacet("facet_comp", label = "Competitors", input="keywords_comp",
                            initial="symrise, givaudan, firmenich, frutarom")
        ];
    display = [
        "post_category_id",
        "published_date",
        "title",
        "subject",
        "relevance",
        "topline"
        ]
    summary = [
        "article"
        ]
    sumheader = [
        "title"
        ]
    urlfields = {
        "title" : ""
        }
    SUMMARY_URL="https://iffconnect.iff.com/Fragrances/marketintelligence/Lists/Posts/ViewPost.aspx?ID={}"

    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}


###
### Costmetics
###

class Page(models.Model):
    page_id = models.IntegerField()
    posted_date = models.DateField()
    site = models.TextField()
    sub_site = models.TextField()
    section = models.TextField()
    title = models.TextField()
    url = models.TextField()
    page = models.TextField()

class PageMap(models.Model):
    page_id = models.IntegerField()
    posted_date = models.DateField()
    site = models.TextField()
    sub_site = models.TextField()
    section = models.TextField()
    title = models.TextField()
    url = models.TextField()
    page = models.TextField()

    class Meta:
        es_index_name = 'page'
        es_type_name = 'page'
        es_mapping = {
            'properties' : {
                'posted_date'   : {'type' : 'date'},
                'site'          : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'sub_site'      : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'section'       : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'title'         : {'type' : 'text'},
                'url'           : {'type' : 'text'},
                'page'          : {'type' : 'text'},
                }
            }
    def es_repr(self):
        data = {}
        mapping = self._meta.es_mapping
        data['_id'] = self.page_id
        for field_name in mapping['properties'].keys():
            data[field_name] = self.field_es_repr(field_name)
        return data
    def field_es_repr(self, field_name):
        config = self._meta.es_mapping['properties'][field_name]
        if hasattr(self, 'get_es_%s' % field_name):
            field_es_value = getattr(self, 'get_es_%s' % field_name)()
        else:
            if config['type'] == 'object':
                related_object = getattr(self, field_name)
                field_es_value = {}
                field_es_value['_id'] = related_object.pk
                for prop in config['properties'].keys():
                    field_es_value[prop] = getattr(related_object, prop)
            else:
                field_es_value = getattr(self, field_name)
        return field_es_value


class PageSeekerView (seeker.SeekerView):
    document = None
    using = client
    index = "page"
    page_size = 30
    facets = [
        seeker.TermsFacet("site.keyword", label = "Site"),
        seeker.TermsFacet("sub_site.keyword", label = "Sub Site"),
        seeker.TermsFacet("section.keyword", label = "Section"),
        seeker.MonthHistogram("posted_date", label = "Posted Month"),
        seeker.YearHistogram("posted_date", label = "Posted Year")
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k"),
        seeker.KeywordFacet("facet_cust", label = "Customers", input="keywords_cust",
                            initial="unilever, procter & gamble, P&G, sc johnson, johnson & johnson, henkel"),
        seeker.KeywordFacet("facet_comp", label = "Competitors", input="keywords_comp",
                            initial="symrise, givaudan, firmenich, frutarom")
        ];
    display = [
        "posted_date",
        "title",
        "site",
        "sub_site",
        ]
    summary = [
        "page"
        ]
    sumheader = [
        "title"
        ]
    urlfields = {
        "title" : ""
        }
    SUMMARY_URL="{}"


    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}

    # A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
    # in the template this is translated into HTML tables, rows, cells and div elements
    dashboard = collections.OrderedDict()
    dashboard_layout = {}
    storyboard = [
        {'name' : 'initial',
         'layout'   : dashboard_layout,
         'active'   : True,
         }
    ] 

###
### FEEDLY
###

class Feedly(models.Model):
    post_id = models.IntegerField()
    subset = models.TextField()
    published_date = models.DateField()
    category = models.TextField()
    feed = models.TextField()
    feed_topics = models.TextField()
    body_topics = models.TextField()
    title = models.TextField()
    url = models.TextField()
    body = models.TextField()
 
class FeedlyMap(models.Model):
    post_id = models.IntegerField()
    subset = models.TextField()
    published_date = models.DateField()
    category = models.TextField()
    feed = models.TextField()
    feed_topics = models.TextField()
    body_topics = models.TextField()
    title = models.TextField()
    url = models.TextField()
    body = models.TextField()

    class Meta:
        es_index_name = 'feedly'
        es_type_name = 'feedly'
        es_mapping = {
            'properties' : {
                'published_date'    : {'type' : 'date'},
                'subset'            : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'category'          : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'feed'              : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'feed_topics'       : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'body_topics'       : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                'title'             : {'type' : 'text'},
                'url'               : {'type' : 'text'},
                'body'              : {'type' : 'text'},
                #'body'              : {'type' : 'text', 'fields' : {
                #    'body_keepwords'    : {'type': 'text', 'analyzer': 'keepwords'},
                #    'body_keeplength'   : {'type': 'token_count', 'analyzer': 'keepwords'}}},
                }
            }
    def es_repr(self):
        data = {}
        mapping = self._meta.es_mapping
        data['_id'] = self.post_id
        for field_name in mapping['properties'].keys():
            data[field_name] = self.field_es_repr(field_name)
        return data
    def field_es_repr(self, field_name):
        config = self._meta.es_mapping['properties'][field_name]
        if hasattr(self, 'get_es_%s' % field_name):
            field_es_value = getattr(self, 'get_es_%s' % field_name)()
        else:
            if config['type'] == 'object':
                related_object = getattr(self, field_name)
                field_es_value = {}
                field_es_value['_id'] = related_object.pk
                for prop in config['properties'].keys():
                    field_es_value[prop] = getattr(related_object, prop)
            else:
                field_es_value = getattr(self, field_name)
        return field_es_value


class FeedlySeekerView (seeker.SeekerView):
    document = None
    using = client
    index = "feedly"
    page_size = 30
    facets = [
        seeker.TermsFacet("subset.keyword", label = "Subset"),
        seeker.TermsFacet("category.keyword", label = "Category"),
        seeker.TermsFacet("feed.keyword", label = "Feed"),
        seeker.TermsFacet("feed_topics.keyword", label = "Topics"),
        seeker.DayHistogram("published_date", label = "Published")
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k"),
        seeker.KeywordFacet("facet_cust", label = "Customers", input="keywords_cust",
                            initial="unilever, procter & gamble, P&G, sc johnson, johnson & johnson, henkel"),
        seeker.KeywordFacet("facet_comp", label = "Competitors", input="keywords_comp",
                            initial="symrise, givaudan, firmenich, frutarom")
        ];
    display = [
        "published_date",
        "title",
        "category",
        "feed",
        "feed_topics",
        "body_topics",
        ]
    summary = [
        "body"
        ]
    sumheader = [
        "title"
        ]
    urlfields = {
        "title" : ""
        }
    SUMMARY_URL="{}"

    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}

    # A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
    # in the template this is translated into HTML tables, rows, cells and div elements
    dashboard = {
        'category_keyword_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Category / Keyword Doc Count",
            'data_type'  : "aggr",
            'controls'    : ['CategoryFilter'],
            'X_facet'     : {
                'field'   : "category.keyword",
                'label'   : "Category" },
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        'feed_keyword_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Feed / Keyword Doc Count",
            'data_type'  : "aggr",
            'X_facet'     : {
                'field'   : "feed.keyword",
                'label'   : "Feed" },
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "keyword_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Keyword Doc Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "customer_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Customer Doc Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_cust",
                'label'   : "Customer" },
            },
        "competitor_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Competitor Doc Count",
            'data_type'  : "facet",
            'X_facet'     : {
                'field'   : "facet_comp",
                'label'   : "Competitor" },
            },
        "published_keyword_line" : {
            'chart_type'  : "LineChart",
            'chart_title' : "Published Year Doc Count",
            'data_type'  : "aggr",
            'controls'    : ['ChartRangeFilter'],
            'X_facet'     : {
                'field'   : "published_date",
                'label'   : "Published",
                'key'     : 'key_as_string',
                'total'   : False,
                'type'    : 'date'},
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            'options'     : {
                "hAxis"   : {'format': 'yy/MMM/d'},
                },
            },
        }
    dashboard_layout = collections.OrderedDict()
    dashboard_layout['rows1'] = [["published_keyword_line"], ["customer_pie", "competitor_pie", "keyword_pie"]]
    dashboard_layout['rows2'] = [["category_keyword_table", "feed_keyword_table"]]

    storyboard = [
        {'name' : 'initial',
         'layout'   : dashboard_layout,
         'active'   : True,
         }
    ]       


###
### Scent Emotion (CFT - Ingredients)
###

class Scentemotion(models.Model):
    cft_id = models.IntegerField()
    dataset = models.TextField()
    ingr_name = models.TextField()
    IPC = models.TextField()
    supplier = models.TextField()
    olfactive = models.TextField()
    region = models.TextField()
    review = models.TextField()
    dilution = models.TextField()
    intensity = models.TextField()
    mood = models.TextField()
    smell = models.TextField()
    negative = models.TextField()
    descriptor = models.TextField()
    color = models.TextField()
    texture = models.TextField()
    emotion = models.TextField()
    hedonics = models.TextField()

 
class ScentemotionMap(models.Model):
    cft_id = models.IntegerField()
    dataset = models.TextField()
    ingr_name = models.TextField()
    IPC = models.TextField()
    supplier = models.TextField()
    olfactive = models.TextField()
    region = models.TextField()
    review = models.TextField()
    dilution = models.TextField()
    intensity = models.TextField()
    mood = []
    smell = []
    negative = []
    descriptor = []
    color = []
    texture = []
    emotion = []
    hedonics = []

    class Meta:
        es_index_name = 'scentemotion'
        es_type_name = 'scentemotion'
        es_mapping = {
            "properties" : {
                "dataset"           : {"type" : "string", "fields" : {"keyword" : {"type" : "keyword", "ignore_above" : 256}}},
                "ingr_name"         : {"type" : "string", "fields" : {"raw" : {"type" : "string", "index" : "not_analyzed"}}},
                "IPC"               : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "supplier"          : {"type" : "string", "fields" : {"keyword" : {"type" : "keyword", "ignore_above" : 256}}},
                "olfactive"         : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "region"            : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "review"            : {"type" : "text"},
                "dilution"          : {"type" : "string", "fields" : {"raw" : {"type" : "string", "index" : "not_analyzed"}}},
                "intensity"         : {"type" : "string", "fields" : {"raw" : {"type" : "string", "index" : "not_analyzed"}}},
                'mood'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'smell'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'negative'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'descriptor'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'color'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'texture'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'emotion'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'hedonics'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                }
            }

    def es_repr(self):
        data = {}
        mapping = self._meta.es_mapping
        data['_id'] = self.cft_id
        for field_name in mapping['properties'].keys():
            data[field_name] = self.field_es_repr(field_name)
        return data
    def get_es_mood(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_smell(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_negative(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_descriptor(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_color(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_texture(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_emotion(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_hedonics(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def field_es_repr(self, field_name):
        config = self._meta.es_mapping['properties'][field_name]
        if hasattr(self, 'get_es_%s' % field_name):
            field_es_value = getattr(self, 'get_es_%s' % field_name)(field_name)
        else:
            if config['type'] == 'object':
                related_object = getattr(self, field_name)
                field_es_value = {}
                field_es_value['_id'] = related_object.pk
                for prop in config['properties'].keys():
                    field_es_value[prop] = getattr(related_object, prop)
            else:
                field_es_value = getattr(self, field_name)
                if config['type'] == 'integer' and type(field_es_value) == str:
                    field_es_value = int(float(field_es_value))
                if (config['type'] == 'string' or config['type'] == 'text') and type(field_es_value) == int:
                    field_es_value = "{0:d}".format(field_es_value)
        return field_es_value


class ScentemotionSeekerView (seeker.SeekerView, workbooks.ScentemotionWorkbook):
    document = None
    using = client
    index = "scentemotion"
    page_size = 20
    facets = [
        seeker.TermsFacet("dataset.keyword", label = "Dataset / Survey"),
        seeker.TermsFacet("olfactive.keyword", label = "Olfactive"),
        seeker.TermsFacet("region.keyword", label = "Region"),
        seeker.TermsFacet("IPC.keyword", label = "IPC", visible_pos=0),
        seeker.TermsFacet("intensity", label = "Intensity", nestedfield="intensity", visible_pos=0),
        #seeker.TermsFacet("mood.keyword", label = "Mood"),
        #seeker.TermsFacet("smell.keyword", label = "Smell"),
        seeker.NestedFacet("mood.val.keyword", label = "Mood", nestedfield="mood"),
        seeker.NestedFacet("smell.val.keyword", label = "Smell", nestedfield="smell"),
        seeker.NestedFacet("negative.val.keyword", label = "Negative", nestedfield="negative"),
        seeker.NestedFacet("descriptor.val.keyword", label = "Descriptor", nestedfield="descriptor"),
        seeker.NestedFacet("color.val.keyword", label = "Color", nestedfield="color"),
        seeker.NestedFacet("texture.val.keyword", label = "Texture", nestedfield="texture"),
        seeker.NestedFacet("emotion.val.keyword", label = "Emotion", nestedfield="emotion", visible_pos=0),
        seeker.NestedFacet("hedonics.val.keyword", label = "Hedonics", nestedfield="hedonics", visible_pos=0),
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Benchmark", input="keywords_k"),
        ];
    display = [
        "IPC",
        "ingr_name",
        "olfactive",
        'intensity',
        "descriptor",
        "region",
        "mood",
        "smell",
        "negative",
        "review",
        ]
    sort = [
        #"-descriptor"
    ]
    exclude = [
        "cft_id",
        "dataset",  
        ]
    field_labels = {
        "mood"        : "Mood",
        "smell"       : "Smell",
        "negative"    : "Negative",
        "descriptor"  : "Descr",
        "color"       : "Color",
        "texture"     : "Texture"
        }
    summary = [
        ]
    sumheader = ["ingr_name"]
    urlfields = {
        "IPC"       : "http://sappw1.iff.com:50200/irj/servlet/prt/portal/prtroot/com.sap.ip.bi.designstudio.nw.portal.ds?APPLICATION=E2ESCENARIO_002?{0}",
        "ingr_name" : "http://www.iff.com/smell/online-compendium#{0}"
        }
    SUMMARY_URL="http://www.iff.com/smell/online-compendium#amber-xtreme"

    tabs = {'results_tab': 'active', 'summary_tab': 'hide', 'storyboard_tab': '', 'insights_tab': 'hide'}
      
    # A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
    # in the template this is translated into HTML tables, rows, cells and div elements


###
### Scent Emotion (CFT - CI Studies)
###

class Studies(models.Model):
    cft_id = models.IntegerField()
    dataset = models.TextField()
    ingr_name = models.TextField()
    IPC = models.TextField()
    olfactive = models.TextField()
    region = models.TextField()
    intensity = models.TextField()
    perception = models.TextField()
    method = models.TextField()
    product_form = models.TextField()
    freshness = models.IntegerField()
    cleanliness = models.IntegerField()
    lastingness  = models.IntegerField()
    intensity = models.IntegerField()
    liking = models.TextField()
    concept = models.TextField()
    emotion = models.TextField()
    fragrattr = models.TextField()
    mood = models.TextField()
    smell = models.TextField()
    suitable_product = models.TextField()
    suitable_stage = models.TextField()
    hedonics = models.TextField()

 
class StudiesMap(models.Model):
    cft_id = models.IntegerField()
    dataset = models.TextField()
    ingr_name = models.TextField()
    IPC = models.TextField()
    olfactive = models.TextField()
    region = models.TextField()
    intensity = models.TextField()
    perception = []
    method = []
    product_form = []
    freshness = []
    cleanliness = []
    lastingness  = []
    intensity = []
    liking = []
    concept = []
    emotion = []
    fragrattr = []
    mood = []
    smell = []
    suitable_product = []
    suitable_stage = []
    hedonics = []

    class Meta:
        es_index_name = 'studies'
        es_type_name = 'studies'
        es_mapping = {
            "properties" : {
                "dataset"           : {"type" : "string", "fields" : {"keyword" : {"type" : "keyword", "ignore_above" : 256}}},
                "ingr_name"         : {"type" : "string", "fields" : {"raw" : {"type" : "string", "index" : "not_analyzed"}}},
                "IPC"               : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "olfactive"         : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "region"            : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "intensity"         : {"type" : "string", "fields" : {"raw" : {"type" : "string", "index" : "not_analyzed"}}},
                'perception'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'method'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'product_form'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'freshness'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'cleanliness'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'lastingness'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'intensity'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'liking'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },

                'concept'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'emotion'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'fragrattr'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'mood'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'smell'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'suitable_product'         : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'suitable_stage'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                'hedonics'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'val' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'prc' : {'type' : 'float'},
                        }
                    },
                }
            }

    def es_repr(self):
        data = {}
        mapping = self._meta.es_mapping
        data['_id'] = self.cft_id
        for field_name in mapping['properties'].keys():
            data[field_name] = self.field_es_repr(field_name)
        return data
    def get_es_perception(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_method(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_product_form(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_freshness(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_cleanliness(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_lastingness(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_intensity(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_liking(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_concept(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_emotion(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_fragrattr(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_mood(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_smell(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_suitable_product(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_suitable_stage(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def get_es_hedonics(self, field_name):
        list_es_value = getattr(self, field_name)
        field_es_value = [{'val':t[0], 'prc':t[1]} for t in list_es_value]
        return field_es_value
    def field_es_repr(self, field_name):
        config = self._meta.es_mapping['properties'][field_name]
        if hasattr(self, 'get_es_%s' % field_name):
            field_es_value = getattr(self, 'get_es_%s' % field_name)(field_name)
        else:
            if config['type'] == 'object':
                related_object = getattr(self, field_name)
                field_es_value = {}
                field_es_value['_id'] = related_object.pk
                for prop in config['properties'].keys():
                    field_es_value[prop] = getattr(related_object, prop)
            else:
                field_es_value = getattr(self, field_name)
                if config['type'] == 'integer' and type(field_es_value) == str:
                    field_es_value = int(float(field_es_value))
                if (config['type'] == 'string' or config['type'] == 'text') and type(field_es_value) == int:
                    field_es_value = "{0:d}".format(field_es_value)
        return field_es_value


class StudiesSeekerView (seeker.SeekerView, workbooks.StudiesWorkbook):
    document = None
    using = client
    index = "studies"
    page_size = 20
    facets = [
        seeker.TermsFacet("dataset.keyword", label = "Dataset / Survey"),
        seeker.TermsFacet("olfactive.keyword", label = "Olfactive"),
        seeker.TermsFacet("region.keyword", label = "Region", visible_pos=0),
        seeker.TermsFacet("IPC.keyword", label = "IPC", visible_pos=1),
        seeker.NestedFacet("perception.val.keyword", label = "Perception", nestedfield="perception", visible_pos=0),
        seeker.NestedFacet("method.val.keyword", label = "Method", nestedfield="method", visible_pos=1),
        seeker.NestedFacet("product_form.val.keyword", label = "Product Form", nestedfield="product_form", visible_pos=0),
        seeker.NestedFacet("freshness.val.keyword", label = "Freshness", nestedfield="freshness", visible_pos=1),
        seeker.NestedFacet("cleanliness.val.keyword", label = "Cleanliness", nestedfield="cleanliness", visible_pos=0),
        seeker.NestedFacet("lastingness.val.keyword", label = "Lastingness", nestedfield="lastingness", visible_pos=0),
        seeker.NestedFacet("intensity.val.keyword", label = "Intensity", nestedfield="intensity", visible_pos=0),
        seeker.NestedFacet("liking.val.keyword", label = "Liking", nestedfield="liking", visible_pos=0),
        seeker.NestedFacet("concept.val.keyword", label = "Concept", nestedfield="concept", visible_pos=0),
        seeker.NestedFacet("emotion.val.keyword", label = "Emotion", nestedfield="emotion", visible_pos=1),
        seeker.NestedFacet("fragrattr.val.keyword", label = "Fragr Attr", nestedfield="fragrattr", visible_pos=0),
        seeker.NestedFacet("mood.val.keyword", label = "Mood", nestedfield="mood", visible_pos=0),
        seeker.NestedFacet("smell.val.keyword", label = "Smell", nestedfield="smell", visible_pos=0),
        seeker.NestedFacet("suitable_product.val.keyword", label = "Suitable Product", nestedfield="suitable_product", visible_pos=0),
        seeker.NestedFacet("suitable_stage.val.keyword", label = "Suitable Stage", nestedfield="suitable_stage", visible_pos=1),
        seeker.NestedFacet("hedonics.val.keyword", label = "Hedonics", nestedfield="hedonics", visible_pos=1),
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Benchmark", input="keywords_k"),
        ];
    display = [
        "IPC",
        "olfactive",
        "emotion",
        "suitable_product",
        "suitable_stage",
        "hedonics",
        ]
    sort = [
        "-hedonics"
    ]
    exclude = [
        "cft_id",
        "dataset",  
        ]
    field_labels = {
        "mood"        : "Mood",
        "smell"       : "Smell",
        "negative"    : "Negative",
        "descriptor"  : "Descr",
        "color"       : "Color",
        "texture"     : "Texture"
        }
    summary = [
        ]
    sumheader = ["ingr_name"]
    urlfields = {
        "IPC"       : "http://sappw1.iff.com:50200/irj/servlet/prt/portal/prtroot/com.sap.ip.bi.designstudio.nw.portal.ds?APPLICATION=E2ESCENARIO_002?{0}",
        "ingr_name" : "http://www.iff.com/smell/online-compendium#{0}"
        }
    SUMMARY_URL="http://www.iff.com/smell/online-compendium#amber-xtreme"

    tabs = {'results_tab': '', 'summary_tab': 'hide', 'storyboard_tab': 'active', 'insights_tab': 'hide'}

###
### Survey (CI)
###

class Survey(models.Model):
    resp_id = models.TextField()
    survey = models.TextField()
    country = models.TextField()
    cluster = models.TextField()
    gender = models.TextField()
    age = models.TextField()
    ethnics = models.TextField()
    city = models.TextField()
    regions = models.TextField()
    education = models.TextField()
    income = models.TextField()
    blindcode = models.TextField()
    brand = models.TextField()
    variant = models.TextField()
    olfactive = models.TextField()
    perception = models.TextField()
    method = models.TextField()
    product_form = models.TextField()
    freshness = models.IntegerField()
    cleanliness = models.IntegerField()
    lastingness  = models.IntegerField()
    intensity = models.IntegerField()
    liking = models.TextField()

    affective = models.TextField()
    ballot = models.TextField()
    behavioral = models.TextField()
    children = models.TextField()
    concept = models.TextField()
    descriptors = models.TextField()
    emotion = models.TextField()
    fragrattr = models.TextField()
    hedonics = models.TextField()
    mood = models.TextField()
    physical = models.TextField()
    smell = models.TextField()
    suitable_product = models.TextField()
    suitable_stage = models.TextField()

 
class SurveyMap(models.Model):
    resp_id = models.TextField()
    survey = models.TextField()
    country = models.TextField()
    cluster = models.TextField()
    gender = models.TextField()
    age = models.TextField()
    ethnics = models.TextField()
    city = models.TextField()
    regions = models.TextField()
    education = models.TextField()
    income = models.TextField()
    blindcode = models.TextField()
    brand = models.TextField()
    variant = models.TextField()
    olfactive = models.TextField()
    perception = models.TextField()
    method = models.TextField()
    product_form = models.TextField()
    freshness = models.IntegerField()
    cleanliness = models.IntegerField()
    lastingness  = models.IntegerField()
    intensity = models.IntegerField()
    liking = models.TextField()

    affective = []
    ballot = []
    behavioral = []
    children = []
    concept = []
    descriptors = []
    emotion = []
    fragrattr = []
    hedonics = []
    mood = []
    physical = []
    smell = []
    suitable_product = []
    suitable_stage = []

    class Meta:
        es_index_name = 'survey'
        es_type_name = 'survey'
        es_mapping = {
            "properties" : {
                "survey"            : {"type" : "string", "fields" : {"keyword" : {"type" : "keyword", "ignore_above" : 256}}},
                "country"           : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "cluster"           : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "gender"            : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "age"               : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "ethnics"           : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "city"              : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "regions"           : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "education"         : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "income"            : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "blindcode"            : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "brand"             : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "variant"           : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "olfactive"         : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "perception"        : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "method"            : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                "product_form"      : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},
                'freshness'         : {'type' : 'integer'},
                'cleanliness'       : {'type' : 'integer'},
                'lastingness'       : {'type' : 'integer'},
                'intensity'         : {'type' : 'integer'},
                "liking"            : {"type" : "string", "fields" : {
                                            "keyword" : {"type" : "keyword", "ignore_above" : 256},
                                            "raw" : {"type" : "string", "index" : "not_analyzed"}
                                       }},

                'affective'          : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'ballot'          : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'behavioral'          : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'children'          : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'concept'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'descriptors'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'emotion'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'fragrattr'          : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'hedonics'          : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'mood'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'physical'              : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'smell'          : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'suitable_product'       : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                'suitable_stage'       : {
                    'type'       : 'nested',
                    'properties' : {
                        'question' : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        'answer'   : {'type' : 'string', 'fields' : {'keyword' : {'type' : 'keyword', 'ignore_above' : 256}}},
                        }
                    },
                }
            }

    def es_repr(self):
        data = {}
        mapping = self._meta.es_mapping
        data['_id'] = self.resp_id
        for field_name in mapping['properties'].keys():
            data[field_name] = self.field_es_repr(field_name)
        return data
    def field_es_repr(self, field_name):
        config = self._meta.es_mapping['properties'][field_name]
        if hasattr(self, 'get_es_%s' % field_name):
            field_es_value = getattr(self, 'get_es_%s' % field_name)(field_name)
        else:
            if config['type'] == 'object':
                related_object = getattr(self, field_name)
                field_es_value = {}
                field_es_value['_id'] = related_object.pk
                for prop in config['properties'].keys():
                    field_es_value[prop] = getattr(related_object, prop)
            else:
                field_es_value = getattr(self, field_name)
                if config['type'] == 'integer' and type(field_es_value) == str:
                    field_es_value = int(float(field_es_value))
        return field_es_value
    def get_es_affective(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.affective.items()]
    def get_es_ballot(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.ballot.items()]
    def get_es_behavioral(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.behavioral.items()]
    def get_es_children(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.children.items()]
    def get_es_concept(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.concept.items()]
    def get_es_descriptors(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.descriptors.items()]
    def get_es_emotion(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.emotion.items()]
    def get_es_fragrattr(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.fragrattr.items()]
    def get_es_hedonics(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.hedonics.items()]
    def get_es_mood(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.mood.items()]
    def get_es_physical(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.physical.items()]
    def get_es_smell(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.smell.items()]
    def get_es_suitable_product(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.suitable_product.items()]
    def get_es_suitable_stage(self, field_name):
        return [{'question': q, 'answer': a} for q, a in self.suitable_stage.items()]


class SurveySeekerView (seeker.SeekerView, workbooks.SurveyWorkbook):
    document = None
    using = client
    index = "survey"
    page_size = 30
    facets = [
        seeker.TermsFacet("survey.keyword", label = "Survey"),
        seeker.TermsFacet("country.keyword", label = "Country"),
        seeker.TermsFacet("regions.keyword", label = "Region", visible_pos=0),
        seeker.TermsFacet("city.keyword", label = "City", visible_pos=0),
        seeker.TermsFacet("gender.keyword", label = "Gender"),
        seeker.TermsFacet("ethnics.keyword", label = "Ethnics", visible_pos=0),
        seeker.TermsFacet("income.keyword", label = "Income", visible_pos=0),
        seeker.TermsFacet("age.keyword", label = "Age"),
        #seeker.RangeFilter("age", label = "Age"),
        seeker.TermsFacet("cluster.keyword", label = "Cluster"),
        seeker.TermsFacet("brand.keyword", label = "Brand"),
        seeker.TermsFacet("product_form.keyword", label = "Product Form"),
        seeker.TermsFacet("method.keyword", label = "Method"),
        seeker.TermsFacet("blindcode.keyword", label = "Blind Code"),
        seeker.TermsFacet("olfactive.keyword", label = "Olfactive"),
        seeker.TermsFacet("perception.keyword", label = "Perception"),
        seeker.TermsFacet("liking.keyword", label = "Liking/Hedonics", order={"_term":"desc"}),
        seeker.TermsFacet("freshness", label = "Freshness", visible_pos=0, order={"_term":"desc"}),
        seeker.TermsFacet("cleanliness", label = "Cleanliness", visible_pos=0, order={"_term":"desc"}),
        seeker.TermsFacet("lastingness", label = "Lastingness", visible_pos=0, order={"_term":"desc"}),
        seeker.TermsFacet("intensity", label = "Intensity", visible_pos=0, order={"_term":"desc"}),
        seeker.OptionFacet("affective", label = "Affective", nestedfield="affective", visible_pos=0),
        seeker.OptionFacet("ballot", label = "Ballot", nestedfield="ballot", visible_pos=0),
        seeker.OptionFacet("behavioral", label = "Behavioral", nestedfield="behavioral", visible_pos=0),
        seeker.OptionFacet("children", label = "Children", nestedfield="children", visible_pos=0),
        seeker.OptionFacet("concept", label = "Concept", nestedfield="concept", visible_pos=0),
        seeker.OptionFacet("descriptors", label = "Descriptors", nestedfield="descriptors", visible_pos=0),
        seeker.OptionFacet("emotion", label = "Emotion", nestedfield="emotion", visible_pos=0),
        seeker.OptionFacet("fragrattr", label = "Fragr Attr", nestedfield="fragrattr", visible_pos=0),
        seeker.OptionFacet("hedonics", label = "Hedonics", nestedfield="hedonics", visible_pos=0),
        seeker.OptionFacet("mood", label = "Mood", nestedfield="mood", visible_pos=0),
        seeker.OptionFacet("physical", label = "Physical", nestedfield="physical", visible_pos=0),
        seeker.OptionFacet("smell", label = "Smell", nestedfield="smell", visible_pos=0),
        seeker.OptionFacet("suitable_product", label = "Suitability Product", nestedfield="suitable_product", visible_pos=0),
        seeker.OptionFacet("suitable_stage", label = "Suitability Stage", nestedfield="suitable_stage", visible_pos=2),
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Benchmark", input="keywords_k"),
        ];
    #display = [
    #    "gender",
    #    "age",
    #    'brand',
    #    "blindcode",
    #    "freshness",
    #    ]
    exclude = [
        "resp_id",
        ]
    field_labels = {
        "question_p"    : "Question",
        }
    summary = [
        ]
    sumheader = ['brand']
    SUMMARY_URL="https://iffconnect.iff.com?id={0}"
    
    tabs = {'results_tab': '', 'summary_tab': 'hide', 'storyboard_tab': 'active', 'insights_tab': '' }
    decoder = None

    ### GLOBAL VARIABLES
             
scrape_li = []
posts_df = DataFrame()
molecules_d = {}
search_keywords = {}

scrape_q = queue.Queue()



