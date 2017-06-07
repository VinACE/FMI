from datetime import datetime
from datetime import time
from datetime import timedelta
import re
from pandas import Series, DataFrame
import pandas as pd
import collections
import urllib
import requests
from urllib.parse import urlparse
from requests_ntlm import HttpNtlmAuth


import app.models as models


def molecules(ipc_field):
#http://usubstsappv1.global.iff.com:9944/auth/launchjob?$protocol=Protocols/Web%20Services/RESTful/test&ipc_in=

#where you will add an IPC# after the equal sign.  Please use these credentials in the response header: 

#USER=rd_iis_svc
#PASS=Abs0lut5

    user = "global\\rd_iis_svc"
    pswrd = "Abs0lut5"

    params = {
        "$protocol" : "Protocols/Web Services/RESTful/test",
        "ipc_in"    : ipc_field,
        }
    #url = "http://usubstsappv1.global.iff.com:9944/auth/launchjob"
    url = "https://usubstsappv1.global.iff.com:9944/auth/launchjob"
    r = requests.get(url, auth=(user, pswrd), params=params)
    #url = "http://usubstsappv1.global.iff.com:9944/auth/launchjob?$protocol=Protocols/Web%20Services/RESTful/test&ipc_in=98663"
    #r = requests.get(url, auth=(user, pswrd))
    print("molecules: get request: ", r.url)
    molecules_json = r.json()

    molecules_d = {}
    return molucules_d

