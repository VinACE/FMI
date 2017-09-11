from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse, QueryDict, Http404
from django.shortcuts import render, redirect
from django.template import loader, Context, RequestContext
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.generic import View
from elasticsearch_dsl.utils import AttrList, AttrDict
#from seeker.templatetags.seeker import seeker_format
from app.templatetags.seeker import seeker_format
from .mapping import DEFAULT_ANALYZER
import collections
import elasticsearch_dsl as dsl
import inspect
import json
import urllib
import re
import string
import numbers
from collections import OrderedDict
import pandas as pd
import numpy as np
import math
from scipy.stats import norm
import seeker.seekerview
import seeker.models

def get_fqa_values_respondents(fqav_df, question, answer, facet):
    values = []
    nr_respondents = 0
    for column in fqav_df.columns:
        if column[0] == question and column[1] == answer:
            values.append(column[2])
            nr_respondents = nr_respondents + fqav_df[column][facet]
    return values, nr_respondents

def get_fq_values_respondents(fqav_df, question, facet):
    values = []
    nr_respondents = 0
    for column in fqav_df.columns:
        if column[0] == question:
            values.append(column[2])
            nr_respondents = nr_respondents + fqav_df[column][facet]
    return values, nr_respondents

def answer_value_decode(answer_code):
    global qa

    answer_value = answer_code
    if type(answer_code) == str:
        first_code = answer_code.split()[0]
        if first_code.isdigit():
            answer_value = int(float(first_code))
    return answer_value

def stats(tile_df, dashboard):
    #questions = tile_df['q_field']
    stats_df = pd.DataFrame()
    corr_df = pd.DataFrame()

    facets = tile_df['facet_tile']
    f_index = np.unique(facets).tolist()
    chart_names = []
    qav_q_columns = []
    qav_a_columns = []
    qav_av_columns = []
    qa_q_columns = []
    qa_a_columns = []
    tile_df = tile_df[tile_df['y_field'] != 'Total']
    fqa_df = pd.DataFrame()
    for chart_name, db_chart in dashboard.items():
        if db_chart['chart_data'] != "correlation":
            continue
        for base_chart_name in db_chart['base']:
            chart_names.append(base_chart_name)
            base_chart = dashboard[base_chart_name]
            question = base_chart['X_facet']['field']
            answers = tile_df[tile_df['chart_name'] == base_chart_name]['x_field']
            answers = np.unique(answers).tolist()
            for answer in answers:
                qa_q_columns.append(question)
                qa_a_columns.append(answer)
                answer_values = tile_df[(tile_df['chart_name'] == base_chart_name) & (tile_df['x_field'] == answer)]['y_field']
                answer_values = np.unique(answer_values).tolist()
                for answer_value in answer_values:
                    qav_q_columns.append(question)
                    qav_a_columns.append(answer)
                    qav_av_columns.append(answer_value)
        if len(qav_q_columns) == 0:
            continue

        qav_columns = pd.MultiIndex.from_arrays([qav_q_columns, qav_a_columns, qav_av_columns], names=['questions', 'answers', 'values'])
        qa_columns = pd.MultiIndex.from_arrays([qa_q_columns, qa_a_columns], names=['questions', 'answers'])
        fqav_df = pd.DataFrame(0.0, columns=qav_columns, index=f_index)
        msk = [(chart_name in chart_names) for chart_name in tile_df['chart_name']]
        for facet, facet_df in tile_df.groupby(tile_df[msk]['facet_tile']):
            for idx, facet_s in facet_df.iterrows():
                f = facet_s['facet_tile']
                q = facet_s['q_field']
                a = facet_s['x_field']
                av = facet_s['y_field']
                count = facet_s['metric']
                fqav_df.loc [f, (q, a, av)] = count
        # aggregate to qa (fact) level
        fqa_df = pd.DataFrame(0.0, columns=qa_columns, index=f_index)
        for facet in f_index:
            for qav in fqav_df.columns:
                q = qav[0]
                a = qav[1]
                v = qav[2]
                question_field = q.replace('_', '.')
                fact = db_chart['facts'][question_field]
                total = 0
                if fact['value_type'] == 'boolean':
                    values, nr_respondents = get_fqa_values_respondents(fqav_df, q, a, facet)
                    for value in values:
                        value_code = answer_value_decode(value)
                        if value_code == "Yes":
                            value_code = 1
                        elif value_code == "No":
                            value_code = 0
                        count = fqav_df[(q, a, value)][facet]
                        total = total + value_code * count
                        if nr_respondents > 0:
                            percentile = (count * value_code) / nr_respondents
                        else:
                            percentile = (count * value_code)
                    fqa_df.loc [facet, (q, a)] = total
                    #fqa_df.loc [f, (q, a)] = percentile
                elif fact['value_type'] == 'ordinal':
                    values, nr_respondents = get_fq_values_respondents(fqav_df, q, facet)
                    for value in values:
                        value_code = answer_value_decode(value)
                        if type(value_code) == str:
                            try:
                                value_code = int(float(value_code))
                            except:
                                value_code = 0
                        count = fqav_df[q, value, value][facet]
                        total = total + value_code * count
                        if nr_respondents > 0:
                            percentile = count / nr_respondents
                        else:
                            percentile = count
                        fqa_df.loc [facet, (q, value)] = count
                        #fqa_df.loc [f, (q, a)] = percentile
                    mean = total / nr_respondents
                    #fqa_df.loc [f, (q, 'mean')] = mean

    if len(fqa_df.index) > 0:
        stats_df = fqa_df.describe().transpose()
        stats_df['question'] = [t[0] for t in stats_df.index]
        stats_df['answer'] = [t[1] for t in stats_df.index]
        corr_df = fqa_df.corr()
        corr_df['question'] = [t[0] for t in corr_df.index]
        corr_df['answer'] = [t[1] for t in corr_df.index]
    return stats_df, corr_df


def bind_tile_chart(tile_df, facet_tile_value, chart):
    X_facet = chart.db_chart['X_facet']
    X_field = X_facet['field']
    data = chart.db_chart['data']
    if len(data) > 0:
        categories = data[0]
        chart_name = chart.name
        q_field = X_field
        rownr = len(tile_df)
        for series in data[1:]:
            x_field = series[0]
            for ix in range(1, len(categories)):
                y_field = categories[ix]
                metric = series[ix]
                tile_df.loc[rownr] = [facet_tile_value, chart_name, q_field, x_field, y_field, metric]
                rownr = rownr + 1
    pass

def bind_tile(seekerview, tiles_select, tiles_d, facets_tile, charts, results, facets_keyword):
    hits = results.hits
    aggregations = results.aggregations
    tile_df = pd.DataFrame(columns=('facet_tile', 'chart_name', 'q_field', 'x_field', 'y_field', 'metric'))
    rownr = 0
    for chart_name, chart in charts.items():
        tiles_d[chart_name] = {}
        chart_data = chart.db_chart['chart_data']
        X_facet = chart.db_chart['X_facet']

        if facets_tile == None:
            tiles_select['All'] = []
            if chart_data == 'facet':
                chart.bind_facet(aggregations)
            elif chart_data == 'aggr':
                if 'aggr_name' in chart.db_chart:
                    aggr_name = chart.db_chart['aggr_name']
                    chart.bind_topline_aggr(aggr_name, aggregations, facets_keyword)
                else:
                    aggr_name = chart_name
                    chart.bind_aggr(chart_name, aggregations)
            elif chart_data == 'hits':
                chart.bind_hits(hits, facets_keyword)
            elif chart_data == 'topline':
                chart.bind_topline(hits, facets_keyword)
            else:
                chart.db_chart['data'] = []
            tiles_d[chart_name]['All'] = chart.db_chart['data']
            #bind_tile_chart(tile_df, 'All', chart)
        else:
            for facet_tile in facets_tile:
                tiles_select[facet_tile.label] = []
                agg_name = facet_tile.name + '_' + chart_name
                if agg_name in aggregations:
                    agg = aggregations[agg_name]
                    tiles = facet_tile.buckets(agg)
                    for facet_tile_value, tile in tiles.items():
                        if facet_tile_value not in tiles_select[facet_tile.label]:
                            tiles_select[facet_tile.label].append(facet_tile_value)
                        if chart_data == 'facet':
                            chart.bind_facet(tile)
                        elif chart_data == 'aggr':
                            if 'aggr_name' in chart.db_chart:
                                aggr_name = chart.db_chart['aggr_name']
                                chart.bind_topline_aggr(aggr_name, tile, facets_keyword)
                            else:
                                chart.bind_aggr(X_facet['field'], tile)
                        else:
                            chart.db_chart['data'] = []
                        tiles_d[chart_name][facet_tile_value] = chart.db_chart['data']
                        #bind_tile_chart(tile_df, facet_tile_value, chart)

    return tile_df

def tile_obsolete(seekerview, facets_tile, charts, results_tile):
    tile_df = pd.DataFrame(columns=('facet_tile', 'chart_name', 'q_field', 'x_field', 'y_field', 'metric'))
    tiles_select = {};
    rownr = 0
    for chart_name, chart in charts.items():
        chart_data = chart.db_chart['chart_data']
        if chart_data == 'topline':
            continue
        if chart_data == 'topline_base':
            continue
        if chart_data == 'hits':
            continue
        if chart_data == 'correlation':
            continue

        X_facet = chart.db_chart['X_facet']
        question_field = X_facet['field']
        answer_field = ''
        single = False
        nested = False
        if 'Y_facet' not in chart.db_chart:
            Y_facet = None
            single = True
        else:
            Y_facet = chart.db_chart['Y_facet']
            if Y_facet['field'] == "answer":
                nested = True
                answer_field = 'answer'
            answer_field = Y_facet['field']

        if len(facets_tile) == 0:
            facets_tile = [seeker.TermsFacet("All", label = "All")]
        for facet_tile in facets_tile:
            tiles = []
            if facet_tile.label != "All":
                tiles_select[facet_tile.label] = []
                agg_name = facet_tile.name + '_' + chart_name
                if agg_name in results_tile.aggregations:
                    # this also converts AttrDict and AttrList to dict and list types !!
                    tile_aggr = results_tile.aggregations[agg_name].to_dict()
                    tiles = tile_aggr['buckets']
            else:
                agg_name = question_field
                if agg_name in results_tile.aggregations:
                    # this also converts AttrDict and AttrList to dict and list types !!
                    tile = results_tile.aggregations.to_dict()
                    tiles = [tile]
            for ti in range(0, len(tiles)):
                tile = tiles[ti]
                if facet_tile.label != "All":
                    facet_tile_value = tile['key']
                    if facet_tile_value not in tiles_select[facet_tile.label]:
                        tiles_select[facet_tile.label].append(facet_tile_value)
                else:
                    facet_tile_value = 'All'
                if nested:
                    questions = tile[question_field]['question']['buckets']
                else:
                    questions = tile[question_field]['buckets']
                if type(questions) == AttrList or type(questions) == list:
                    for qi in range(0, len(questions)):
                        question = questions[qi]
                        question_value = question[X_facet['key']]
                        question_count = question[X_facet['metric']]
                        if type(question_value) == int:
                            question_value = "{0:d}".format(question_value)
                        tile_df.loc[rownr] = [facet_tile_value, chart_name, question_field, question_value, "Total", question_count]
                        rownr = rownr + 1
                        if not single and answer_field in question:
                            answers = question[answer_field]['buckets']
                            if type(answers) == dict:
                                for answer_value in answers:
                                    count = answers[answer_value]['doc_count']
                                    tile_df.loc[rownr] = [facet_tile_value, chart_name, question_field, question_value, answer_value, count]
                                    rownr = rownr + 1
                            else:
                                for ai in range(0, len(answers)):
                                    answer = answers[ai]
                                    answer_value = answer['key']
                                    if type(answer_value) == int:
                                        answer_value = "{0:d}".format(answer_value)
                                    count = answer['doc_count']
                                    tile_df.loc[rownr] = [facet_tile_value, chart_name, question_field, question_value, answer_value, count]
                                    rownr = rownr + 1
                        else:
                            count = question['doc_count']
                            answer_value = question_value
                            tile_df.loc[rownr] = [facet_tile_value, chart_name, question_field, question_value, answer_value, count]
                            rownr = rownr + 1
                if type(questions) == AttrDict or type(questions) == dict:
                    for question_value, answer in questions.items():
                        if single:
                            count = answer['doc_count']
                            tile_df.loc[rownr] = [facet_tile_value, chart_name, question_field, question_value, "Total", count]
                            rownr = rownr + 1
    return tile_df, tiles_select 


 
def bucket_coor(key_bucket, buckets, db_facet):
    if type(buckets) == AttrList:
        bucket = key_bucket
        key = bucket[db_facet['key']]
        metric = bucket[db_facet['metric']]
    else:
        key = key_bucket
        bucket = buckets[key]
        metric = bucket[db_facet['metric']]
    return key, metric, bucket


# aggs : { <
#GET survey/_search
#{
#  "size": 0,
#  "aggs": {
#    "regions": {
#      "terms": {
#        "field": "regions.keyword"
#      },
#      "aggs": {
#        "city": {
#          "terms": {
#            "field": "city.keyword"
#          },
#          "aggs": {
#            "children": {
#              "nested": {
#                "path": "children"
#              },
#              "aggs": {
#                "question": {
#                  "terms": {
#                    "field": "children.question.keyword",
#                    "size": 20,
#                    "min_doc_count": 1
#                  },
#                  "aggs": {
#                    "answer": {
#                      "terms": {
#                        "field": "children.answer.keyword",
#                        "size": 20,
#                        "min_doc_count": 1
#                      }
#                    }
#                  }
#                }
#              }
#            }
#          }
#        }
#      }
#    }
#  }
#}

def facet_aggregate(facet, charts):
    # Aggregate a facet when it occurs in a chart (storyboard) or it is visible on the sreen
    if facet.visible_pos > 0:
        return True;
    for chart_name, chart in charts.items():
        if chart['chart_data'] == 'facet':
            if chart['X_facet']['field'] == facet.field:
                return True;
            if 'Y_facet' in chart:
                if chart['Y_facet']['field'] == facet.field:
                    return True;
    return False


#
# Google Charts are used to render the Chart object
# A Goolge Chart takes a DataTable as input. This DataTable can be constructed as a JavaScript data parameter.
# This data statement defines the table as an object with cols, rows and p attributes.
# A cols is an array with col object. A col object has an id, label, type, pattern and p (style) attribute.
# A rows is an array of cell objects. Each cell has an v (value), f (formatted value) and p (stype) attribute.
# Example of a p attribute: p:{style: 'border: 1px solid green;'}
#

class Chart(object):
    name = ""
    chart_type = ""
    db_chart = None
    decoder = None
    get_facet_by_field_name = None

    def __init__(self, name, dashboard, get_facet_by_field_name, decoder=None, **kwargs):
        self.name = name
        self.chart_type = dashboard[name]['chart_type']
        self.db_chart = dashboard[name]
        self.get_facet_by_field_name = get_facet_by_field_name
        self.decoder = decoder
        self.db_chart['data'] = []
        if 'key' not in self.db_chart['X_facet']:
            self.db_chart['X_facet']['key'] = "key"
        if 'metric' not in self.db_chart['X_facet']:
            self.db_chart['X_facet']['metric'] = "doc_count"
        if 'Y_facet' in self.db_chart:
            if 'key' not in self.db_chart['Y_facet']:
                self.db_chart['Y_facet']['key'] = "key"
            if 'metric' not in self.db_chart['Y_facet']:
                self.db_chart['Y_facet']['metric'] = "doc_count"

    def bind_facet(self, aggregations):
        self.db_chart['data'] = None
        self.db_chart['data'] = []
        X_facet = self.db_chart['X_facet']
        X_field = X_facet['field']
        X_label = X_facet['label']
        x_total = True
        sub_total = False
        if 'total' in X_facet:
            x_total = X_facet['total']
        if 'Y_facet' in self.db_chart:
            Y_facet = self.db_chart['Y_facet']
            Y_field = self.db_chart['Y_facet']['field']
            Y_label = Y_facet['label']
        else:
           Y_facet = None
           Y_field = ""
           Y_Label = X_label
        if X_field in aggregations:
            agg = aggregations[X_field]
            if 'question' in agg:
                agg = agg['question']
            #categories = [X_label]
            dt_index = []
            dt_columns = [X_label]
            y_start = 1
            dt_columns.append("Total")
            y_start = y_start + 1
            dt = pd.DataFrame(0.0, columns=dt_columns, index=[0])
            # next fill the series for the categories
            rownr = 0
            for key_bucket in agg.buckets:
                X_key, X_metric, bucket = bucket_coor(key_bucket, agg.buckets, self.db_chart['X_facet'])
                #series = [0] * len(categories)
                #series[0] = X_key
                dt.loc[rownr, X_label] = X_key
                dt_index.append(X_key)
                dt.loc[rownr, "Total"] = X_metric
                if Y_field != "" and Y_field in bucket:
                    subagg = bucket[Y_field]
                    sub_total = True
                    for key_subbucket in subagg.buckets:
                        Y_key, Y_metric, subbucket = bucket_coor(key_subbucket, subagg.buckets, self.db_chart['Y_facet'])
                        if self.decoder:
                            Y_key = self.decoder(X_key, Y_key)
                        if type(Y_key) == int:
                            Y_key = "{0:d}".format(Y_key)
                        #series[categories.index(Y_key)] = Y_metric
                        if Y_key not in dt_columns:
                            inserted = False
                            for i in range(y_start, len(dt_columns)):
                                if Y_key < dt_columns[i]:
                                    dt_columns.insert(i, Y_key)
                                    dt.insert(i, Y_key, pd.Series(0, index=dt_index))
                                    inserted = True
                                    break
                            if not inserted:
                                dt_columns.append(Y_key)
                        dt.loc[rownr, Y_key] = Y_metric
                #self.db_chart['data'].append(series)
                rownr = rownr + 1
            dt.fillna(0, inplace=True)
            if sub_total == True and x_total == False:
                dt_columns.remove('Total')
                del dt['Total']
            self.db_chart['data'].append(dt_columns)
            # remove Total only when sub_totals exists
            for ix, row in dt.iterrows():
                self.db_chart['data'].append(row.tolist())


    def bind_aggr(self, agg_name, aggregations):
        self.db_chart['data'] = None
        self.db_chart['data'] = []
        X_facet = self.db_chart['X_facet']
        xfacet = self.get_facet_by_field_name(X_facet['field'])
        X_field = X_facet['field']
        X_label = X_facet['label']
        x_total = True
        sub_total = False
        if 'total' in X_facet:
            x_total = X_facet['total']
        if 'Y_facet' in self.db_chart:
            Y_facet = self.db_chart['Y_facet']
            yfacet = self.get_facet_by_field_name(Y_facet['field'])
            Y_field = self.db_chart['Y_facet']['field']
            Y_label = Y_facet['label']
        else:
            Y_facet = None
            Y_field = ""
            Y_Label = X_label
            yfacet = None
        # Aggregation is an AttrDict
        # Buckets is an AttrList for Terms and AttrDict for Keywords. The facet.buckets method returns alwasy a OrderedDict
        # Bucket is an AttrDict and can act as a Sub-Aggregation
        if agg_name in aggregations:
            agg = aggregations[agg_name]
            buckets = xfacet.buckets(agg)
            dt_index = []
            dt_columns = [X_label]
            y_start = 1
            dt_columns.append("Total")
            y_start = y_start + 1
            dt = pd.DataFrame(0.0, columns=dt_columns, index=[0])
            # next fill the series for the categories
            modes = ['sizing_', 'filling_']
            for mode in modes:
                if mode == 'filling_':
                    dt = pd.DataFrame(0.0, columns=dt_columns, index=dt_index)
                rownr = 0
                for X_key, bucket in buckets.items():
                    # skip and map categories
                    X_key = xfacet.get_category(X_key, bucket, X_facet)
                    if X_key == None:
                        continue
                    X_metric = xfacet.get_metric(bucket)
                    if mode == 'sizing_':
                        dt_index.append(X_key)
                    if mode == 'filling_':
                        dt.loc[X_key, X_label] = X_key
                        dt.loc[X_key, "Total"] = X_metric
                    # loop through the different values for this category, normally only one
                    xvalbuckets = xfacet.valbuckets(bucket)
                    for X_value_key, xvalbucket in xvalbuckets.items():
                        # skip and map values
                        X_value_key = xfacet.get_value_key(X_value_key, xvalbucket, X_facet)
                        if X_value_key == None:
                            continue
                        if Y_field == "" or Y_field not in xvalbucket:
                            Y_metric = xfacet.get_metric(xvalbucket)
                            if X_value_key not in dt_columns:
                                sub_total = True
                                if mode == 'sizing_':
                                    dt_columns.append(X_value_key)
                            if mode == 'filling_':
                                dt.loc[X_key, X_value_key] = Y_metric
                        else:
                            subagg = xvalbucket[Y_field]
                            subbuckets = yfacet.buckets(subagg)
                            for Y_key, subbucket in subbuckets.items():
                                # skip and map answers, categories
                                if 'answers' in Y_facet:
                                    if Y_key not in Y_facet['answers'] and len(Y_facet['answers']) > 0:
                                        continue
                                Y_key = yfacet.get_category(Y_key, subbucket, Y_facet)
                                if Y_key == None:
                                    continue
                                sub_total = True
                                Y_metric = yfacet.get_metric(subbucket)
                                # check whether Y facet has subbuckets (multiple values)
                                # loop through the different values for this category, normally only one
                                Y_metric = 0
                                yvalbuckets = yfacet.valbuckets(subbucket)
                                for Y_value_key, yvalbucket in yvalbuckets.items():
                                    # skip and map values
                                    Y_value_key = yfacet.get_value_key(Y_value_key, yvalbucket, Y_facet)
                                    if Y_value_key == None:
                                        continue
                                    V_metric = xfacet.get_metric(yvalbucket)
                                    Y_metric = Y_metric + V_metric
                                    #yes_count = 0
                                    #for value_bucket in subbucket.buckets:
                                    #    V_key, V_metric, subvaluebucket = bucket_coor(value_bucket, subbucket.buckets, self.db_chart['Y_facet'])
                                    #    if self.decoder:
                                    #        V_key = self.decoder(Y_key, V_key)
                                    #    if type(V_key) == int:
                                    #        V_key = "{0:d}".format(Y_key)
                                    #    if V_key in Y_facet['values']:
                                    #        yes_count = yes_count + V_metric
                                    #Y_metric = yes_count
                                if Y_key not in dt_columns:
                                    if mode == 'sizing_':
                                        inserted = False
                                        zero = pd.Series(0.0, index=dt.index)
                                        for i in range(y_start, len(dt_columns)):
                                            if Y_key < dt_columns[i]:
                                                dt_columns.insert(i, Y_key)
                                                dt.insert(i, Y_key, zero)
                                                inserted = True
                                                break
                                        if not inserted:
                                            dt_columns.append(Y_key)
                                            dt[Y_key] = zero
                                if mode == 'filling_':
                                    #dt.loc[rownr, Y_key] = dt.loc[rownr, Y_key] + Y_metric
                                    dt.loc[X_key, Y_key] = Y_metric
                    rownr = rownr + 1

            dt.fillna(0, inplace=True)
            if sub_total == True and x_total == False:
                dt_columns.remove('Total')
                del dt['Total']
            transpose = False
            if 'transpose' in self.db_chart:
                transpose = self.db_chart['transpose']
            if transpose:
                # first column contains the labels, remove this column before transpose and add it again after transpose
                del dt[X_label]
                dt = dt.transpose()
                dt_trans_columns = [Y_label]
                dt_trans_columns.extend(dt_index)
                dt_trans_index = dt_columns[1:]
                dt.insert(0, Y_label, dt_trans_index)
                dt_columns = dt_trans_columns
            self.db_chart['data'].append(dt_columns)
            for ix, row in dt.iterrows():
                self.db_chart['data'].append(row.tolist())

    def bind_topline_aggr(self, aggr_name, aggregations, facets_keyword=None):
        self.db_chart['data'] = None
        self.db_chart['data'] = []
        X_facet = self.db_chart['X_facet']
        X_field = X_facet['field']
        X_label = X_facet['label']
        hed_lines = X_facet['lines'][X_field]
        Y_facet = self.db_chart['Y_facet']
        Y_field = Y_facet['field']
        Y_label = Y_facet['label']
        self.bind_aggr(aggr_name, aggregations)
        data = self.db_chart['data']
        if len(data) == 0:
            return
        # X-facet in rows, Y-facet in columns
        self.db_chart['data'] = []

        benchmark = []
        if facets_keyword:
            for facet_keyword in facets_keyword:
                if facet_keyword.keywords_k != '' and facet_keyword.keywords_k != []:
                    benchmark.append(facet_keyword.keywords_k)

        dt_index = []
        dt_columns = [X_label]
        for col in data[0][1:]:
            if col == 'Total':
                continue
            IPC = col.strip()
            # benchmark will be the first column(s)
            if IPC in benchmark:
                dt_columns.insert(1, IPC)
            else:
                dt_columns.append(IPC)
        if len(benchmark) == 0:
            dt_columns.insert(1, 'Average')
        dt_index = list(hed_lines.keys())
        dt_index.sort()
        dt = pd.DataFrame(0.0, columns=dt_columns, index=dt_index)
        dt[X_label] = dt_index


        # scan through the rows to populate df
        Y_total = 0
        hit_count = 0
        Y_benchmark = 0
        benchmark_count = 0
        cand_topline = {}

        for ix in range(1, len(data[0])):
            IPC = data[0][ix].strip()
            if IPC == 'Total':
                continue
            sum_scores = 0
            nr_resp = 0
            for row in data[1:]:
                answer = row[0]
                try:
                    answer_code = int(float(answer.split(' ')[0]))
                except:
                    if isinstance(answer, numbers.Real):
                        answer_code = int(answer)
                    else:
                        answer_code = 0
                for hed_line, answers in hed_lines.items():
                    if answer_code in answers:
                        dt.loc[hed_line, IPC] = dt.loc[hed_line, IPC] + row[ix]
                if answer_code > 0:
                    sum_scores = sum_scores + answer_code * row[ix]
                    nr_resp = nr_resp + row[ix]
            for hed_line, answers in hed_lines.items():
                if 'mean' in answers:
                    if nr_resp > 1:
                        Y_metric = sum_scores / nr_resp
                    else:
                        Y_metric = sum_scores
                    dt.loc[hed_line, IPC] = Y_metric
                    Y_total = Y_total + Y_metric
                    hit_count = hit_count + 1

        if len(benchmark) == 0:
            for hed in dt.index:
                sum = dt.ix[hed][1:].sum()
                avg = sum / (len(dt._ix[hed]) - 2)
                dt.loc[hed, 'Average'] = avg
        if ('q-mean' in X_facet):
            if hit_count == 0:
                Y_metric= Y_total
            else:
                Y_metric = Y_total / hit_count
            X_key = "Q-Mean"
            dt_index.append(X_key)
            dt.loc[X_key, X_label] = X_key
            rownr = 0
            for colnr in range(1, len(dt_columns)):
                dt.loc[X_key, dt_columns[colnr]] = Y_metric
            if 'series' in self.db_chart:
                if 'average' in self.db_chart['series']:
                    self.db_chart['series'][dt_columns.index(X_key)] = {"type": 'line'}
                    del self.db_chart['series']['average']

        # prepare for the setProperty formatter. Capture the cells for which a win95, win90, win80, lose95, lose90, lose80
        # className have to be set. This win/lose is set based on the first columns, which contains either the benchmark
        # or the average.
        # The cells in a DataTable start at rownr 0 (this not the header) and at colnr 0 (this is the label)
        if 'formatter' in self.db_chart:
            if 'setProperty' in self.db_chart['formatter']:
                winlose = []
                for rownr in range(0, len(dt)):
                    line = dt.ix[rownr]
                    avg = line[1]
                    var = 0
                    for colnr in range(2, len(line)):
                        var = var + abs(line[colnr] - avg)
                    stddev = math.sqrt(var)
                    int95 = norm.interval(0.95, avg, stddev)
                    int90 = norm.interval(0.90, avg, stddev)
                    int80 = norm.interval(0.80, avg, stddev)
                    winlose.append([rownr, 1, 'className', 'benchmark'])
                    for colnr in range(2, len(line)):
                        if line[colnr] >= int95[1]:
                            winlose.append([rownr, colnr, 'className', 'win95'])
                        elif line[colnr] >= int90[1]:
                            winlose.append([rownr, colnr, 'className', 'win90'])
                        elif line[colnr] >= int80[1]:
                            winlose.append([rownr, colnr, 'className', 'win80'])
                        elif line[colnr] <=int95[0]:
                            winlose.append([rownr, colnr, 'className', 'lose95'])
                        elif line[colnr] <=int90[0]:
                            winlose.append([rownr, colnr, 'className', 'lose90'])
                        elif line[colnr] <=int80[0]:
                            winlose.append([rownr, colnr, 'className', 'lose80'])
                self.db_chart['formatter']['setProperty'] = winlose

        transpose = False
        if 'transpose' in self.db_chart:
            transpose = self.db_chart['transpose']
        if transpose:
            # first column contains the labels, remove this column before transpose and add it again after transpose
            del dt[X_label]
            dt = dt.transpose()
            dt_trans_columns = [Y_label]
            dt_trans_columns.extend(dt_index)
            dt_trans_index = dt_columns[1:]
            dt.insert(0, Y_label, dt_trans_index)
            dt_columns = dt_trans_columns

        dt.fillna(0, inplace=True)
        self.db_chart['data'].append(dt_columns)
        for ix, row in dt.iterrows():
            self.db_chart['data'].append(row.tolist())


    def bind_hits(self, hits, facets_keyword=None):
        self.db_chart['data'] = None
        self.db_chart['data'] = []
        X_facet = self.db_chart['X_facet']
        X_field = X_facet['field']
        X_label = X_facet['label']
        x_total = True
        if 'total' in X_facet:
            x_total = X_facet['total']
        if 'Y_facet' in self.db_chart:
            Y_facet = self.db_chart['Y_facet']
            Y_field = Y_facet['field']
            Y_label = Y_facet['label']
        else:
           Y_facet = None
           Y_field = None
           Y_Label = X_label

        benchmark = []
        if facets_keyword:
            for facet_keyword in facets_keyword:
                benchmark.append(facet_keyword.keywords_k)

        # next fill the series for the categories
        Y_total = 0
        hit_count = 0
        Y_benchmark = 0
        benchmark_count = 0
        dt_index = []
        dt_columns = [X_label]
        if x_total:
            dt_columns.append("Total")
        dt = pd.DataFrame(0.0, columns=dt_columns, index=[0])
        rownr = 0
        for hit in hits.hits:
            X_key = hit['_source'][X_field]
            #series = [0] * len(categories)
            #series[0] = X_key
            dt.loc[rownr, X_label] = X_key
            dt_index.append(X_key)
            #if x_total:
            #    series[1] = 1
            if Y_facet:
                Y_key = hit['_source'][Y_field]
                if type(Y_key) == list:
                    Y_key_nested = Y_key
                    Y_nested = 0
                    nested_count = 0
                    for Y_value in Y_key_nested:
                        Y_key = Y_value['val']
                        Y_metric = Y_value[Y_facet['metric']]
                        if 'answers' in Y_facet:
                            # in case anaswers is empty, add all y values
                            if Y_value['val'] in Y_facet['answers'] or len( Y_facet['answers']) == 0:
                                Y_nested = Y_nested + Y_metric
                                nested_count = nested_count + 1
                                if self.decoder:
                                    Y_key = self.decoder(X_key, Y_key)
                                if type(Y_key) == int:
                                    Y_key = "{0:d}".format(Y_key)
                                #series[categories.index(Y_key)] = Y_metric
                                if Y_key not in dt_columns:
                                    dt_columns.append(Y_key)
                                dt.loc[rownr, Y_key] = Y_metric
                        else:
                            # in case the answer is scaled, starts with a number, use weight factor for average
                            try:
                                weight = int(float(Y_key.split(' ')[0]))
                            except:
                                weight = 1
                            Y_nested = Y_nested + Y_metric * weight
                            nested_count = nested_count + 1
                    if nested_count == 0:
                        Y_metric= Y_nested
                    else:
                        Y_metric = Y_nested / nested_count
                    if 'answers' not in Y_facet:
                        Y_key = Y_facet['label']
                        #series[categories.index(Y_key)] = Y_metric
                        dt.loc[rownr, Y_key] = Y_metric
                        if Y_key not in dt_columns:
                            dt_columns.append(Y_key)
                    elif 'a-mean' in Y_facet:
                        if Y_facet['a-mean'] == True:
                            Y_key = "A-Mean"
                            #series[categories.index(Y_key)] = Y_metric
                            dt.loc[rownr, Y_key] = Y_metric
                            if Y_key not in dt_columns:
                                dt_columns.append(Y_key)
                            if 'series' in self.db_chart:
                                if 'average' in self.db_chart['series']:
                                    self.db_chart['series'][dt_columns.index(Y_key)] = {"type": 'line'}
                                    del self.db_chart['series']['average']
                else:
                    if type(Y_key) == str:
                        try:
                            Y_metric = float(Y_key.split(' ')[0])
                        except:
                            Y_metric = 0
                    else:
                        Y_metric = hit['_source'][Y_field]
                    Y_key = Y_facet['label']
                    #series[categories.index(Y_key)] = Y_metric
                    dt.loc[rownr, Y_key] = Y_metric
                    if Y_key not in dt_columns:
                        dt_columns.append(Y_key)
            Y_total = Y_total + Y_metric
            hit_count = hit_count + 1
            if X_key in benchmark:
                Y_benchmark = Y_benchmark + Y_metric
                benchmark_count = benchmark_count + 1
            #self.db_chart['data'].append(series)
            rownr = rownr + 1
        if ('q-mean' in Y_facet):
            if hit_count == 0:
                Y_metric= Y_total
            else:
                Y_metric = Y_total / hit_count
            Y_key = "Q-Mean"
            rownr = 0
            #for series in self.db_chart['data']:
            #    series[categories.index(Y_key)] = Y_metric
            for rownr in range(0, len(dt)):
                dt.loc[rownr, Y_key] = Y_metric
                if Y_key not in dt_columns:
                    dt_columns.append(Y_key)
                rownr = rownr + 1
            if 'series' in self.db_chart:
                if 'average' in self.db_chart['series']:
                    self.db_chart['series'][dt_columns.index(Y_key)] = {"type": 'line'}
                    del self.db_chart['series']['average']
        if len(benchmark) > 0:
            if benchmark_count == 0:
                Y_metric= Y_benchmark
            else:
                Y_metric = Y_benchmark / benchmark_count
            Y_key = "Benchmark"
            rownr = 0
            #for series in self.db_chart['data']:
            #    series[categories.index(Y_key)] = Y_metric
            for rownr in range(0, len(dt)):
                dt.loc[rownr, Y_key] = Y_metric
                if Y_key not in dt_columns:
                    dt_columns.append(Y_key)
                rownr = rownr + 1
            # replace average and benchmark for combobox with real position
            if 'series' in self.db_chart:
                if 'series' in self.db_chart:
                    if 'benchmark' in self.db_chart['series']:
                        self.db_chart['series'][categories.index(Y_key)] = {"type": 'line'}
                        del self.db_chart['series']['benchmark']

        #if len(self.db_chart['data']) > 0:
        #    self.db_chart['data'].insert(0, categories)
        transpose = False
        if 'transpose' in self.db_chart:
            transpose = self.db_chart['transpose']
        if transpose:
            # first column contains the labels, remove this column before transpose and add it again after transpose
            del dt[X_label]
            dt = dt.transpose()
            dt_trans_columns = [Y_label]
            dt_trans_columns.extend(dt_index)
            dt_trans_index = dt_columns[1:]
            dt.insert(0, Y_label, dt_trans_index)
            dt_columns = dt_trans_columns

        dt.fillna(0, inplace=True)
        self.db_chart['data'].append(dt_columns)
        for ix, row in dt.iterrows():
            self.db_chart['data'].append(row.tolist())

    def _nested_box(self, nestedlist, values):
        prc = 0
        for item in nestedlist:
            try:
                item_code = int(float(item['val'].split(' ')[0]))
            except:
                item_code = item['val']
            for value in values:
                if item_code == value:
                    prc = prc + item['prc']
        return prc

    def _nested_mean(self, nestedlist):
        prc = 0
        if len(nestedlist) > 0:
            for item in nestedlist:
                try:
                    weight = int(float(item['val'].split(' ')[0]))
                except:
                    weight = 1
                prc = prc + item['prc'] * weight
            prc = prc / len(nestedlist)
        return prc


    def bind_topline(self, hits, facets_keyword=None):
        self.db_chart['data'] = None
        self.db_chart['data'] = []
        X_facet = self.db_chart['X_facet']
        X_fields = X_facet['fields']
        Y_facet = self.db_chart['Y_facet']
        Y_field = Y_facet['field']

        benchmark = []
        if facets_keyword:
            for facet_keyword in facets_keyword:
                benchmark.append(facet_keyword.keywords_k)

        topline_columns = []
        for hit in hits.hits:
            IPC = hit['_source'][Y_field]
            # benchmark will be the first column(s)
            if IPC in benchmark:
                topline_columns.insert(0, IPC)
            else:
                topline_columns.append(IPC)
        topline_index = ['Hedonics Mean', 'Hedonics Excellent', 'Hedonics Top2', 'Hedonics Top3', 'Hedonics Bottom2']
        topline_df = pd.DataFrame(0.0, columns=topline_columns, index=topline_index)

        # scan through the hits to populate df
        Y_total = 0
        hit_count = 0
        Y_benchmark = 0
        benchmark_count = 0
        cand_topline = {}
        for hit in hits.hits:
            IPC = hit['_source'][Y_field]
            hedonics = hit['_source']['hedonics']
            Y_nested = self._nested_mean(hedonics)
            topline_df.loc['Hedonics Mean', IPC] = Y_nested
            topline_df.loc['Hedonics Excellent', IPC] = self._nested_box(hedonics, [7])
            topline_df.loc['Hedonics Top2', IPC] = self._nested_box(hedonics, [7, 6])
            topline_df.loc['Hedonics Top3', IPC] = self._nested_box(hedonics, [7, 6, 5])
            topline_df.loc['Hedonics Bottom2', IPC] = self._nested_box(hedonics, [2, 1])
            Y_total = Y_total + Y_nested
            hit_count = hit_count + 1

        for ix in topline_df.index:
            series = [ix]
            series.extend(topline_df.ix[ix].tolist())
            self.db_chart['data'].append(series)

        if len(self.db_chart['data']) > 0:
            categories = ['Questions']
            categories.extend(topline_columns)
            self.db_chart['data'].insert(0, categories)

    def bind_correlation(self, stats_df, corr_df):
        # The data will be loaded in google_chart arrayToDataTable format
        # This means columns=series and rows=categories.
        # First Row are the column=series headers, followed by the different categories
        # First Column are the category names followed by the serie values
        self.db_chart['data'] = None
        self.db_chart['data'] = []
        X_facet = self.db_chart['X_facet']
        X_field = X_facet['field']
        # First row
        row = [X_facet['label']['category']]
        for col in X_field:
            if col in stats_df.columns:
                row.append(X_facet['label'][col])
        self.db_chart['data'].append(row)
        # Category rows
        for ix, stats_s in stats_df.iterrows():
            # First column
            row = [ix[0]]
            for col in X_field:
                # Series columns
                if col in stats_df.columns:
                    row.append(stats_s[col])
            self.db_chart['data'].append(row)
        pass


    def json(self):
        return json.dumps({'chart_type': self.chart_type, 'data': self.db_chart['data']})



def is_common(ngram):
    commonwords = [
        'the', 'be', 'and', 'of', 'a', 'in', 'to', 'have', 'it',
        'i', 'that', 'for', 'you', 'he', 'with', 'on', 'do', 'say', 'this',
        'they', 'us', 'an', 'at', 'but', 'we', 'his', 'from', 'that', 'not',
        'by', 'she', 'or', 'as', 'what', 'go', 'their', 'can', 'who', 'get',
        'if', 'would', 'her', 'all', 'my', 'make', 'about', 'know', 'will',
        'as', 'up', 'one', 'time', 'has', 'been', 'there', 'year', 'so',
        'think', 'when', 'which', 'then', 'some', 'me', 'people', 'take',
        'out', 'into', 'just', 'see', 'him', 'your', 'come', 'could', 'now',
        'than', 'like', 'other', 'how', 'then', 'its', 'our', 'two', 'more',
        'these', 'want', 'way', 'look', 'first', 'also', 'new', 'because',
        'day', 'more', 'use', 'no', 'man', 'find', 'here', 'thing', 'give', 
        'many', 'well'
        ]
    for word in ngram:
        if word in commonwords:
            return True
    return False

def clean_input(input):
    input = re.sub('\n+', " ", input)       #replace nl with a space
    input = re.sub('\[[0-9]*\]', "", input) #discard citation marks
    input = re.sub(' +', " ", input)        #replace multiple spaces with a sigle space
    input = bytes(input, "UTF-8")           #remove unicode characters
    input = input.decode("ascii", "ignore")
    input = input.split(' ')
    words = []
    for item in input:
        item = item.strip(string.punctuation)
        if len(item) > 1 or (item.lower() == 'a' or item.lower() == 'i'):
            words.append(item)
    return words


def get_ngrams(input, n):
    input = clean_input(input)
    output = {}
    for i in range(len(input)-n+1):
        newngram = input[i:i+n]
        if not is_common(newngram):
            newngram = " ".join(newngram)
            if newngram in output:
                output[newngram] = output[newngram] + 1
            else:
                output[newngram] = 1
    ngrams = OrderedDict(sorted(output.items(), key=lambda t: t[1], reverse=True))
    return ngrams