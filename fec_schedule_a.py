import requests
from requests.adapters import HTTPAdapter, Retry
import logging
from rich import inspect, print 
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import polars as pl
import json
from db_models import ScheduleA, FecLoadLog
from sqlmodel.sql.expression import Select, SelectOfScalar
from db_config import DbConfig
from typing import Optional, List, Union
from dataclasses import dataclass, field, MISSING
from db_dal_classes import SelectFecScheduleA, SelectFecCandidates,SelectFecCommittees, SelectOneFecScheduleA

from fec_inserter import InsertScheduleA, InsertLoadLog
from fec_dataclasses import DcScheduleA

import database_psql_procedures as sql
import time 

from sqlmodel import Field, Session, SQLModel, create_engine, select, or_, insert
engine = db_engine = DbConfig.get_central_engine()
    
SelectOfScalar.inherit_cache = True  # type: ignore
Select.inherit_cache = True  # type: ignore     
logging.basicConfig(level=logging.DEBUG)  


class WriteFiles:
    def __init__(self, committee_id, page):
        self.committee_id = committee_id
        self.page = page
    
    def write_file(self):
        with open(f'C:\\Users\\timko\code\\mkdocs_nadc\\{self.committee_id}.txt', 'a') as file:
            file.write(self.page)


API_KEY = '3A1Dq0EgwLLL7zXVJPKlU2XUS5AXxknVacIkDrX3'
payload = {'api_key': API_KEY}
BASE_URL = 'https://api.open.fec.gov/v1/'





def return_page_stats(page):
    num_pages = page['pagination']['pages']   
    if page['pagination']['last_indexes'] != None:    
        last_index = page['pagination']['last_indexes']['last_index']
        last_crd = None

    else:
        last_index = None
        last_crd = None
    per_page = page['pagination']['per_page']
    count = page['pagination']['count']
    return num_pages, last_index, last_crd, per_page, count

class RunMainCommittees:
    def __init__(self, committee_id):
        self.committee_id = committee_id
        self.URL = BASE_URL + 'schedules/schedule_a/'
        self.per_page = 100
     
    
    def example_retry(self):   
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 500, 502, 503, 504 ])
        payload = {'api_key': API_KEY,'committee_id':self.committee_id,'page':10,'per_page':self.per_page}      
        session.mount('https://', HTTPAdapter(max_retries=retries))

        # session.get("http://httpstat.us/503")        
        session.get(self.URL,params=payload)
        
   
    def specific_page(self):
        session = requests.Session()
        
        payload = {'api_key': API_KEY,'committee_id':self.committee_id,'page':10,'per_page':self.per_page}      
        req = session.get(self.URL,params=payload)
        print(req.request)
        
        # first_page = req.json()
        # print(req)
        # inspect(first_page)
        
        # num_pages = first_page['pagination']['pages']      
   
   
   
    def working_main(self):
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=3, status_forcelist=[ 500, 502, 503, 504 ])
        payload = {'api_key': API_KEY,'committee_id':self.committee_id,'page':1,'per_page':self.per_page}      
        session.mount('https://', HTTPAdapter(max_retries=retries))
        req = session.get(self.URL,params=payload)
        print(f'status code: {req.status_code}')
        first_page = req.json()
        # inspect(first_page)
        # input('stop')
        num_pages = first_page['pagination']['pages']    
        # last_index = first_page['pagination']['last_indexes']['last_index']
        # last_crd = first_page['pagination']['last_indexes']['last_contribution_receipt_date']
        # per_page = first_page['pagination']['per_page']
        # count = first_page['pagination']['count']
        yield first_page, 1
            
        for page in range(2, num_pages + 1):    
            print(f'page: {page}')
            payload = {'api_key': API_KEY,'committee_id':self.committee_id,'page':page,'per_page':self.per_page}     
            next_req = session.get(self.URL, params=payload)            
            print(f'status code: {next_req.status_code}')
            next_page = next_req.json()                 
            yield next_page, page

    def working_main_conductor(self):
        for this_page, page in self.working_main():
            time.sleep(3)
            print(f'page: {page}')
            # inspect(page)
            num_pages, last_index, last_crd, per_page, count = return_page_stats(this_page)
            ll = InsertLoadLog(committee_id=self.committee_id, page=page, num_pages=num_pages, last_index=last_index, last_crd=last_crd, per_page=per_page, count=count)
            ll.insert()
            # print(num_pages, last_index, last_crd, per_page, count)
            # print(page)
            for x in this_page['results']:
                z =json.dumps(x)
                # writer = WriteFiles(committee_id=self.committee_id, page=z)
                # writer.write_file()
                
                y = DcScheduleA.from_json(z)            
                go_thing = InsertScheduleA(dc_object=y)
                go_thing.insert()

class RunMainCandidates:
    def __init__(self, candidate_id):
        self.candidate_id = candidate_id
        self.URL = BASE_URL + 'schedules/schedule_a/'
        self.per_page = 100
        
    def working_main(self):
        session = requests.Session()
        payload = {'api_key': API_KEY,'candidate_id':self.candidate_id,'page':1,'per_page':self.per_page}      
        first_page = session.get(self.URL,params=payload).json()
        # print(first_page)
        num_pages = first_page['pagination']['pages']    
        # # print(first_page)
        yield first_page
            
        for page in range(2, num_pages + 1):    
            print(range.index)
            next_page = session.get(self.URL, params={'api_key': API_KEY,'candidate_id':self.candidate_id,'page':page,'per_page':self.per_page}).json()
            # print(next_page['pagination'])        
            yield next_page

    def working_main_conductor(self):
        for page in self.working_main():
            print(page.response())
            for x in page['results']:
                z =json.dumps(x)
                y = DcScheduleA.from_json(z)            
                go_thing = InsertScheduleA(dc_object=y)
                go_thing.insert()

        
def main_committees():
    
    x = SelectFecCommittees()
    committees = x.distinct_committees()     
    
    # x = SelectFecScheduleA()
    # committees = x.distinct_committees()    
        
    for committee in committees:
        # inspect(committee)
        x = RunMainCommittees(committee_id=committee.committee_id)
        print(committee.committee_id, committee.name)
        x.working_main_conductor()
       

def main_candidates():
    
    x = SelectFecCandidates()
    candidates = x.distinct_candidates()    
        
    for candidate in candidates:
        # inspect(candidate)
        x = RunMainCandidates(candidate_id=candidate)
        x.working_main_conductor()
        # print(candidate)


if __name__ == '__main__':
    # sql.truncate_generic_table(table_name='fec_schedule_a')
    main_committees()
    
    # x = RunMainCommittees(committee_id='C00721472')
    # x.example_retry()
    # x.working_main_conductor()
    # x.specific_page()
    main_candidates()
    