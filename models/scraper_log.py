import json
from odoo import models, fields, api, _
import logging
import base64
import io
import pandas as pd

_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError,UserError

class ScraperLog(models.Model):
    _name = "scraper.log"
    _description = "Scraper Log"

    name = fields.Char(
        default='New', 
        readonly=True,
        help="Auto-generated name for the log entry. Defaults to 'New' and is automatically set."
    )
    scraper_store_id = fields.Many2one(
        'scraper.store', 
        string="Store",
        help="The competitor store associated with this log entry."
    )
    store_url = fields.Char(
        string="Store URL",
        help="The URL of the competitor's store that was scraped."
    )
    mapping_id = fields.Many2one(
        'scraper.field.mapping',
        help="Field mapping configuration used for this scraping operation."
    )
    store_data_id = fields.Many2one(
        'scraped.store.data',
        help="Reference to the scraped data associated with this log entry."
    )
    active = fields.Boolean(
        default=True,
        help="Indicates if this log entry is active. Uncheck to archive instead of deleting."
    )
    store_request_id = fields.Many2one(
        'scraper.request',
        string="Store Request ID",
        help="The original scraping request that generated this log entry."
    )
    response_json = fields.Text(
        required=True,
        help="Raw JSON response data from the scraping operation. Contains the complete scraped data."
    )
    excel_file = fields.Binary(
        string="Scraped Data Excel",
        readonly=True,
        help="Excel file containing the formatted scraped data for download."
    )
    excel_filename = fields.Char(
        string="Excel Filename",
        readonly=True,
        help="Name of the generated Excel file containing scraped data."
    )
    request_payload = fields.Text(
        help="The original request payload sent for the scraping operation."
    )
    error_message = fields.Text(
        help="Detailed error message if the scraping operation failed."
    )
    processed = fields.Boolean(
        default=False,
        help="Indicates whether the scraped data has been processed."
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('data_validated', 'Data Validated'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partially_processed', 'Partially Processed')
    ], 
    default='draft',
    help="""Current status of the scraping log:
    - Draft: Initial state when log is created
    - Data Validated: Scraped data has been validated
    - Success: Data was successfully processed
    - Failed: Scraping or processing failed
    - Partially Processed: Some data was processed successfully"""
    )

    created_at = fields.Datetime(
        default=fields.Datetime.now,
        help="Timestamp when this log entry was created."
    )

    def action_generate_excel(self):    
        for rec in self:
            try:
                if not rec.response_json:
                    if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"You have not json data for import In Excel.",
                            'status': 'failed'
                            })                                          
                    else :
                        rec.write({
                            'error_message' : f"You have not json data for import In Excel.", 
                            'status': 'failed'
                            }) 
                    break 

                payload = json.loads(rec.response_json)
                store_data = payload.get("store_data", [])
                rows = []
                for store in store_data:
                    row = {}
                    for key, value in store.items():
                        if key == "data":
                            continue
                        row[f"store_{key}"] = value

                    data_block = store.get("data", {})
                    for key, value in data_block.items():
                        row[f"data_{key}"] = value

                    rows.append(row)
                df = pd.DataFrame.from_records(rows)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="Store Data")
                buffer.seek(0)
                rec.excel_file = base64.b64encode(buffer.read())
                store_name = rec.scraper_store_id.name.replace(' ', '_').lower() if rec.scraper_store_id else 'unknown_store'
                rec.excel_filename = f"scraping_{store_name}_{rec.id}.xlsx"

            except Exception as e:
                if rec.error_message:
                    rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"Generate Excel Error : {str(e)}",
                            'status': 'failed'
                            })                    
                else :
                    rec.write({
                            'error_message' : f"Generate Excel Error : {str(e)}" ,
                            'status': 'failed'
                            })     

    def update_bab_product_id_from_mapping(self):
        for rec in self:
            if not rec.competitor_product:
                if rec.error_message:
                    rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"'Store product' is missing in data",
                            'status': 'failed'
                            })                    
                else :
                    rec.write({
                            'error_message' : f"'Store product' is missing in data",
                            'status': 'failed'
                            })    
                break
             

            pro_map_line_id = self.env['product.mapping.lines'].search([
                ('scraper_store_id', '=', rec.scraper_store_id.id),
                ('json_product_key', '=', rec.competitor_product)], limit=1)

            if pro_map_line_id and pro_map_line_id.product_id:
                rec.bab_product_id = pro_map_line_id.product_id.id

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('scraper.log') or 'New'
        return super().create(vals)

    def validate_pre_store_data(self):
        for rec in self:
            if not rec.scraper_store_id:
                if rec.error_message:
                    rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"Store is missing",
                            'status': 'failed'
                            })                    
                else :
                    rec.write({
                            'error_message' : f"Store is missing",
                            'status': 'failed'
                            })    
                break
         
            if not rec.mapping_id:
                mapping_id = self.env['scraper.field.mapping'].search([('scraper_store_id', '=', rec.scraper_store_id.id)])
                if mapping_id:
                    rec.mapping_id = mapping_id.id
                else:
                    if rec.error_message:
                        rec.write({
                                'error_message' : rec.error_message + "\n\n" + f"'Scrapper Field Mapping' record is missing for '%s' store, {rec.scraper_store_id.name}",
                                'status': 'failed'
                                })                    
                    else :
                        rec.write({
                                'error_message' : f"'Scrapper Field Mapping' record is missing for '%s' store, {rec.scraper_store_id.name}",
                                'status': 'failed'
                                })    
                    break

            rec.validate_response_json()
           

    def generate_store_data(self):
        for rec in self:            
            try:
                if not rec.store_data_id:
                    store_data = {
                        'log_id': rec.id,
                        'scraper_store_id': rec.scraper_store_id.id or False,
                        'mapping_id': rec.mapping_id.id or False,
                        'raw_response_data': self.response_json or '',
                        'store_request_id' : rec.store_request_id.id
                         }
                    if store_data:
                        rec.store_data_id = self.env['scraped.store.data'].create(store_data)
                    rec.status = 'success'
                
                else:                
                    if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"'Store Data' record is already exist '%s' for '%s' log , {rec.store_data_id.name}, {rec.name}.",
                             'status': 'success'
                            })                    
                    else :
                         rec.write({
                            'error_message' : f"'Store Data' record is already exist '%s' for '%s' log , {rec.store_data_id.name}, {rec.name}.",
                            'status': 'success'
                            }) 

            except Exception as e:
                if rec.error_message:
                    rec.write({
                        'error_message' : rec.error_message + "\n\n" + f"Invalid JSON format.\n\nError: {str(e)}",
                        'status': 'failed'
                        })                    
                else :
                    rec.write({
                            'error_message' : f"Invalid JSON format.\n\nError: {str(e)}",
                            'status': 'failed'
                            })    
              

    def validate_response_json(self):
        for rec in self:
            if not rec.response_json:
                if rec.error_message:
                    rec.write({
                        'error_message' : rec.error_message + "\n\n" + f"Response JSON cannot be empty.",
                        'status': 'failed'
                        })                    
                else :
                    rec.write({
                            'error_message' : f"Response JSON cannot be empty.",
                            'status': 'failed'
                            })    
                break
                
            try:
                data = json.loads(rec.response_json)
            except Exception as e:
                if rec.error_message:
                    rec.write({
                        'error_message' : rec.error_message + "\n\n" + f"Invalid JSON format.\n\nError: {str(e)}",
                        'status': 'failed'
                        })                    
                else :
                    rec.write({
                            'error_message' : f"Invalid JSON format.\n\nError: {str(e)}",
                            'status': 'failed'
                            })    
                break 
               

            if not isinstance(data, (list, dict)):
                if rec.error_message:
                    rec.write({
                        'error_message' : rec.error_message + "\n\n" + f"Response JSON must be a list or an object (dict).",
                        'status': 'failed'
                        })                    
                else :
                    rec.write({
                            'error_message' : f"Response JSON must be a list or an object (dict).",
                            'status': 'failed'
                            })    
                break 
                
            if isinstance(data, dict):
                if 'store_data' not in data:
                    if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"JSON object must contain an 'store_data' key.",
                            'status': 'failed'
                            })                    
                    else :
                        rec.write({
                                'error_message' : f"JSON object must contain an 'store_data' key.",
                                'status': 'failed'
                                })    
                    break                        

                elif not isinstance(data.get('store_data'), list):
                    if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"'items' must be a list of objects.",
                            'status': 'failed'
                            })                    
                    else :
                        rec.write({
                                'error_message' : f"'items' must be a list of objects.",
                                'status': 'failed'
                                })    
                    break       
                    

            if isinstance(data, list):
                for index, row in enumerate(data, start=1):
                    if not isinstance(row, dict):
                        if rec.error_message:
                            rec.write({
                                'error_message' : rec.error_message + "\n\n" + f"Row {index} is not a valid object (dict).",
                                'status': 'failed'
                                })                    
                        else :
                            rec.write({
                                    'error_message' : f"Row {index} is not a valid object (dict).",
                                    'status': 'failed'
                                    })    
                        break  
            
            rec.status = 'data_validated'          
