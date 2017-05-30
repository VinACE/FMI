"""
Definition of api-views.
"""

from pandas import Series, DataFrame
from django.shortcuts import render
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
#from django.http import JsonResponse
from django.template import RequestContext
from django.core.files import File
from datetime import datetime
import json
import app.models as models

from .scrape_ds import *

platformseekers = {
    'Fragrantica'           : (models.PerfumeSeekerView, "search_pi"),
    'Market Intelligence'   : (models.PostSeekerView, "search_mi"),
    'Cosmetica'             : (models.PageSeekerView, "search_cosmetic"),
    'Feedly'                : (models.FeedlySeekerView, "search_feedly"),
    'Scent Emotion (Ingr)'  : (models.ScentemotionSeekerView, "search_scentemotion"),
    #'Scent Emotion (Studies)' : (models.StudiesSeekerView, "search_studies"),
    #'CI Surveys'            : (models.SurveySeekerView, "search_survey"),
    }



def platformsearch(request):
    results = {}
    keywords_q = request.GET['q']
    for dataset, seeker in platformseekers.items():
        seekerview = seeker[0]()
        using = seekerview.using
        index = seekerview.index
        #search = seekerview.document.search().index(index).using(using).extra(track_scores=True)
        search = seekerview.get_empty_search()
        if keywords_q:
            search = seekerview.get_search_query_type(search, keywords_q)
            results_count = search[0:0].execute().hits.total
            results[dataset] = {'count': results_count, 'url': seeker[1]}
    json_results = json.dumps(results)
    return HttpResponse(json_results, content_type='application/json')


def scrape_accords_api(request):
    accords_df_json = scrape_accords_json()
    return HttpResponse(accords_df_json, content_type='application/json')

def scrape_notes_api(request):
    notes_df_json = scrape_notes_json()
    return HttpResponse(notes_df_json, content_type='application/json')

def scrape_votes_api(request):
    votes_df_json = scrape_votes_json()
    return HttpResponse(votes_df_json, content_type='application/json')

def scrape_reviews_api(request):
    reviews_df_json = scrape_reviews_json()
    return HttpResponse(reviews_df_json, content_type='application/json')




