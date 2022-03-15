import requests
from requests_oauthlib import OAuth2Session
from urllib.parse import urljoin, urlparse, urlunparse, urlencode
from getpass import getpass
from oauthlib.oauth2 import LegacyApplicationClient, Client
import json
import time
from datetime import datetime
import os
import sys
import argparse
import boto3
from pathlib import Path
from types import GeneratorType
import shutil

from config import (
    HSPIAMConfig,
    HSPCDLConfig,
    BaseConfig,
)

def _write_json(filename, ljobj):
    """ Write a list of json objects to file
    """
    with open(filename, 'w') as outf:
        for i in ljobj:
            json.dump(i, outf)
            outf.write("\n")

def _read_json(filename):
   """ Generator which reads the contents of the file as
       json
   """
   with open(filename) as inf:
       for l in inf:
           yield json.loads(l)
           
def _download_linked_data(url, sobj):
    """ Downloads data in chunks and returns an array of
        json objects
    """
    getnext = True
    lresponse = []
    while getnext:
        print('Getting chunk ...')
        getnext = False
        r = sobj.get(url)
        rescode = r.status_code
        if rescode == requests.codes.ok:
            resp = r.json()
            for lnk in resp['link']:
                if lnk['relation'] == 'next':
                    getnext = True
                    url = lnk['url']
            lresponse.append(resp)
    return rescode, lresponse

def _download_s3_credentials(config):
    """
    """
    global _sobj
    if os.path.exists('s3_credentials.txt'):
       with open("s3_credentials.txt") as fp:
           s3cred = json.load(fp)
       if s3cred["expiration"] and datetime.fromisoformat(s3cred["expiration"]) > datetime.now():
           print("Reusing s3 credentials")
           return s3cred
    _sobj.headers.update({'api-version':'2'})
    r = _sobj.get(config["s3_cred_url"])
    if r.status_code == requests.codes.ok:
        resp = r.json()
        with open(os.path.join(config["tmpdir"],"s3_credentials.txt"),"w") as fp:
            json.dump(resp, fp)
    else:
        print(r.status_code)
        print(r.text)
        resp = None
    return resp

def fetch_tokens(config):
    """ Fetch access tokens
    """
    if os.path.exists(os.path.join(config["tmpdir"],'fetch_tokens.txt')):
        with open(os.path.join(config["tmpdir"],'fetch_tokens.txt')) as fp:
            tokens = json.load(fp)
        if tokens['expires_at'] and tokens['expires_at'] > time.time() + 60:
            print('Reusing previous fetched tokens')
            return tokens
    print('Fetching tokens')
    iam_url = HSPIAMConfig.HSP_IAM_URL
    token_url = urljoin(iam_url, "authorize/oauth2/token")
    userpwd = HSPIAMConfig.HSP_IAM_PASSWORD
    if not userpwd:
        userpwd = getpass("Enter HSP IAM PASSWORD: ")
    client = LegacyApplicationClient(client_id=HSPCDLConfig.HSP_CDL_CLIENT_ID)
    response = OAuth2Session(client=client).fetch_token(
        token_url = token_url,
        username = HSPIAMConfig.HSP_IAM_USERNAME,
        password = userpwd,
        client_secret = userpwd
    )
    with open(os.path.join(config["tmpdir"],'fetch_tokens.txt'),'w') as fp:
        json.dump(response, fp)
    return response
    
def _gen_process_bundle(bundles):
    """ Generator which returns a resource json object from a bundle
        or a list of bundles
    """
    lb = bundles if isinstance(bundles, GeneratorType) else \
         bundles if isinstance(bundles, list) else \
         [bundles]
    for b in lb:
        if 'entry' not in b:
            continue
        for e in b['entry']:
            yield e['resource']
    return
    
def fetch_patients(config):
    """ Fetch list of patients
    """
    global _sobj
    print('Fetching patient list ...')
    cdal_patient_url = config["cdal_fhir_patient_url"]
    patients = []
    _sobj.headers.update({'api-version':'3'})
    scode, patients = _download_linked_data(cdal_patient_url, _sobj)
    pinfo = []
    for r in _gen_process_bundle(patients):
        pinfo.append({'id':r['id'],'MR':r['identifier'][0]['value']})
    _write_json(os.path.join(config["tmpdir"],'patients.txt'),pinfo)
        

def _download_patient_data(poutdir, cdal_data_url, mrid):
    global _sobj
    print(f"Downloading data for patient: {mrid}")
    data_collection_url = urlparse(urljoin(cdal_data_url, "DataCollection"))
    data_collection_url = data_collection_url._replace(
        query=urlencode({'patient':mrid}))
    _sobj.headers.update({'api-version':'3'})
    scode, cbundle = _download_linked_data(urlunparse(data_collection_url), _sobj)
    if scode != requests.codes.ok:
        return scode
    lcollect = [{'collectionId':'default'}]
    for r in _gen_process_bundle(cbundle):
        lcollect.append({'collectionId':r['id']})
    dbundle = []
    data_object_url = urlparse(urljoin(cdal_data_url, "DataObject"))
    for c in lcollect:
        do_url = data_object_url._replace(
            query=urlencode({'patient':mrid, 'collectionId':c['collectionId'], 'page':0}))
        scode, dobj = _download_linked_data(urlunparse(do_url), _sobj)
        if scode != requests.codes.ok:
            return scode        
        dbundle.extend(dobj)
    _write_json(os.path.join(poutdir, 'metadata.json'), dbundle)    
    return scode

def fetch_patient_metadata(argv, config):
    """ Fetches data for patients in the patients.txt file.
    """
    if not os.path.exists(os.path.join(config["tmpdir"],'patients.txt')):
        print("Patient list missing!!")
        print("Download patient list first")
        print_usage()
        return
    outdir = config["tmpdir"]
    cdal_data_url = config['cdal_data_url']
    _sobj.headers.update({'api-version':'3'})
    for p in _read_json(os.path.join(outdir,"patients.txt")):
        p_mr = p['MR']
        poutdir = os.path.join(outdir,p_mr)
        if os.path.exists(poutdir):
            print(f"Patient data {p_mr} already downloaded. Skipping")
            continue
        os.makedirs(poutdir)
        scode = _download_patient_data(poutdir, cdal_data_url, p_mr)
        if scode != requests.codes.ok:
            print(f"Download failed: {scode}")
            return
        time.sleep(2)

def _gen_extract_s3_files(mdfiles):
    """ Generator which extract s3 files details from
        metadata.json and returns a dict with type and 
        list of files.
    """
    for md in mdfiles:
        jobjs = _read_json(md)
        bitems = _gen_process_bundle(jobjs)
        for b in bitems:
            yield {'outdir': os.path.dirname(md),
                   'restype': b['resourceType'],
                   'files': b["files"] }

def _download_from_s3(files, config):
    """ Downloads files from s3 
    """
    _sobj.headers.update({'api-version':'2'})
    s3cred = _download_s3_credentials(config)
    s3 = boto3.resource(
        "s3",
        aws_access_key_id=s3cred['accessKey'],
        aws_secret_access_key=s3cred['secretKey'],
        aws_session_token=s3cred['sessionToken'],
    )
    s3_base_url = urlparse(s3cred['s3BaseUrl'])
    bucket = s3.Bucket(s3_base_url.netloc)
    prefix = s3_base_url.path.lstrip("/")
    for f in files:
        if f['restype'].lower() == 'reimaginebiosamplesdata':
            for i in f["files"]:
                file_key = i[i.find(prefix):]
                fname = os.path.join(f["outdir"], i.split("/")[-1])
                if os.path.exists(fname):
                    print(f"Skipping downloading {fname}")
                    continue
                print(f"Downloading {fname}")    
                bucket.download_file(file_key, fname)
        elif f['restype'].lower() == "dicom":
            for i in f["files"]:
                print(f"Downloading to {f['outdir']} ...")
                fileprefix = i[i.find(prefix):]
                for obj_summary in bucket.objects.filter(Prefix=fileprefix):
                    file_key = obj_summary.key
                    dicomfile = file_key[file_key.find("DICOM/"):]
                    file_name = dicomfile.split("/")[-1]
                    dicomdir = dicomfile[:dicomfile.find(file_name)]\
                        .replace("urn:oid:","")\
                        .replace('/',"\\")
                    dicomdir = os.path.join(f["outdir"],dicomdir)
                    if not os.path.exists(dicomdir):
                        os.makedirs(dicomdir)
                    if os.path.exists(os.path.join(dicomdir,file_name)):
                        print('Skipping ...')
                        continue
                    print(f"Downloading {file_name}")
                    # To avoid problem with long pathnames in Windows
                    bucket.download_file(file_key, os.path.join(f["outdir"],file_name))
                    shutil.move(os.path.join(f["outdir"],file_name), os.path.join(dicomdir,file_name))

def fetch_patient_data(argv, config):
    """ Fetches data of a patient based on the metadata.json
    """
    indir = config["tmpdir"]
    # Get metadata.json from patient subdirectories to process
    metadfiles = Path(indir).rglob('metadata.json')
    s3files = _gen_extract_s3_files(metadfiles)
    _download_from_s3(s3files, config)

        
def print_usage():
    print(f"\ndownload.py COMMAND [ARGS]")
    print("""
patients: 
    This command downloads the list of patients associated with
    a research study and stores it in .tmp\\patients.txt

patient-metadata: 
    This command downloads metadata about patient data and stores it in metadata.json
       args: 
       output-dir: Output directory where metadata.json per patient is
       created.
       
patient-data:
    This command downloads the actual data per patient and stores it under the 
    subfolder created with patient's MR identifier in the output directory.
        args:
        output-dir: Output directory where DICOM data and BioSamples data
        will be downloaded per patient.
""")

_sobj = None

def main(argv):
    global _sobj
    if len(argv) < 1:
        print_usage()
        return
    config = {}
    config["tmpdir"] = BaseConfig.OUTPUT_DIR
    config["cdal_fhir_patient_url"] = HSPCDLConfig.cdl_fhir_patient_url()
    config["cdal_data_url"] = HSPCDLConfig.cdl_data_url()
    config["s3_cred_url"] = HSPCDLConfig.cdl_s3_download_credentials_url()
    config['iam_tokens'] = fetch_tokens(config)
    accessToken = config['iam_tokens']['access_token']
    reqh = {
        'accept':'*/*',
        'content-type':'application/json',
        'connection':'keep-alive',
        'authorization':f"Bearer {accessToken}"
    }
    _sobj = requests.Session()
    _sobj.headers.update(reqh)
    os.makedirs(config["tmpdir"],exist_ok=True)
    command = argv[0].lower()
    if command == "patients":
        fetch_patients(config)
    elif command == "patient-metadata":
        fetch_patient_metadata(argv[1:], config)
    elif command == "patient-data":
        fetch_patient_data(argv[1:], config)
    else:
        print(f'Unknown command: {command}')
        print_usage()
    return

if __name__ == "__main__":
    main(sys.argv[1:])