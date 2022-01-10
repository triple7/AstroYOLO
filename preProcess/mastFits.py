import sys
import os
import time
import re
import json
from fits2jpeg import *

try: # Python 3.x
    from urllib.parse import quote as urlencode
    from urllib.request import urlretrieve
except ImportError:  # Python 2.x
    from urllib import pathname2url as urlencode
    from urllib import urlretrieve

try: # Python 3.x
    import http.client as httplib 
except ImportError:  # Python 2.x
    import httplib   


## Some global vars 
MAST_DATA = './images/'

from astropy.table import Table
import numpy as np
import pprint
pp = pprint.PrettyPrinter(indent=4)

#Most interesting observation property filters are below
#https://mast.stsci.edu/api/v0/_c_a_o_mfields.html
#
#

#get list of observation sources
#table = obs.query_region("10.403516 -17.432961")

#Most interesting data source filter parameters
#https://mast.stsci.edu/api/v0/_productsfields.html
#
#dataproduct_type Valid values: IMAGE, SPECTRUM, SED, TIMESERIES, VISIBILITY, EVENTLIST, CUBE, CATALOG, ENGINEERING, NULL
#obs_collection HST, HLA, SWIFT, GALEX, Kepler, K2...
#productType Valid values: SCIENCE, CALIBRATION, BIAS, DARK, FLAT, WAVECAL, NOISE, WEIGHT, AUXILIARY, INFO, CATALOG, LIGHTCURVE, TARGETPIXELS, PREVIEW, PREVIEW_FULL, PREVIEW_1D, PREVIEW_2D, THUMBNAIL, PREVIEW_THUMB, MINIMUM_SET, RECOMMENDED_SET, COMPLETE_SET, WEBSERVICE
#type Valid values: C (composite), S (simple)
#

#print(table[:10])
#Getting only the intentType, observation_group and the observation id
#table = [[t[0], t[1], t[-2]] for t in table]
#get the data products associated to the object
#data = obs.get_product_list(table[0][-1])
#print(data)
#Get the manifest of downloadable observations for TESS calibrated images
#manifest = obs.download_products(data,  dataproduct_type=["image"], obs_collection=["TESS"])
#print("Number of files: ", str(len(manifest)))

def mastQuery(request):
    server='mast.stsci.edu'
    version = ".".join(map(str, sys.version_info[:3]))
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain", "User-agent":"python-requests/"+version}
    requestString = json.dumps(request)
    requestString = urlencode(requestString)
    
    conn = httplib.HTTPSConnection(server)
    conn.request("POST", "/api/v0/invoke", "request="+requestString, headers)
    resp = conn.getresponse()
    head = resp.getheaders()
    content = resp.read().decode('utf-8')
    conn.close()
    return head,content

if __name__ == '__main__':
    objectOfInterest = sys.argv[1]
    name = objectOfInterest
    print(name)
    resolverRequest = {'service':'Mast.Name.Lookup',
                         'params':{'input':objectOfInterest,
                                   'format':'json'},
                         }
    headers,resolvedObjectString = mastQuery(resolverRequest)
    resolvedObject = json.loads(resolvedObjectString)
    if len(resolvedObject) == 0:
        print("Couldnt resolve object "+name)
        quit()
    res = resolvedObject['resolvedCoordinate'][0]
    resKeys = ['canonicalName', 'objectType', 'radius']
    resValues = [res.get(k) for k in resKeys]
    # for i in range(len(resKeys)):
        # print(resKeys[i], resValues[i])
    # Here we want ra/dec and radius of the object
    objRa = res['ra']
    objDec = res['decl']
    objType = res['objectType'] if res.get('objectType') != None else 'star'
    # here we have the choice of parameters. They are in
    #https://mast.stsci.edu/api/v0/_c_a_o_mfields.html
    mastRequest = {'service':'Mast.Caom.Cone',
                   'params':{'ra':objRa,
                             'dec':objDec,
    },
                   'format':'json',
                   'pagesize':500,
                   'page':1,
                   'removenullcolumns':True,
                   'removecache':True}

    headers,mastDataString = mastQuery(mastRequest)
    mastData = json.loads(mastDataString)
    # print('keys for mast data\n',mastData.keys())
    # print(mastData['status'])
    # print('found '+str(len(mastData['data']))+' products of specified fields')

    mastDataTable = Table()
    for col,atype in [(x['name'],x['type']) for x in mastData['fields']]:
        if atype=="string":
            atype="str"
        if atype=="boolean":
            atype="bool"
        mastDataTable[col] = np.array([x.get(col,None) for x in mastData['data']],dtype=atype)
    
    # types = []
    # for row in mastDataTable:
    #     K = ['intentType', 'dataproduct_type', 'obs_collection', 'instrument_name', 'wavelength_region', 'calib_level']
    #     for k in K:
    #         print(k, row[k])
    
    count = 0
    for i in range(len(mastDataTable)):
        interestingObservation = mastDataTable[i]
        paramFilters = ['dataproduct_type', 'wavelength_region']
        filterValues = [['image', 'optical']]
        # filterValues = [['image', 'optical'], ['image', 'optical;infrared'], ['image', 'optical;uv', ['image', 'uv;optical']], ['image', 'uv']]
        results = [interestingObservation[k].lower() for k in paramFilters]
        # print(results)
        if results not in filterValues:
            continue
        
        obsid = interestingObservation['obsid']
        productRequest = {'service':'Mast.Caom.Products', 'params':{'obsid':obsid}, 'format':'json', 'pagesize':1, 'page':1}
        headers,obsProductsString = mastQuery(productRequest)
        obsProducts = json.loads(obsProductsString)
        
        sciProdArr = obsProducts['data']
        scienceProducts = Table()
        for col,atype in [(x['name'],x['type']) for x in obsProducts['fields']]:
            if atype=="string":
                atype="str"
            if atype=="boolean":
                atype="bool"
            if atype == "int":
                atype = "float"
            scienceProducts[col] = np.array([x.get(col,None) for x in sciProdArr],dtype=atype)
        
        server='mast.stsci.edu'
        conn = httplib.HTTPSConnection(server)
        
        # here some more filters are available
        #https://mast.stsci.edu/api/v0/_productsfields.html
        for row in scienceProducts:
            productFilters = ['type', 'productType']
            productValues = [['s', 'science']]
            productResult = [row[k].lower() for k in productFilters]
            if productResult not in productValues:
                continue
            path = row['productFilename']
            outPath = MAST_DATA+objType
            if not os.path.exists(outPath):
                os.makedirs(outPath)
            outPath += '/'+row['productFilename']
        
            # Download the data
            uri = row['dataURI']
            fileFormat = str(uri).split('.')[-1]
            # print(fileFormat)
            if fileFormat != 'jpeg' and fileFormat != 'fits':
                continue
            conn.request("GET", "/api/v0/download/file?uri="+uri)
            resp = conn.getresponse()
            fileContent = resp.read()
        
            # save to file
            with open(outPath,'wb') as FLE:
                FLE.write(fileContent)
                if fileFormat == 'fits':
                    fits2jpeg(outPath)
        
            conn.close()

