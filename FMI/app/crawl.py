
from datetime import datetime
from datetime import time
from datetime import timedelta
from django.core.files import File
import glob, os
import pickle
import urllib
import requests
from urllib.parse import urlparse
import re
from requests_ntlm import HttpNtlmAuth
from pandas import Series, DataFrame
import pandas as pd
from bs4 import BeautifulSoup

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.connections import connections
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk
import seeker
import app.models as models
import app.elastic as elastic
import app.survey as survey


class Crawler:
    site = ''
    pages = set()
    bulk_data = []

    def __init__(self, site):
        self.site = site

    def scrape(self, url):
        try:
            print("Scrape: scraping url ", url)
            html = urllib.request.urlopen(url)
            bs = BeautifulSoup(html.read(), "lxml")
            [script.decompose() for script in bs("script")]
        except:
            print("Scrape: could not open url ", url)
        return bs

    def get_pagination_links(self, sub_site):
        include_url = urlparse(sub_site).scheme+"://"+urlparse(sub_site).netloc
        links = set()
        url = sub_site
        page_nr = 0
        page_size = 10
        link_count = 0
        while url != None and link_count < 100:
            bs = self.scrape(url)
            box_1_tag = bs.find("div", class_="box_1")
            for link_tag in box_1_tag.findAll("a", href=re.compile("^(/|.*"+include_url+")")):
                if link_tag.attrs['href'] is not None:
                    if link_tag.attrs['href'] not in links:
                        if link_tag.attrs['href'].startswith('/'):
                            link = include_url+link_tag.attrs['href']
                        else:
                            link = link_tag.attrs['href']
                        links.add(link)
                        link_count = link_count + 1
            result_count_tag = bs.find("span", class_="result_count")
            if result_count_tag != None:
                result_count_list = result_count_tag.text.split()
                result_count = int(float(result_count_list[4]))
            else:
                result_count = page_size
            navigation_tag = bs.find(id="navigation")
            if navigation_tag != None:
                next_tag = navigation_tag.find("span", class_="next")
                if next_tag != None:
                    next_url = include_url + next_tag.find("a").attrs['href']
                else:
                    next_url = None
            else:
                page_nr = page_nr + 1
                if page_nr * page_size > result_count:
                    next_url = None
                else:
                    next_url = sub_site + '/(offset)/{}'.format(page_nr)
            url = next_url
        return links

    def get_internal_links(self, url, bs):
        include_url = urlparse(url).scheme+"://"+urlparse(url).netloc
        links = set()
        for link_tag in bs.findAll("a", href=re.compile("^(/|.*"+include_url+")")):
            if link_tag.attrs['href'] is not None:
                if link_tag.attrs['href'] not in links:
                    if link_tag.attrs['href'].startswith('/'):
                        link = include_url+link_tag.attrs['href']
                    else:
                        link = link_tag.attrs['href']
                    links.add(link)
        return links

    def get_external_links(self, url, bs):
        include_url = urlparse(url).scheme+"://"+urlparse(url).netloc
        links = set()
        for link_tag in bs.findAll("a", href=re.compile("^(/|.*"+include_url+")")):
            if link_tag.attrs['href'] is not None:
                if link_tag.attrs['href'] not in links:
                    if link_tag.attrs['href'].startswith('/'):
                        links.append(include_url+link_tag.attrs['href'])
                    else:
                        link_tag.append(link.attrs['href'])
        return links

    def push_to_index(self, url, bs):
        id = url
        site = urlparse(url).netloc.split('.')[1]
        sub_site = urlparse(url).path.split('/')
        sub_site = '-'.join(sub_site[1:-1])
        if sub_site == '':
            sub_site = 'Home'
        pagemap             = models.PageMap()

        pagemap.page_id     = id
        pagemap.site        = site
        pagemap.sub_site    = sub_site
        pagemap.url         = url

        # get posted date
        try:
            pagemap.posted_date = datetime.today()
            author_info_tag = bs.find("div", class_="author_info")
            published = author_info_tag.find('p', class_='date').text
            pagemap.posted_date = datetime.strptime(published, '%d-%b-%Y')
        except:
            pass
        try:
            box_1_tag = bs.find("div", class_="box_1")
            product_info_bar_tag = box_1_tag.find("div", class_="product_info_bar")
            published = re.search(r'([0-9]{2}-[a-z,A-Z]{3}-[0-9]{4})', product_info_bar.text, re.MULTILINE)
            pagemap.posted_date = datetime.strptime(published.group(0), '%d-%b-%Y')
        except:
            pass
        # get page
        try:
            pagemap.page        = bs.get_text()
            box_1_tag = bs.find("div", class_="box_1")
            pagemap.page = box_1_tag.text
            product_main_text_tag = box_1_tag.find("div", class_="product_main_text")
            if product_main_text_tag != None:
                pagemap.page = product_main_text_tag.text
            else:
                story_tag = box_1_tag.find("div", class_="story")
                pagemap.page = story_tag.text
        except:
            pass
        # get title
        try:
            if bs.title != None:
                pagemap.title   = bs.title.text
            else:
                pagemap.title   = ''
            box_1_tag = bs.find("div", class_="box_1")
            pagemap.title = box_1_tag.find("h1").text
        except:
            pass
        # get section
        try:
            box_2_tag = bs.find("div", class_="box_2")
            pagemap.section = box_2_tag.text.strip(' \t\n\r')
        except:
            pass

        data = elastic.convert_for_bulk(pagemap, 'update')
        return data


def crawl_cosmetic(scrape_choices):
    cosmetic = Crawler('cosmeticsdesign')
    cosmetic.bulk_data = None
    cosmetic.bulk_data = []
    cosmetic.pages = set()
    sub_sites = set()
    if len(scrape_choices) == 0:
        sub_sites.add(site)
#   for site in ['http://www.cosmeticsdesign.com/', 'http://www.cosmeticsdesign-europe.com/', 'http://www.cosmeticsdesign-asia.com/']:
    for site in ['http://www.cosmeticsdesign.com/']:
        for scrape_choice in scrape_choices:
            if scrape_choice == 'product':
                sub_sites.add(site+'/Product-Categories/Skin-Care')
                sub_sites.add(site+'/Product-Categories/Hair-Care')
            if scrape_choice == 'market':
                sub_sites.add(site+'Market-Trends')
                sub_sites.add(site+'Brand-Innovation')

    for sub_site in sub_sites:
        links = cosmetic.get_pagination_links(sub_site)
        for link in links:
            bs = cosmetic.scrape(link)
            cosmetic.pages.add(link)
            data = cosmetic.push_to_index(link, bs)
            cosmetic.bulk_data.append(data)

    #links = sub_sites
    #while len(links) > 0 and count <50:
    #    intlinks = cosmetic.get_pagination_links(link, bs)
    #    newlinks = set()
    #    for link in links:
    #        bs = cosmetic.scrape(link)
    #        cosmetic.pages.add(link)
    #        intlinks = cosmetic.get_internal_links(link, bs)
    #        intlinks = intlinks - cosmetic.pages
    #        newlinks = newlinks.union(intlinks)
    #        data = cosmetic.push_to_index(link, bs)
    #        cosmetic.bulk_data.append(data)
    #        count = count + 1
    #        if count > 50:
    #            break
    #    links = newlinks
    bulk(models.client, actions=cosmetic.bulk_data, stats_only=True)

#
# FEEDLY
#
headers = {
#   sjaak.waarts@gmail.com
#   "Authorization" : "OAuth Az5SlrMMGO5owXJjGNpxDdf7B6tKdhJ_a9bmV-B7QG4pYhggBica6k0ONuE38l2PrpqjxU42UYoeO_QcV3feSBma6rAgT627orLQYo385hH_0A_iX3IyYWePPKJdpKEgl81eBUtw0tALOA-DeVdt4LVsynpHcBOLS4P1Z6Ll6473B4f6leXO3vMK-BFqUA8PM_Ny4JnHOI8vXJ_ErcR0ixDVeDOzER8:feedlydev"
#   sjaak.waarts@gmail.com (expires on 2017-02-08)
    "Authorization" : "AyArarRGBWzf6qc63KsI6lJO6VTr5_u-oAd17yp7gMlwIu2XGxqBTAlK6kPd8OGzquQYtRj32y3K51n-zkKO_MK-vjaXGXG8l32dRLb4arfkwhMhC3f_iIiN9v3_JsHwgjWvNN-nSi46JEpaNkMcAyNYyd_-T8448q8vuoZgU_j-UCRs4BKkGCIfhaoCFOUDX_y565fdOETLeqsZMmESePOHv-5f3Fo:feedlydev"
#   Rebecca (expires on 2017-02-02)
#   "Authorization" : "AwFFQrRDR0ALNVMpm0xQJ_Rp2BSuy_n7nNrsYmoAbAqIPCJsIZxggzBabTLVb0Qxtjrk8xMDepyA3gvuO3h3j2b5m45V9biYqBS6XBszpk6x-oa-mcWCAy1a5HvM3cg7V41fllELFUyqPpbMvFolhPmqJGAQsfKc28huj6R4U-cHS7Ted4sSLQmWUj83XHQebFegI3UlClUU-YEdA4bhGsBOwW3nBg:feedlydev"
    }

def crawl_feedly(from_date, rss_field):
    global headers

    bulk_data = []
    today = datetime.now()
    days = timedelta(days=31)
    yesterday = today - days
    s = yesterday.timestamp()
    t = time(0, 0)
    dt = datetime.combine(from_date, t)
    s = dt.timestamp()
    #datetime.datetime.fromtimestamp(s).strftime('%c')
    ms = s * 1000
    newerthan = "{:.0f}".format(ms)
    headers = {
#       sjaak.waarts@gmail.com
#       "Authorization" : "OAuth Az5SlrMMGO5owXJjGNpxDdf7B6tKdhJ_a9bmV-B7QG4pYhggBica6k0ONuE38l2PrpqjxU42UYoeO_QcV3feSBma6rAgT627orLQYo385hH_0A_iX3IyYWePPKJdpKEgl81eBUtw0tALOA-DeVdt4LVsynpHcBOLS4P1Z6Ll6473B4f6leXO3vMK-BFqUA8PM_Ny4JnHOI8vXJ_ErcR0ixDVeDOzER8:feedlydev"
#       sjaak.waarts@gmail.com (expires on 2017-04-12)
#       "Authorization" : "A2ScDrZV4o-6ZYKXifNVJHif7dsFhQrbkvCue6MrvbuKYcilmi5TbtMIl5IwATfpELY52INwNMZQ5vkqAGfwqQMUVV60iReBvH_lp-HXq1vGTmHb7Iow-d3evduu-De9yz3D-9z9z-DIffkeyQtVdwiONj4UBlk4sakgoE3Cx-_zVIfuiTnLRCyABxJS29acATrpRAmXthGfmBwIetk-moYNMna6tg:feedlydev"
        "Authorization" : "Aw9M5rkU1gRrrvZJahGpxozQTzRhUxIflGX6leMC3cYUBO7UosO5A7fclErhJ3O3uTjWNMQ33nsE02viJjNeFx5jwhCRlLc036OpUkBqqc099cLtV7T2lEkyc5Wy153PV8iu2eOBclzuT1-Jpjwt3ZMhuHZGbd4QMDM4uxUMgaCERGQKAH4zeAEjORim_Be_ah99hPfqRdSqymzuH6axi0po9SIeu-M:feedlydev"
#       Rebecca (expires on 2017-02-02)
#       "Authorization" : "AwFFQrRDR0ALNVMpm0xQJ_Rp2BSuy_n7nNrsYmoAbAqIPCJsIZxggzBabTLVb0Qxtjrk8xMDepyA3gvuO3h3j2b5m45V9biYqBS6XBszpk6x-oa-mcWCAy1a5HvM3cg7V41fllELFUyqPpbMvFolhPmqJGAQsfKc28huj6R4U-cHS7Ted4sSLQmWUj83XHQebFegI3UlClUU-YEdA4bhGsBOwW3nBg:feedlydev"
        }

    params_streams = {
#       "count"     : "100",
        "count"     : "1000",
        "ranked"    : "newest",
        "unreadOnly": "false",
        "newerThan" : newerthan
        }
    #url = "http://cloud.feedly.com/v3/profile"
    #r = requests.get(url, headers=headers)
    url = "http://cloud.feedly.com/v3/subscriptions"
    r = requests.get(url, headers=headers)
    feeds = r.json()
    for feed in feeds:
        feed_id = feed['id']
        feed_title = feed['title'].encode("ascii", 'replace')
        feed_category = feed['categories'][0]['label']
        print("Scrape: scraping feed ", feed_title)
        if rss_field == '' or feed_category == rss_field:
            url = "http://cloud.feedly.com//v3/streams/contents"
            params_streams['streamId'] = feed_id
            r = requests.get(url, headers=headers, params=params_streams)
            stream = r.json()
            for entry in stream['items']:
                feedlymap = models.FeedlyMap()
                feedlymap.post_id = entry['id']
                feedlymap.published_date = datetime.fromtimestamp(entry['published']/1000)
                feedlymap.category = feed_category
                feedlymap.feed = feed_title
                if 'topics' in feed:
                    feedlymap.feed_topics = feed['topics']
                if 'keywords' in entry:
                    feedlymap.body_topics = entry['keywords']
                feedlymap.title = entry['title']
                if 'canonicalUrl' in entry:
                    feedlymap.url = entry['canonicalUrl']
                else:
                    n = entry['originId'].find('http')
                    feedlymap.url = entry['originId'][n:]
                feedlymap.post_id = feedlymap.url
                if 'summary' in entry:
                    bs = BeautifulSoup(entry['summary']['content'],  "lxml") # in case of RSS feed
                if 'content' in entry:
                    bs = BeautifulSoup(entry['content']['content'], "lxml") # in case of Google News feed
                feedlymap.body = bs.get_text().encode("ascii", 'replace')
                data = elastic.convert_for_bulk(feedlymap, 'update')
                bulk_data.append(data)

    bulk(models.client, actions=bulk_data, stats_only=True)

def export_opml_feedly(opml_filename):
    global headers

    url = "http://cloud.feedly.com/v3/opml"
    r = requests.get(url, headers=headers)
    xml = r.content

    opml_file = 'data/' + opml_filename + '_opml.txt'
    try:
        file = open(opml_file, 'wb')
        pyfile = File(file)
        pyfile.write(xml)
        pyfile.close()
        return True
    except:
        return False


def import_opml_feedly(opml_filename):
    global headers

    opml_file = 'data/' + opml_filename + '_opml.txt'
    try:
        file = open(opml_file, 'rb')
        pyfile = File(file)
        xml = pyfile.read()
        pyfile.close()
    except:
        return False

    url = "http://cloud.feedly.com/v3/opml"
    h2 = headers
    h2['Content-Type'] = 'application/xml'
    r = requests.post(url, headers=headers, data=xml)
    
    return True


def crawl_studies_facts(survey_field, facts_d):
    bulk_data = []
    count = 0
    total_count = 0
    facts_df = DataFrame.from_dict(facts_d, orient='index')
    facts_df['blindcode'] = [ix[0] for ix in facts_df.index]
    facts_df['fact'] = [ix[1] for ix in facts_df.index]
    facts_df['answer'] = [ix[2] for ix in facts_df.index]

    for blindcode, facts_blindcode_df in facts_df.groupby(facts_df['blindcode']):
        se = models.StudiesMap()
        se.cft_id = blindcode
        se.dataset = survey_field
        se.ingr_name = blindcode
        se.IPC = blindcode
        percentile = {}

        for idx, fact_s in facts_blindcode_df.iterrows():
            fact = fact_s['fact']
            answer = fact_s['answer']
            #se.supplier = "CI"
            #se.olfactive = cft_s.olfactive
            #se.region = cft_s.region
            #se.review = cft_s.review
            #se.dilution = cft_s.dilution
            #se.intensity = cft_s.intensity

            if fact not in percentile.keys():
                percentile[fact] = []
            val = answer
            prc = fact_s[0]
            if prc > 0:
                percentile[fact].append((val, prc))

        for fact in percentile.keys():
            if fact == 'emotion':
                se.emotion = percentile[fact]
            if fact == 'suitable_stage':
                se.suitable_stage = percentile[fact]
            if fact == 'hedonics':
                se.hedonics = percentile[fact]
            if fact == 'freshness':
                se.freshness = percentile[fact]

        data = elastic.convert_for_bulk(se, 'update')
        bulk_data.append(data)
        count = count + 1
        if count > 100:
            bulk(models.client, actions=bulk_data, stats_only=True)
            total_count = total_count + count
            print("crawl_studies_facts: written another batch, total written {0:d}".format(total_count))
            bulk_data = []
            count = 1

    bulk(models.client, actions=bulk_data, stats_only=True)
    pass

def crawl_scentemotion(cft_filename):
    ml_file = 'data/' + cft_filename
    cft_df = pd.read_csv(ml_file, sep=';', encoding='ISO-8859-1', low_memory=False)
    cft_df.fillna(0, inplace=True)
    cft_df.index = cft_df['cft_id']
    bulk_data = []
    count = 0
    total_count = 0
    for cft_id, cft_s in cft_df.iterrows():
        se = models.ScentemotionMap()
        se.cft_id = cft_id
        se.dataset = "ingredients"
        se.ingr_name = cft_s.ingr_name
        se.IPC = cft_s.IPC
        se.supplier = cft_s.supplier
        se.olfactive = cft_s.olfactive
        se.region = cft_s.region
        se.review = cft_s.review
        se.dilution = cft_s.dilution
        se.intensity = cft_s.intensity

        percentile = {}
        for col in cft_s.index:
            col_l = col.split("_", 1)
            fct = col_l[0]
            if fct not in ["mood", "smell", "negative", "descriptor", "color", "texture"]:
                continue
            if fct not in percentile.keys():
                percentile[fct] = []
            val = col_l[1]
            prc = cft_s[col]
            if prc > 0:
                #percentile[fct].append((val, "{0:4.2f}".format(prc)))
                percentile[fct].append((val, prc))

        se.mood = percentile["mood"]
        se.smell = percentile["smell"]
        se.negative = percentile["negative"]
        se.descriptor = percentile["descriptor"]
        se.color = percentile["color"]
        se.texture = percentile["texture"]

        data = elastic.convert_for_bulk(se, 'update')
        bulk_data.append(data)
        count = count + 1
        if count > 100:
            bulk(models.client, actions=bulk_data, stats_only=True)
            total_count = total_count + count
            print("crawl_scentemotion: written another batch, total written {0:d}".format(total_count))
            bulk_data = []
            count = 1

    bulk(models.client, actions=bulk_data, stats_only=True)
    pass

def map_survey(survey_filename):
    survey_name = os.path.splitext(survey_filename)[0].split('-', 1)[0].strip()
    ml_file = 'data/' + survey_filename
    survey_df = pd.read_csv(ml_file, sep=';', encoding='ISO-8859-1', low_memory=False)
    survey_df.fillna(0, inplace=True)
    field_map , col_map = survey.map_columns(survey_name, survey_df.columns)
    return col_map


def crawl_survey1(survey_filename):
    survey_name = os.path.splitext(survey_filename)[0].split('-', 1)[0].strip()
    ml_file = 'data/' + survey_filename
    survey_df = pd.read_csv(ml_file, sep=';', encoding='ISO-8859-1', low_memory=False)
    survey_df.fillna(0, inplace=True)
    # col_map[column]: (field, question, answer, dashboard)
    # field_map[field]: [question=0, answer=1, column=2)]
    field_map , col_map = survey.map_columns(survey_name, survey_df.columns)
    survey_df.index = survey_df[field_map['resp_id'][0][2]]
    bulk_data = []
    count = 0
    total_count = 0
    for resp_id, survey_s in survey_df.iterrows():
        sl = models.SurveyMap()
        resp_id = survey.answer_value_to_string(survey_s[field_map['resp_id'][0][2]])
        blindcode = survey.answer_value_to_string(survey_s[field_map['blindcode'][0][2]])
        sl.resp_id = resp_id+"_"+blindcode
        sl.survey  = survey_name
        sl.affective = {}
        sl.ballot = {}
        sl.behavioral = {}
        sl.children = {}
        sl.concept = {}
        sl.descriptors = {}
        sl.emotion = {}
        sl.fragrattr = {}
        sl.hedonics = {}
        sl.mood = {}
        sl.physical = {}
        sl.smell = {}
        sl.suitable_product = {}
        sl.suitable_stage = {}
        for field, maps in field_map.items():
            # resp_id is the unique id of the record, this is already set above
            if field == 'resp_id':
                continue
            # map: 0=question, 1=answer, 2=column
            map = maps[0]
            answer_value = survey_s[map[2]]
            answer_value = survey.answer_value_to_string(answer_value)
            answer_value = survey.answer_value_encode(map[0], map[1], field, answer_value)
            # column mapping, no question
            if map[0] == None:
                # in case of multiple mapping search for the column that has a value
                for ix in range(1, len(maps)):
                    map = maps[ix]
                    answer_value_2 = survey_s[map[2]]
                    answer_value_2 = survey.answer_value_to_string(answer_value_2)
                    if (field == 'blindcode'):
                        answer_value = answer_value + '-' + answer_value_2[:3]
                    else:
                        if len(answer_value_2) > len(answer_value):
                            answer_value = answer_value_2
                setattr(sl, field, answer_value)
            # question mapping, no answer
            elif map[1][0] == '_':
                setattr(sl, field, answer_value)
            # answer mapping
            else:
                setattr(sl, field, {map[1]: answer_value})
                attr = getattr(sl, field)
                for ix in range(1, len(maps)):
                    map = maps[ix]
                    answer_value = survey_s[map[2]]
                    answer_value = survey.answer_value_to_string(answer_value)
                    answer_value = survey.answer_value_encode(map[0], map[1], field, answer_value)
                    attr[map[1]] = answer_value
                    #attr.append({map[1]: answer_value})

        data = elastic.convert_for_bulk(sl, 'update')
        bulk_data.append(data)
        count = count + 1
        if count > 100:
            bulk(models.client, actions=bulk_data, stats_only=True)
            total_count = total_count + count
            print("crawl_survey: written another batch, total written {0:d}".format(total_count))
            bulk_data = []
            count = 1
            #break

    bulk(models.client, actions=bulk_data, stats_only=True)
    pass


def crawl_survey(survey_filename):
    survey_name = os.path.splitext(survey_filename)[0].split('-', 1)[0].strip()
    if survey_name == 'fresh and clean':
         crawl_survey1(survey_filename)
    elif survey_name == 'orange beverages':
         crawl_survey1(survey_filename)








