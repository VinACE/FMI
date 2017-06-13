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
import os
from FMI.settings import BASE_DIR
import base64


import app.models as models


def molecules(ipc_field):
#http://usubstsappv1.global.iff.com:9944/auth/launchjob?$protocol=Protocols/Web%20Services/RESTful/test&ipc_in=

#where you will add an IPC# after the equal sign.  Please use these credentials in the response header: 

#USER=rd_iis_svc
#PASS=Abs0lut5

    user = "global\\rd_iis_svc"
    pswrd = "Abs0lut5"

    params = {
        #"$protocol" : "Protocols/Web Services/RESTful/test",
        "$protocol" : "Protocols/Web Services/RESTful/ipc_properties",
        "ipc_in"    : ipc_field,
        }
    url = "http://usubstsappv1.global.iff.com:9944/auth/launchjob"
    #url = "https://usubstsappv1.global.iff.com:9944/auth/launchjob"
    r = requests.get(url, auth=(user, pswrd), params=params)
    #url = "http://usubstsappv1.global.iff.com:9944/auth/launchjob?$protocol=Protocols/Web%20Services/RESTful/test&ipc_in=98663"
    if r.status_code != 200:
        print("molecules: get request failed ", r.status_code)
        return

    print("molecules: get request: ", r.url)
    molecules_json = r.json()

    #imgdata = base64.b64decode(molecules_json['MOLECULE']) 
    #imgdata = molecules_json['MOLECULE'].decode("base64")
    b64_string = molecules_json['MOLECULE']
    b64_bytes = b64_string.encode()
    imgdata = base64.decodebytes(b64_bytes) 
    img_file = os.path.join(BASE_DIR, 'data/' + 'molecule.jpg')
    try:
        with open(img_file, 'wb') as f:
            f.write(imgdata)
    except:
        cwd = os.getcwd()
        print("molecules: working dirtory is: ", cwd)

    molecules_d = {}
    return molecules_d

