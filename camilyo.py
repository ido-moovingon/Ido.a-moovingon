# # # # # # # # # # # # # # # # # # # # # # #
#                                           #
#         HTTP Check for Camilyo            #
#   Created by Ido Abuhav for MoovingON     #
#         ido.a@moovingon.com               #
#                                           #
# # # # # # # # # # # # # # # # # # # # # # #
 

import requests
import json
import argparse
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import time
import os

 

#retry mechanism for http request
def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def _log(msg):
    """ utility method for logging progress
        TODO: use python logging library """
    print(f"{datetime.now()} - {msg}")


def create_alert_in_xiteit(alert_data, alert_severity):
    #alerts are being send with the same API token as Nodeping so the same alert will update.
    xiteit_url = 'https://app.xiteit.co:8080/'
    api_url = xiteit_url + 'api/alerts/?format=json'
    headers = {'Authorization': 'Token a7e4295ccdaf8520c478bd9fc9e42473e9b5ec04',
               'Content-Type': 'application/json'}
    token = '111aa5e9e09751024fa3298f262cf5878ba5c832'
    alert_payload = {
        **alert_data,
        "status": alert_severity,
        "token": token
    }

    _log("Info - Sending alert to XiteiT")
    response = requests.post(api_url, headers=headers, json=alert_payload)
    if response.status_code != 200:
        _log('Error - could not create event on XiteiT')
        print("Script failed on line 65")
        exit(2)
    else:
        _log("Info - Event Created on XiteiT")
        return

# this func triggers job on Camilyo jenkins that restrtes the FE servers
def trigger_camilyo_jenkins(jenkins_farm,jenkins_host):

    cert = "noCertificateCheck"
    build = "itzik-dev"
    os.system(f"java -jar /opt/scripts/camilyo/jenkins-cli.jar -{cert} -s https://jenkins.develop.camilyo.net:8443 -auth automation@camilyo.com:11b935bdda37df6fcfd61ab89cf0cd01e1 build {build} -p FARM={jenkins_farm} -p HOST={jenkins_host} -s > test_output.txt")
    
    with open("test_output.txt") as job_result:
        lines = [line.strip('\n') for line in job_result.readlines()]
       
    return (lines)

    

_log("---Starting---")


_log("Info - Getting alert info")
# parsing the parametes from Jenkins

parser = argparse.ArgumentParser('Parameters from XiteiT Alert.')

parser.add_argument('--host', help='XiteiT alert host')
parser.add_argument('--service', help='XiteiT alert service')
parser.add_argument('--site_url', help='Alert site URL - under Camilyo domain')
parser.add_argument('--ticket_id', help='XiteiT Alert ticket ID')

args = parser.parse_args()
# Set args
host = args.host
service = args.service
site_url = args.site_url
ticket_id = args.ticket_id

site_url = str(site_url)

# setting alert info for XiteiT
alert_data = {'host': host,
              'check_type': service,
              'site_url': site_url,
              'ticket_id': ticket_id
              }

# cutting the url and adding http
raw_url = site_url.split('//')[1]
http_url = f'http://{raw_url}'
url_list = [http_url, site_url]
# flags for later conditions
http_up = 0
https_up = 0
up = 0
down = 0

#print XiteiT ticket_id for debug
_log(f"Info - XiteiT Alert ID is {ticket_id}")

_log("Info - Checking endpoints")
for url in url_list:
    t0 = time.time()
    response = None
    try:
        response = requests_retry_session().get(url, timeout=5)
    except Exception as x:
        if not response:
            down = (down + 1)
            pass
        else:
            print(f'Error - request faild on {url}', x.__class__.__name__)
            print('Sctipt failed on line 133')
            exit(2)
    else:
        _log(f'Info - managed to execute GET request')
        t1 = time.time()
        t2 = (t1-t0)
        _log(f'Info - request took {t2} seconds')
        if response.status_code != 200:
            _log(f'Error - url {url} is down or Forbidden. status code is {response.status_code}')
        else:
            up = (up + 1)
            _log(f'Info - url {url} is up. status code is {response.status_code}')
            if (url == http_url):
                http_up = (http_up + 1)
            else:
                https_up = (https_up + 1)

# print("http_up=",http_up)
# print("https_up=",https_up)
# print("up=",up)
# print("down=",down)

if (https_up == 0 and http_up == 1):
    _log("Error - https site is down, server need to be restarted")
    #preparing the params to trigger Camilyo jenkins
    jenkins_farm = host.split('-')[0]
    jenkins_host = host.split('-')[1]

    job_status = trigger_camilyo_jenkins(jenkins_farm,jenkins_host)
    if "SUCCESS" in job_status[1]:
        _log("Info - Camilyo Jenkins Job ended with success")
        create_alert_in_xiteit(
                            alert_data={
                            **alert_data,
                            "output": "Jenkins job end with success - restating the host"
                            },
                            alert_severity = "https_down"
                            )
        exit()
    else:
        alert_severity = "Disaster"
        _log("Error - Camilyo Jenkins Job faild, need to contact Camilyo On-call")
        create_alert_in_xiteit(
                            alert_data={
                            **alert_data,
                            "output": "Jenkins job failed"
                            },
                            alert_severity = "Disaster"
                            )
        exit()


if (https_up == 0 and http_up == 0):
    # sending alert to XiteiT
    _log("Error - Both sites are down, need to contact the On-call")
    create_alert_in_xiteit(
                            alert_data={
                            **alert_data,
                            "output": "both HTTP and HTTPS are down"
                            },
                            alert_severity = "Disaster"
                            )
    
    exit()

if (https_up == 1 and http_up == 0):
    _log("Info - https site is up and http site is down, recovering alert on XiteiT")
    create_alert_in_xiteit(
                            alert_data={
                            **alert_data,
                            "output": "https site is up and http site is down"
                            },
                            alert_severity = "Recovery"
                            )
    exit()

if (up == 2):
    _log("Info - Both sites are up, recovering alert on XiteiT")
    create_alert_in_xiteit(
                            alert_data={
                            **alert_data,
                            "output": "Both sites are up"
                            },
                            alert_severity = "Recovery"
                            )
    exit()
