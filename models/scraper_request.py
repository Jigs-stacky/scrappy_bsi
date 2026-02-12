from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import uuid
import requests
from requests.auth import HTTPBasicAuth
import json
import ast

import time
import psycopg2
from psycopg2.extras import RealDictCursor


class ScraperRequest(models.Model):
    _name = 'scraper.request'
    _description = 'Scraper API Request'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='New', readonly=True, help="Auto-generated name for the scraper request. Defaults to 'New' and is automatically set.")
    request_id = fields.Char(readonly=True, copy=False, help="Unique identifier for the scraper request. Generated automatically.")
    active = fields.Boolean(default=True, help="Indicates whether the scraper request is active or not. Defaults to True.")
    scraper_store_id = fields.Many2one('scraper.store', string="Store", help="The store associated with the scraper request.")
    scraper_store_url = fields.Char(string = "URL", related='scraper_store_id.url', help="The URL of the competitor's website being scraped (read-only, derived from the selected store).")
    screepy_status = fields.Selection([('pending','Pending'),('completed','Completed'),('running','Running'),('failed','Failed')], help="Current status of the scraping job in the Scrapy system. Tracks the progress of the request.",string="Scrappy Status")
    screepy_request_id = fields.Char(string="Scrappy Request Id")

    response_json = fields.Text(help="Raw JSON response data received from the scraping request. Stores the complete response for reference.")
      
    request_generated_at = fields.Datetime(readonly=True, help="Timestamp when the request was generated.")
    scheduler_run_date = fields.Date(default=lambda self: fields.Date.today() + timedelta(days=1), help="Scheduled date for the scraping job to run. Defaults to tomorrow's date.")

    acknowledgment_at = fields.Datetime(readonly=True, help="Timestamp when the request was acknowledged.")
    response_received_at = fields.Datetime(readonly=True, help="Timestamp when the response was received.")

    error_message = fields.Text(
        help="Detailed error message if the scraping operation failed."
    ) 

    status = fields.Selection([
        ('draft', 'Draft'),
        ('inprogress', 'In Progress'),
        ('fetch_done', 'Fetch Done'),
        ('logged_data', 'Log Generated'),
        ('failed','Failed')
    ], default='draft', tracking=True, help="""Current status of the scraping request:
        - Draft: Initial state when request is created
        - In Progress: Scraping job is currently running
        - Fetch Done: Data has been successfully fetched
        - Log Generated: Scraping process completed and logs are available"""
    )

    _sql_constraints = [
        ('unique_request_id', 'unique(request_id)', 'Request ID must be unique'),
    ]


    def cron_fetch_api_token(self):
        url = "http://91.98.233.239:8000/api/auth/login/"

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-CSRFTOKEN": "RiNbPiVwmfq9sVyH7cTYxbwIf4JN9SV8"
        }

        payload = {
            "username": "admin",
            "password": "admin"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()  # or response.json()
            self.env['ir.config_parameter'].sudo().set_param(
                'scrapper.tokens',
                data.get('access')
            )


    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'scraper.request'
            ) or 'REQ/NEW'
        return super().create(vals)

    def _archive_old_store_data(self):
        for rec in self:
            if rec.status == 'draft':
                continue

            store_domain = rec.scraper_store_id
            request_id = rec.request_id

            self.env['scraped.store.data'].search([
                ('scraper_store_id', '=', store_domain.id),
                ('active', '=', True),
                ('store_request_id', '!=', rec.id),
            ]).write({'active': False})
            self.env['scraped.store.data.line'].search([
                ('scraper_store_id', '=', store_domain.id),
                ('active', '=', True),
                ('store_request_id', '!=', rec.id),
            ]).write({'active': False})
            self.env['scraper.log'].search([
                ('scraper_store_id', '=', store_domain.id),
                ('active', '=', True),
                ('store_request_id', '!=', rec.id),
            ]).write({'active': False})
            self.search([
                ('scraper_store_id', '=', rec.scraper_store_id.id),
                ('active', '=', True),
                ('screepy_request_id', '!=', request_id),
            ]).write({'active': False})

            rec.active = True


    def action_send_request(self):
        for rec in self:
            if rec.status != 'draft':
                continue

            try:
                rec.request_id = f"REQ-{uuid.uuid4().hex[:10].upper()}"  
               
                token = rec.env['ir.config_parameter'].sudo().get_param('scrapper.tokens')
               
                headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                }
              
                if not rec.scraper_store_id:
                    if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"You Dont Have Select Scrapper Store ID",
                            'status': 'failed'
                            })
                    else :
                       rec.write({
                            'error_message' : f"You Dont Have Select Scrapper Store ID",
                            'status': 'failed'
                            })
                    break
                    

                payload = {
                    "domain_id": rec.scraper_store_id.domain 
                }
              
                endpoint = "http://91.98.233.239:8000/api/scraping/start/"
                
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
    
                if response.status_code != 200:
                    if rec.error_message:
                        rec.write({
                            'error_message' :  rec.error_message + "\n\n" + f"Response Status : {response.status_code} \nResponse Text {response.text}",
                            'status': 'failed'
                            })                        
                    else:                       
                        rec.write({
                            'error_message' : f"Response Status {response.status_code} \nResponse Text {response.text}",
                            'status': 'failed'
                            })
                    break

                rec.screepy_status = response.json().get('status')
                rec.screepy_request_id = response.json().get('request_id')                    

                rec.write({
                    'status': 'inprogress',
                    'request_generated_at': fields.Datetime.now(),
                })
                rec._archive_old_store_data()
              
            except requests.exceptions.RequestException as e:
                if rec.error_message:
                    rec.write({
                            'error_message' :  rec.error_message + "\n\n" + f"Scraper server is unreachable.\n\n{str(e)}",
                            'status': 'failed'
                            })
                else :
                    rec.write({
                        'error_message' : f"Scraper server is unreachable.\n\n{str(e)}",
                        'status': 'failed'
                        })
                   

    def scrapy_fetch_data(self):
        for rec in self:            
            try:
                if rec.screepy_status != "completed":
                    url = "http://91.98.233.239:8000/api/scraping-requests"
                    token = rec.env['ir.config_parameter'].sudo().get_param('scrapper.tokens')
                    params = {"request_id": rec.screepy_request_id}
                    headers = {
                                "Authorization": f"Bearer {token}",
                                "Accept": "application/json",                               
                    }
                    response = requests.get(url, params=params,headers=headers, timeout=150)
                                        

                    if response.status_code != 200:
                        if rec.error_message:
                            rec.write({
                                'error_message' : rec.error_message + "\n\n" + f"Response Status {response.status_code}",
                                'status': 'failed'
                                })                           
                        else :
                            rec.write({
                                'error_message' : f"Response Status {response.status_code} \nResponse Text {response.text}",
                                'status': 'failed'
                                }) 
                        break

                    
                    results = response.json().get('results')
                    print("\n\n\n result ====",results)
                    if not results:
                        if rec.error_message:
                            rec.error_message = rec.error_message + "\n\n" + f"No scraping data found."
                        else :
                            rec.error_message = f"No scraping data found."
                        break

                    rec.screepy_status =  results[0]['status']

                if rec.screepy_status == "completed":
                    rec._fetech_data()  
                else:
                    rec.response_json = False
                
            except Exception as e:                 
                if rec.error_message:
                    rec.write({ 
                        'error_message' : rec.error_message + "\n\n" + f"Data Fetching Status Error :  {str(e)}",
                        'status': 'failed'
                        })  
                else :
                    rec.write({
                        'error_message' : f"Data Fetching Status Error :  {str(e)}",
                        'status': 'failed'
                        })  
                
    def _fetech_data(self):
        for rec in self:
            try:
                if not rec.screepy_request_id:
                    rec.write({
                        'error_message' : f"You Have not Screepy Request Id For Fetching Data",
                        'status': 'failed'
                        })
                    break

                url = "http://91.98.233.239:8000/api/store-data"
                token = rec.env['ir.config_parameter'].sudo().get_param('scrapper.tokens')
                headers = {
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json",          
                    }
                params = {"scraping_request": rec.screepy_request_id,'page_size':100}
        
                response = requests.get(url,headers=headers, params=params, timeout=15)       
                
                if response.status_code != 200:
                    if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"Response Status {response.status_code}",
                            'status': 'failed'
                            })
                    else :
                        rec.write({
                            'error_message' : f"Response Status {response.status_code}",
                            'status': 'failed'
                            })
                    break
                data = response.json()
                total_pages = data.get('total_pages')
                page_size = data.get('page_size')
                
                store_data = [] 
                if total_pages and total_pages > 1:                    
                    for page in range(2,total_pages+1):            
                        response_data = rec._next_page_data_fetches(page,page_size,rec.screepy_request_id)
                        if response_data:                            
                            store_data.extend(response_data)

                    if store_data:
                        data['store_data'].extend(store_data)                
                        json_data = json.dumps(data)                      
                        rec.write({
                                "response_json" : json_data,
                                "status" : "fetch_done",
                                "acknowledgment_at" : fields.Datetime.now(),
                            })  
                            
                else:
                    json_data = json.dumps(data)                      
                    rec.write({
                            "response_json" : json_data,
                            "status" : "fetch_done",
                            "acknowledgment_at" : fields.Datetime.now(),
                        })  
                            
            except Exception as e:
                if rec.error_message:
                    rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"Fetching Data Error : {str(e)}",
                            'status': 'failed'
                            })
                else :
                    rec.write({
                            'error_message' : f"Fetching Data Error : {str(e)}",
                            'status': 'failed'
                            })
    
    def _next_page_data_fetches(self,page,page_size,request):
        for rec in self:
            try :
                url = "http://91.98.233.239:8000/api/store-data"
                token = self.env['ir.config_parameter'].sudo().get_param('scrapper.tokens')
                headers = {
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json",          
                    }
                params = {"page" :page,"scraping_request": request,"page_size":page_size}

                response = requests.get(url,headers=headers, params=params, timeout=15)
                if response.status_code != 200:
                    if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"Response Status {response.status_code}",
                            'status': 'failed'
                            })
                    else :
                        rec.write({
                            'error_message' : f"Response Status {response.status_code}",
                            'status': 'failed'
                            })

                    return False

                data = response.json()                
                return data.get('store_data')

            except Exception as e:
                    if rec.error_message:
                        rec.write({
                                'error_message' : rec.error_message + "\n\n" + f"Fetching Data Error : {str(e)}",
                                'status': 'failed'
                                })
                    else :
                        rec.write({
                                'error_message' : f"Fetching Data Error : {str(e)}",
                                'status': 'failed'
                                })


    def scrapy_log_generate(self):
        for rec in self:
            try :
                if rec.response_json:
                    log_id = self.env['scraper.log'].create({
                            'scraper_store_id': rec.scraper_store_id.id,
                            'store_url' : rec.scraper_store_url,
                            'store_request_id' : rec.id,
                            'response_json' : rec.response_json
                    })
                    if log_id:
                        rec.write({
                            "status" : "logged_data",
                            "response_received_at" : fields.Datetime.now(),
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Success',
                                'message': 'logged Data Succefully Imported.',
                                'type': 'success',   # success | warning | danger | info
                                'sticky': False,    
                                }
                            }
                else :
                    if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"You have not json data for import In Log."                          
                            })                       
                    else :
                         rec.write({
                            'error_message' : f"You have not json data for import In Log."                          
                            })
                    break
                  
            except Exception as e:
                if rec.error_message:
                    rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"Import Log Error : {str(e)}"                      
                            })   
                else :
                    rec.write({
                            'error_message' : f"Import Log Error : {str(e)}"                      
                            })  
                   