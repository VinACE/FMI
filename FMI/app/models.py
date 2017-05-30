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
import app.workbooks as workbooks

from django.utils.encoding import python_2_unicode_compatible

#class Author (models.Model):
#    first_name = models.CharField(max_length=100)
#    last_name = models.CharField(max_length=100)
#    bio = models.TextField()

#    def __str__(self):
#        return '%s %s' % (self.first_name, self.last_name)

#class Category (models.Model):
#    name = models.CharField(max_length=100)

#    def __str__(self):
#        return self.name

#class Book (models.Model):
#    title = models.CharField(max_length=200)
#    authors = models.ManyToManyField(Author, related_name='books', blank=True)
#    category = models.ForeignKey(Category, related_name='books', null=True, blank=True)
#    date_published = models.DateField(default=datetime.date.today)
#    pages = models.IntegerField(default=0)

#    def __str__(self):
#        return self.title

#class Magazine (models.Model):
#    name = models.CharField(max_length=200)
#    issue_date = models.DateField(default=datetime.date.today)

#    def __str__(self):
#        return self.name


#from elasticsearch import Elasticsearch, RequestsHttpConnection
#ES_CLIENT = Elasticsearch(
#    ['http://127.0.0.1:9200/'],
#    connection_class=RequestsHttpConnection
#)

#connections.create_connection(hosts=['localhost'])
#connections.create_connection(hosts=['108.61.167.27'])
#client = Elasticsearch(['108.61.167.27'])
client = Elasticsearch(FMI.settings.ES_HOSTS)


class Account(models.Model):
    account_number = models.IntegerField()
    address = models.CharField(max_length=200)
    age = models.IntegerField()
    balance = models.FloatField()
    city = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    employer = models.CharField(max_length=30)
    firstname = models.CharField(max_length=30)
    lastname = models.CharField(max_length=30)
    state = models.CharField(max_length=30)

#class MagazineDoc(DocType):
#    name = String()
#    issue_date = Date()



import django.db.models.options as options
options.DEFAULT_NAMES = options.DEFAULT_NAMES + (
    'es_index_name', 'es_type_name', 'es_mapping'
)


class Accord(models.Model):
    accord = models.CharField(max_length=20)
    votes = models.IntegerField()


class BookSeekerView (seeker.SeekerView):
    document = None
    using = client
    index = "seeker-tests"
    facets = [
        seeker.TermsFacet("category.raw.keyword", label = "Category"),
        seeker.YearHistogram("date_published", label = "Published")
        ]

class AccountSeekerView (seeker.SeekerView):
    document = None
    using = client
    index = "bank"
    page_size = 30
    facets = [
        seeker.TermsFacet("state.keyword", label = "State"),
        ]

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
            'chart_data'  : "facet",
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
            'chart_data'  : "facet",
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
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "reviewed_keyword_line" : {
            'chart_type'  : "LineChart",
            'chart_title' : "Reviewed Year Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "review_date",
                'label'   : "Reviewed",
                'key'     : 'key_as_string'},
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        }
    dashboard_layout = {
        'table1' : [["reviewed_keyword_line"], ["keyword_label_table"]],
        'table2' : [["perfume_keyword_table", "keyword_pie"]]
        }
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
                'topline'           : {'type' : 'text'},
                'source'            : {'type' : 'text'},
                'article'           : {'type' : 'text', "fields" : { "raw": { "type":  "keyword" }}},
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

class PostSeekerView (seeker.SeekerView):
    document = None
    using = client
    index = "post"
    page_size = 30
    facets = [
        seeker.TermsFacet("post_category_id.keyword", label = "Category"),
        seeker.TermsFacet("editor_id.keyword", label = "Editor"),
        seeker.YearHistogram("published_date", label = "Published"),
        seeker.RangeFilter("rating_count", label = "Rating"),
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k"),
        seeker.KeywordFacet("facet_corp", label = "Corporations", input="keywords_corp")
        ];
    display = [
        "post_category_id",
        "published_date",
        "title",
        "relevance",
        "topline"
        ]
    summary = [
        "article"
        ]
    sumheader = [
        "title"
        ]
    SUMMARY_URL="https://iffconnect.iff.com/Fragrances/marketintelligence/Lists/Posts/ViewPost.aspx?ID={}"

    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}

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
        "keyword_category_table" : {
            'chart_type': "Table",
            'chart_title' : "Keyword / Category Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            'Y_facet'     : {
                'field'   : "post_category_id.keyword",
                'label'   : "Category" },
            },
        "facet_keyword_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Keyword Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "facet_coorp_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Corporation Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_corp",
                'label'   : "Corporations" },
            },
        "published_keyword_line" : {
            'chart_type'  : "LineChart",
            'chart_title' : "Published Year Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "published_date",
                'label'   : "Published",
                'key'     : 'key_as_string'},
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        }

    dashboard_layout = {
        'table1' : [["published_keyword_line"], ["keyword_category_table"]],
        'table2' : [["category_keyword_table", "facet_keyword_pie", "facet_coorp_pie"]]
        }
    storyboard = [
        {'name' : 'initial',
         'layout'   : dashboard_layout,
         'active'   : True,
         }
    ] 


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
        seeker.TermsFacet("sub_site.keyword", label = "Sub Site"),
        seeker.TermsFacet("section.keyword", label = "Section"),
        seeker.YearHistogram("posted_date", label = "Posted")
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k"),
        seeker.KeywordFacet("facet_corp", label = "Corporations", input="keywords_corp")
        ];
    display = [
        "posted_date",
        "section",
        "title"
        ]
    summary = [
        "page"
        ]
    sumheader = [
        "title"
        ]
    SUMMARY_URL="{}"

    # A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
    # in the template this is translated into HTML tables, rows, cells and div elements
    dashboard = {}
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
        seeker.TermsFacet("category.keyword", label = "Category"),
        seeker.TermsFacet("feed.keyword", label = "Feed"),
        seeker.TermsFacet("feed_topics.keyword", label = "Topics"),
        seeker.DayHistogram("published_date", label = "Published")
        ]
    facets_keyword = [
        seeker.KeywordFacet("facet_keyword", label = "Keywords", input="keywords_k"),
        seeker.KeywordFacet("facet_corp", label = "Corporations", input="keywords_corp")
        ];
    display = [
        "published_date",
        "category",
        "feed",
        "title",
        "feed_topics",
        "body_topics",
        ]
    summary = [
        "body"
        ]
    sumheader = [
        "title"
        ]
    SUMMARY_URL="{}"

    tabs = {'results_tab': 'active', 'summary_tab': '', 'storyboard_tab': '', 'insights_tab': 'hide'}

    # A dashboard layout is a dictionary of tables. Each table is a list of rows and each row is a list of charts
    # in the template this is translated into HTML tables, rows, cells and div elements
    dashboard = {
        'feed_keyword_table' : {
            'chart_type'  : "Table",
            'chart_title' : "Category / Keyword Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "feed.keyword",
                'label'   : "Feed" },
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "keyword_feed_table" : {
            'chart_type': "Table",
            'chart_title' : "Keyword / Category Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            'Y_facet'     : {
                'field'   : "feed.keyword",
                'label'   : "Feed" },
            },
        "facet_keyword_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Keyword Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        "facet_feed_pie" : {
            'chart_type': "PieChart",
            'chart_title' : "Feed Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "feed.keyword",
                'label'   : "Feeds" },
            },
        "published_keyword_line" : {
            'chart_type'  : "LineChart",
            'chart_title' : "Published Year Doc Count",
            'chart_data'  : "facet",
            'X_facet'     : {
                'field'   : "published_date",
                'label'   : "Published",
                'key'     : 'key_as_string'},
            'Y_facet'     : {
                'field'   : "facet_keyword",
                'label'   : "Keywords" },
            },
        }
    dashboard_layout = {
        'table1' : [["published_keyword_line"], ["keyword_feed_table"]],
        'table2' : [["feed_keyword_table", "facet_feed_pie", "facet_keyword_pie"]]
        }
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


class ScentemotionSeekerView (seeker.SeekerView):
    document = None
    using = client
    index = "scentemotion"
    page_size = 20
    facets = [
        seeker.TermsFacet("dataset.keyword", label = "Dataset / Survey"),
        seeker.TermsFacet("olfactive.keyword", label = "Olfactive"),
        seeker.TermsFacet("region.keyword", label = "Region"),
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
        "-descriptor"
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
    dashboard_olfactive = {
        'rows' : [["region_olfactive_table"], ["olfactive_pie", "olfactive_col"]],
        }
    dashboard_candidates = {
        'rows' : [["cand_mood_col"],["cand_smell_col"],["cand_intensity_col"]],
        }
    dashboard_profile = {
        'columns' : [["cand_intensity_col"], ["mood_cand_radar", "smell_cand_radar"], ["negative_cand_radar", "descriptor_cand_radar"]],
        }
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


class StudiesSeekerView (seeker.SeekerView):
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
    dashboard_olfactive = {
        'rows' : [["region_olfactive_table"], ["olfactive_pie", "olfactive_col"]],
        }
    dashboard_candidates = {
        'rows' : [["cand_emotion_col"],["cand_freshness_col"],["cand_hedonics_col"]],
        }
    dashboard_profile = {
        'columns' : [["hedonics_cand_table"], ["suitable_stage_cand_bar"],["suitable_stage_cand_radar"]],
        }
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

 
class SurveyMap(models.Model, workbooks.SurveyWorkbook):
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
        seeker.TermsFacet("liking.keyword", label = "Liking/Hedonics"),
        seeker.TermsFacet("freshness", label = "Freshness", visible_pos=0),
        seeker.TermsFacet("cleanliness", label = "Cleanliness", visible_pos=0),
        seeker.TermsFacet("lastingness", label = "Lastingness", visible_pos=0),
        seeker.TermsFacet("intensity", label = "Intensity", visible_pos=0),
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
search_keywords = {}

scrape_q = queue.Queue()



