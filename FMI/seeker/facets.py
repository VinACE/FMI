from django.conf import settings
from elasticsearch_dsl import Search, A, Q
import functools
import operator
from .mapping import DEFAULT_ANALYZER

class Facet (object):
    field = None
    label = None
    visible_pos = 1
    keywords_input = 'keywords_k'

    template = getattr(settings, 'SEEKER_DEFAULT_FACET_TEMPLATE', 'app/seeker/facets/terms.html')

    def __init__(self, field, label=None, name=None, description=None, template=None, visible_pos = 1, **kwargs):
        self.field = field
        self.label = label or self.field.replace('_', ' ').replace('.raw', '').replace('.', ' ').capitalize()
        self.name = (name or self.field).replace('.raw', '').replace('.', '_')
        self.template = template or self.template
        self.description = description
        self.visible_pos = visible_pos
        self.kwargs = kwargs

    def aggr(self, **extra):
        params = {}
        return params 

    # term
    #   agg_name = self.name (facet)
    #   search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1)
    # term * term (chart)
    #   agg_name = chart_name
    #   search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1).\
    #                      bucket(x_field, 'terms', field=x_field, size=40, min_doc_count=1)
    # term * term * term (chart)
    #   agg_name = chart_name
    #       search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1).\
    #                       bucket(x_field, 'terms', field=x_field, size=40, min_doc_count=1).\
    #                           bucket(y_field, 'terms', field=y_field, size=40, min_doc_count=1)
    # term * nestedterm - q/a (chart)
    #   agg_name = chart_name
    #        search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1).\
    #                   bucket(nestedfield, 'nested', path=nestedfield).\
    #                       bucket('question', 'terms', field=nestedfield+".question.keyword", size=40, min_doc_count=1).\
    #                           bucket('answer', 'terms', field=nestedfield+".answer.keyword", size=40, min_doc_count=1)
    # term * optionterm - val (chart)
    #   agg_name = chart_name
    #        search.aggs.bucket(self.name, 'nested', path=self.nestedfield).bucket('val', 'terms', field=self.field, size=40, min_doc_count=1)
    # term * optionterm
    #   agg_name = chart_name
    #        search.aggs.bucket(self.name, 'nested', path=self.nestedfield).\
    #                    bucket('question', 'terms', field=self.nestedfield+".question.keyword", size=40, min_doc_count=1).\
    #                        bucket('answer', 'terms', field=self.nestedfield+".answer.keyword", size=40, min_doc_count=1)
    def apply(self, search, agg_name, aggs_stack, **extra):
        return search

    def filter(self, search, values):
        return search

    def data(self, response):
        try:
            #print("Facet.data", self.name)
            return response.aggregations[self.name].to_dict()
        except:
            if self.name in response.aggregations:
                pass
                #print("Facet.data failed", response.aggregations[self.name])
            else:
                pass
                #print("Facet.data failed, no aggregations")
            return {}

    def get_key(self, bucket):
        return bucket.get('key')

    def buckets(self, response):
        for b in self.data(response).get('buckets', []):
            yield self.get_key(b), b.get('doc_count')


class TermsFacet (Facet):

    def __init__(self, field, **kwargs):
        self.filter_operator = kwargs.pop('filter_operator', 'or')
        super(TermsFacet, self).__init__(field, **kwargs)

    def _get_aggregation(self, **extra):
        params = {
            'field': self.field,
            'size' : 40,
            'min_doc_count': 1
            }
        params.update(self.kwargs)
        params.update(extra)
        return A('terms', **params)

    # use apply for aggregation (facet, chart, tile)
    def apply(self, search, agg_name, aggs_stack, **extra):
        #search.aggs[self.name] = self._get_aggregation(**extra)
        if agg_name in aggs_stack:
            aggs_tail = search.aggs[agg_name]
            for sub_agg_name in aggs_stack[agg_name][1:]:
                aggs_tail = aggs_tail.aggs[sub_agg_name]
            aggs_stack[agg_name].append(self.name)
            sub_agg_name = self.name
            #aggs_tail.bucket(self.name, 'terms', field=self.field, size=40, min_doc_count=1)
        else:
            aggs_tail = search
            aggs_stack[agg_name] = [agg_name]
            sub_agg_name = agg_name
        aggs_tail.aggs[sub_agg_name] = self._get_aggregation(**extra)
        if extra:
            aggs_stack[agg_name].append(list(extra['aggs'].keys())[0])
        #search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1)
        return search

    ## use apply for facet tile aggregation
    #def apply_tile(self,  search, chart_name, x_field, y_field, **extra):
    #    agg_name = self.name+'_'+chart_name
    #    #if y_field == None:
    #    #    search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1).\
    #    #                    bucket(x_field, 'terms', field=x_field, size=40, min_doc_count=1)
    #    #else:
    #    #    search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1).\
    #    #                    bucket(x_field, 'terms', field=x_field, size=40, min_doc_count=1).\
    #    #                        bucket(y_field, 'terms', field=y_field, size=40, min_doc_count=1)
    #    search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1)
    #    aggs_tail = search.aggs[agg_name]
    #    #search.aggs[agg_name].bucket(x_field, 'terms', field=x_field, size=40, min_doc_count=1)
    #    aggs_tail.bucket(x_field, 'terms', field=x_field, size=40, min_doc_count=1)
    #    aggs_tail = aggs_tail.aggs[x_field]
    #    if y_field:
    #        #search.aggs[agg_name].aggs[x_field].bucket(y_field, 'terms', field=y_field, size=40, min_doc_count=1)
    #        aggs_tail.bucket(y_field, 'terms', field=y_field, size=40, min_doc_count=1)
    #    return search

    ##use apply for facet aggregation
    #def apply_tile_nested(self, search, agg_name, nestedfield, **extra):
    #    #search.aggs[self.name] = self._get_aggregation(**extra)
    #    search.aggs.bucket(agg_name, 'terms', field=self.field, size=40, min_doc_count=1).\
    #                    bucket(nestedfield, 'nested', path=nestedfield).\
    #                        bucket('question', 'terms', field=nestedfield+".question.keyword", size=40, min_doc_count=1).\
    #                            bucket('answer', 'terms', field=nestedfield+".answer.keyword", size=40, min_doc_count=1)
    #    return search


    def filter(self, search, values):
        if len(values) > 1:
            if self.filter_operator.lower() == 'and':
                filters = [Q('term', **{self.field: v}) for v in values]
                return search.query(functools.reduce(operator.and_, filters))
            else:
                return search.filter('terms', **{self.field: values})
        elif len(values) == 1:
            return search.filter('term', **{self.field: values[0]})
        return search

class NestedFacet (TermsFacet):
    template = 'app/seeker/facets/nestedterms.html'
    rangeon = True
    rangemin = 0.25
    rangemax = 0.0
    nestedfield = ''
    sort_nested_filter = None

    def __init__(self, field, nestedfield=None, **kwargs):
        self.nestedfield = nestedfield
        super(NestedFacet, self).__init__(field, **kwargs)

    #"aggs": {
    #  "smell": {
    #    "terms": {
    #      "field": "smell.keyword"
    #    }
    #  },
    #  "texture_p": {
    #    "nested": {
    #      "path": "texture_p"
    #    },
    #    "aggs": {
    #      "texture": {
    #        "terms": {
    #          "field": "texture_p.val.keyword"
    #        }
    #      }
    #    }
    #  }
    #}

    def _get_aggregation(self, **extra):
        params = {
            'path': self.nestedfield,
            'aggs': {
                'val' : {
                    'terms' : {
                        'field' : self.field,
                        'size'  : 40,
                        'min_doc_count' : 1
                        }
                    }
                }
            }
        params.update(self.kwargs)
        params.update(extra)
        return A('nested', **params)

    # use apply for aggregation (facet, chart, tile)
    def apply(self, search, agg_name, aggs_stack, **extra):
        #search.aggs.bucket(agg_name, 'nested', path=self.nestedfield).bucket('val', 'terms', field=self.field, size=40, min_doc_count=1)
        if agg_name in aggs_stack:
            aggs_tail = search.aggs[self.name]
            for sub_agg_name in aggs_stack[agg_name][1:]:
                aggs_tail = aggs_tail.aggs[sub_agg_name]
            aggs_stack[agg_name].append(self.name)
            sub_agg_name = self.name
        else:
            aggs_tail = search
            aggs_stack[agg_name] = [agg_name]
            sub_agg_name = agg_name
        aggs_tail.aggs[sub_agg_name] = self._get_aggregation(**extra)
        return search


    def filter(self, search, values):
        self.sort_nested_filter = None
        query = None
        field = self.nestedfield
        field_val = field+".val.keyword"
        field_prc = field+".prc"
        if len(values) > 1:
            filters = []
            terms_filter = {field_val : []}
            for val in values:
                terms_filter[field_val].append(val)
                sub_filter = [{"term": {field_val: val}}, {"range": {field_prc: {"gte": self.rangemin}}}]
                filter = {"path": field, "query" : {"bool" : {"must": sub_filter}}}
                search = search.filter('nested', **filter)
            nested_filter = [{"terms": terms_filter}, {"range": {field_prc: {"gte": self.rangemin}}}]
            query = {"bool" : {"must": nested_filter}}
        elif len(values) == 1:
            sub_filter = [{"term": {field_val: values[0]}}, {"range": {field_prc: {"gte": self.rangemin}}}]
            filter = {"path": field, "query" : {"bool" : {"must": sub_filter}}}
            query = {"bool" : {"must" : sub_filter}}
            self.sort_nested_filter = query
            return search.filter('nested', **filter)
        self.sort_nested_filter = query
        return search

    def sort(self):
        return self.sort_nested_filter


class OptionFacet (TermsFacet):
    template = 'app/seeker/facets/optionterms.html'
    rangeon = True
    rangemin = 0.25
    rangemax = 0.0
    nestedfield = ''
    sort_nested_filter = None

    def __init__(self, field, nestedfield=None, **kwargs):
        self.nestedfield = nestedfield
        super(OptionFacet, self).__init__(field, **kwargs)

    def _get_aggregation(self, **extra):
        params = {
            'path': self.nestedfield,
            'aggs': {
                'question' : {
                    'terms': {
                        "field" : self.nestedfield+".question.keyword",
                        "size"  : 40,
                        "min_doc_count" : 1
                        },
                    'aggs' : {
                        "answer" : {
                            'terms' : {
                                "field" : self.nestedfield+".answer.keyword",
                                "size"  : 40,
                                "min_doc_count" : 1
                                }
                            }
                        }
                    }
                }
            }
        params.update(self.kwargs)
        params.update(extra)
        return A('nested', **params)

    # use apply for aggregation (facet, chart, tile)
    def apply(self, search, agg_name, aggs_stack, **extra):
        #search.aggs.bucket(agg_name, 'nested', path=self.nestedfield).\
        #               bucket('question', 'terms', field=self.nestedfield+".question.keyword", size=40, min_doc_count=1).\
        #                   bucket('answer', 'terms', field=self.nestedfield+".answer.keyword", size=40, min_doc_count=1)
        if agg_name in aggs_stack:
            aggs_tail = search.aggs[agg_name]
            for sub_agg_name in aggs_stack[agg_name][1:]:
                aggs_tail = aggs_tail.aggs[sub_agg_name]
            aggs_stack[agg_name].append(self.name)
            sub_agg_name = self.name
        else:
            aggs_tail = search
            aggs_stack[agg_name] = [agg_name]
            sub_agg_name = agg_name
        aggs_tail.aggs[sub_agg_name] = self._get_aggregation(**extra)
        return search

    def filter(self, search, values):
        self.sort_nested_filter = None
        query = None
        field = self.nestedfield
        q_field = field+".question.keyword"
        a_field = field+".answer.keyword"
        filters = []
        terms_filter = {q_field : []}
        for val in values:
            m = val.find('^')
            q = val[:m]
            a = val[m+1:]
            terms_filter[q_field].append(q)
            sub_filter = [{"term": {q_field: q}}, {"term": {a_field: a}}]
            filter = {"path": field, "query" : {"bool" : {"must": sub_filter}}}
            search = search.filter('nested', **filter)
        nested_filter = [{"terms": terms_filter}]
        query = {"bool" : {"must": nested_filter}}
        self.sort_nested_filter = query
        return search

    def sort(self):
        return self.sort_nested_filter

class KeywordFacet (TermsFacet):
    template = 'app/seeker/facets/keyword.html'
    keywords_input = ''
    keywords_text = ''
    keywords_k = []
    read_keywords = ''

    def __init__(self, field, input=None, **kwargs):
        self.keywords_input = input
        super(KeywordFacet, self).__init__(field, **kwargs)

    #"aggs": {
    #  "perfume": {
    #    "terms": {
    #      "field": "perfume.keyword"
    #    },
    #    "aggs": {
    #      "keyfig": {
    #        "filters": {
    #          "filters": {
    #            "bottle": {
    #              "multi_match": {
    #                "query": "bottle",
    #                "fields": [
    #                  "review"
    #                ]
    #              }
    #            },
    #            "floral": {
    #              "multi_match": {
    #                "query": "floral",
    #                "fields": [
    #                  "review"
    #                ]
    #              }
    #            }
    #          }
    #        }
    #      }
    #    }
    #  },

    def _get_aggregation(self, **extra):
        params = {}
        params.update(extra)
        return A('filters', **params)

    # use apply for aggregation (facet, chart, tile)
    def apply(self, search, agg_name, aggs_stack, **extra):
        if agg_name in aggs_stack:
            aggs_tail = search.aggs[agg_name]
            for sub_agg_name in aggs_stack[agg_name][1:]:
                aggs_tail = aggs_tail.aggs[sub_agg_name]
            aggs_stack[agg_name].append(self.name)
            sub_agg_name = self.name
        else:
            aggs_tail = search
            aggs_stack[agg_name] = [agg_name]
            sub_agg_name = agg_name
        aggs_tail.aggs[sub_agg_name] = self._get_aggregation(**extra)
        return search

    def data(self, response):
        try:
            #print("KeywordFacet.data", self.name)
            return response.aggregations[self.name].to_dict()
        except:
            if self.name in response.aggregations:
                pass
                #print("KeywordFacet.data failed", response.aggregations[self.name])
            else:
                pass
                #print("KeywordFacet.data failed, no aggregations")
            return {'keyword': 'Enter your keywords'}


class GlobalTermsFacet (TermsFacet):

    def apply(self, search, agg_name, aggs_stack, **extra):
        top = A('global')
        top[self.field] = self._get_aggregation(**extra)
        search.aggs[self.field] = top
        return search

    def data(self, response):
        print("GlobalTemrsFacet.data", self.name)
        return response.aggregations[self.field][self.field].to_dict()


class YearHistogram (Facet):
    template = 'app/seeker/facets/year_histogram.html'

    def _get_aggregation(self, **extra):
        params = {
            'field': self.field,
            'interval': 'year',
            'format': 'yyyy',
            'min_doc_count': 1,
            'order': {'_key': 'desc'},
        }
        params.update(self.kwargs)
        params.update(extra)
        return A('date_histogram', **params)

    def apply(self, search, agg_name, aggs_stack, **extra):
        if agg_name in aggs_stack:
            aggs_tail = search.aggs[agg_name]
            for sub_agg_name in aggs_stack[agg_name][1:]:
                aggs_tail = aggs_tail.aggs[sub_agg_name]
            aggs_stack[agg_name].append(self.name)
            sub_agg_name = self.name
        else:
            aggs_tail = search
            aggs_stack[agg_name] = [agg_name]
            sub_agg_name = agg_name
        aggs_tail.aggs[sub_agg_name] = self._get_aggregation(**extra)
        return search

    def filter(self, search, values):
        if len(values) > 0:
            filters = []
            for val in values:
                kw = {
                    self.field: {
                        'gte': '%s-01-01T00:00:00' % val,
                        'lte': '%s-12-31T23:59:59' % val,
                    }
                }
                filters.append(Q('range', **kw))
            search = search.query(functools.reduce(operator.or_, filters))
        return search

    def get_key(self, bucket):
        return bucket.get('key_as_string')

class MonthHistogram (Facet):
    template = 'app/seeker/facets/year_histogram.html'

    def _get_aggregation(self, **extra):
        params = {
            'field': self.field,
            'interval': 'month',
            'format': 'yyyy-MM',
            'min_doc_count': 1,
            'order': {'_key': 'desc'},
        }
        params.update(self.kwargs)
        params.update(extra)
        return A('date_histogram', **params)

    def apply(self, search, agg_name, aggs_stack, **extra):
        if agg_name in aggs_stack:
            aggs_tail = search.aggs[agg_name]
            for sub_agg_name in aggs_stack[agg_name][1:]:
                aggs_tail = aggs_tail.aggs[sub_agg_name]
            aggs_stack[agg_name].append(self.name)
            sub_agg_name = self.name
        else:
            aggs_tail = search
            aggs_stack[agg_name] = [agg_name]
            sub_agg_name = agg_name
        aggs_tail.aggs[sub_agg_name] = self._get_aggregation(**extra)
        return search

    def filter(self, search, values):
        if len(values) > 0:
            filters = []
            for val in values:
                kw = {
                    self.field: {
                        'gte': '%s-01T00:00:00' % val,
                        'lte': '%s-31T23:59:59' % val,
                    }
                }
                filters.append(Q('range', **kw))
            search = search.query(functools.reduce(operator.or_, filters))
        return search

    def get_key(self, bucket):
        return bucket.get('key_as_string')

class DayHistogram (Facet):
    template = 'app/seeker/facets/year_histogram.html'

    def _get_aggregation(self, **extra):
        params = {
            'field': self.field,
            'interval': 'day',
            'format': 'yyyy-MM-dd',
            'min_doc_count': 1,
            'order': {'_key': 'desc'},
        }
        params.update(self.kwargs)
        params.update(extra)
        return A('date_histogram', **params)

    def apply(self, search, agg_name, aggs_stack, **extra):
        if agg_name in aggs_stack:
            aggs_tail = search.aggs[agg_name]
            for sub_agg_name in aggs_stack[agg_name][1:]:
                aggs_tail = aggs_tail.aggs[sub_agg_name]
            aggs_stack[agg_name].append(self.name)
            sub_agg_name = self.name
        else:
            aggs_tail = search
            aggs_stack[agg_name] = [agg_name]
            sub_agg_name = agg_name
        aggs_tail.aggs[sub_agg_name] = self._get_aggregation(**extra)
        return search

    def filter(self, search, values):
        if len(values) > 0:
            filters = []
            for val in values:
                kw = {
                    self.field: {
                        'gte': '%sT00:00:00' % val,
                        'lte': '%sT23:59:59' % val,
                    }
                }
                filters.append(Q('range', **kw))
            search = search.query(functools.reduce(operator.or_, filters))
        return search

    def get_key(self, bucket):
        return bucket.get('key_as_string')

class RangeFilter (Facet):
    template = 'app/seeker/facets/range.html'

    def apply(self, search, agg_name, aggs_stack, **extra):
        #params = {
        #    'field': self.field,
        #    'keyed': True,
        #    'ranges': [{'to': 25}, {'from':25, 'to': 50}, {'from':50, 'to': 75}, {'from':75}],
        #}
        params = {
            'field': self.field,
            'interval': 10,
        }
        params.update(self.kwargs)
        params.update(extra)
        search.aggs[self.name] = A('histogram', **params)
        return search

    def filter(self, search, values):
        if len(values) == 2:
            r = {}
            if values[0].isdigit():
                r['gte'] = values[0]
            if values[1].isdigit():
                r['lte'] = values[1]
            search = search.filter('range', **{self.field: r})
        return search
