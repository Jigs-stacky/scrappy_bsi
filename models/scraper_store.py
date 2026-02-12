from odoo import models, fields
import requests
from odoo.exceptions import ValidationError, UserError

class ScraperStore(models.Model):
    _name = 'scraper.store'
    _description = 'Store'

    name = fields.Char(default='New', help="The name of the competitor store. Defaults to 'New' if not specified.")
    url = fields.Char(string = "URL", help="The base URL of the competitor's website that will be scraped for data.")
    domain = fields.Integer(string="Domain ID",readonly=False, help="Unique identifier for the store's domain in the external system. Used for API integration.")
    active = fields.Boolean(string='Active', default=True, help="If checked, the store is active and can be used for scraping.")
    data_type = fields.Selection(
        [
            ('manual', 'Manual'),
            ('scrapy', 'Scrapy'),
        ],
        string="Data Type",
        default='scrapy',
        required=True
    )
    
    def scraper_store_domain(self):
        for rec in self:
            url = "http://91.98.233.239:8000/api/domains"
            token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY3NjE2MjE0LCJpYXQiOjE3NjcwMTE0MTQsImp0aSI6Ijk3NTcxZDgwN2MxMjQ5MzNiMThiZDIwNzY2OGUwZTI2IiwidXNlcl9pZCI6IjEifQ.aPTS3z4xwwpiLm6PHWRWF9n7tEILXINgsW5TzPBooZA"
            )
            headers = {
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",          
                }
          
            try:
                response = requests.get(url,headers=headers, timeout=15)            
                if response.status_code != 200:
                    raise UserError(f"Failed to fetch store data: {response.status_code}\n{response.text}")  
        
                for item in response.json().get("results", []):
                    shop_id = self.search([('name','=',item["name"]),('domain','=',item["id"])])
           
                    if not shop_id:
                        self.create({
                              'name' : item["name"],
                              'domain' : item["id"],
                         })
            except Exception as e:
                    return {
                        "error": True,
                        "message": str(e)
                    }
