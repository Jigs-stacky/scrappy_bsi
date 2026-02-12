from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import re
from odoo.tools.safe_eval import safe_eval
from dateutil import parser

class ScrapedStoreData(models.Model):
    _name = 'scraped.store.data'
    _description = 'Scraped Store Data'

    name = fields.Char(
    default='New', 
    readonly=True,
    help="Auto-generated name for the scraped data record. Defaults to 'New' and is automatically set."
    )
    scrape_date = fields.Date(
        default=fields.Date.today,
        help="The date when the data was scraped. Defaults to the current date."
    )
    scrape_datetime = fields.Datetime(
        default=fields.Datetime.now,
        help="The exact date and time when the data was scraped."
    )

    log_id = fields.Many2one(
        'scraper.log',
        help="Reference to the scraper log entry that generated this data."
    )
    scraper_store_id = fields.Many2one(
        'scraper.store', 
        string="Store",
        help="The competitor store from which this data was scraped."
    )
    mapping_id = fields.Many2one(
        'scraper.field.mapping',
        help="The field mapping configuration used for processing this scraped data."
    )
    store_request_id = fields.Many2one(
        'scraper.request',
        string="Store Request ID",
        help="The scraping request that initiated this data collection."
    )

    line_ids = fields.One2many(
        'scraped.store.data.line', 
        'scraped_store_data_id',
        help="Individual data lines containing the scraped product information."
    )
    raw_response_data = fields.Text(
        'Raw Response Data', 
        readonly=True,
        help="The complete raw JSON response from the scraping operation."
    )
    active = fields.Boolean(
        default=True,
        help="Indicates if this record is active. Uncheck to archive instead of deleting."
    )
    error_message = fields.Text(
        help="Detailed error message if the scraping operation failed."
    ) 

    status = fields.Selection([
                ('draft','Draft'),               
                ('completed','Completed'),
                ('failed','Failed'),
                ],
                default='draft',
                help="Status Of the Scrapped Store Data"            
            )
    data_type = fields.Selection(
        related='scraper_store_id.data_type',
        store=True,
        readonly=True
    )

    store_plan = fields.Selection(related='mapping_id.store_plan',string='Store Plan Duration')
    
    def all_store_plan_price_calculate(self):
        for rec in self:            
            for line in rec.line_ids:
                line.store_plan_price_calculate()

    def all_per_m2_monthly_price_calculate(self):
        for rec in self:            
            for line in rec.line_ids:
                line.per_m2_monthly_price_calculate()
    
    def update_all_bab_product_id_from_mapping(self):
        for rec in self:
            for line in rec.line_ids:
                line.update_bab_product_id_from_mapping()
            rec.write({
                'status': 'completed'
                })

    def update_all_location_details(self):
        for rec in self:
            for line in rec.line_ids:
                line.update_location_details()

    def update_all_bab_product_price_plan_from_mapping(self):
        for rec in self:
            for line in rec.line_ids:
                line.get_subscription_pricing_from_plan()


    def all_avg_price_manipulations(self):
        for rec in self:
            for line in rec.line_ids:
                line.avg_price_manipulations()
            rec.write({
                'status' : "completed"
                })

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = (
                self.env['ir.sequence'].next_by_code('scraped.store.data')
                or 'New'
            )
        return super(ScrapedStoreData, self).create(vals)

    def validate_store_data(self):
        for rec in self:
            if not rec.log_id or not rec.log_id.response_json:
                if rec.error_message:
                        rec.write({
                            'error_message' : rec.error_message + "\n\n" + f"No log data available to import.",
                            'status': 'failed'
                            })                                          
                else :
                    rec.write({
                        'error_message' : f"No log data available to import.", 
                        'status': 'failed'
                        }) 
                break 
              
            if not rec.mapping_id:
                if rec.error_message:
                    rec.write({
                        'error_message' : rec.error_message + "\n\n" + f"Please select a mapping configuration before importing.",
                        'status': 'failed'
                        })                                          
                else :
                    rec.write({
                        'error_message' : f"Please select a mapping configuration before importing.", 
                        'status': 'failed'
                        }) 
                break 
                

            # Clear existing lines
            if rec.line_ids:
                rec.line_ids.unlink()

            # Store raw data
            rec.write({'raw_response_data': rec.log_id.response_json})


    def import_from_logs(self):
        for rec in self:
            rec.validate_store_data()           
            try:
                data = json.loads(rec.log_id.response_json)                 
                # Create new lines
                line_vals = []
                
                if data.get('store_data'):
                    data = data.get('store_data')            
                
                    for item in data:
                        if not isinstance(item, dict):
                            continue                        
                            
                        line_val = {                          
                            'bab_product_id': False,
                            'bab_price': 0.0,
                            'scrappy_id' : '',
                            'scraped_store_data_id': self.id or False,
                            'scraper_store_id': self.scraper_store_id.id or False,
                            'competitor_product': '',
                            'competitor_price': 0.0,
                            'store_location': '',
                            'product_category': '',
                            'plan': '',
                            'timeframe': '',
                            'per_day_amount': 0.0,
                            'discounted_per_day_amount': 0.0,
                            'insurance': 0.0,
                            'str_discounted_per_day_amount' : '',
                            'str_per_day_amount' : '',
                            'str_insurance' : '',
                            'str_competitor_price': '',
                            'store_location_id' : False,
                            'timestamp':False,
                            'billing_cycle' : '',
                            'payment_plan' : ''
                        }
                                                                          
                        # Get all mappings for this mapping_id
                        for mapping_line in self.mapping_id.field_mapping_ids:
                            if not mapping_line.json_key or not mapping_line.target_field_id:
                                continue
                           
                            field_name = mapping_line.target_field_id.name
                            if field_name in line_val:
                                # Get the value from the item using the mapped JSON key
                          
                                json_keys = mapping_line.json_key
                                json_key_list = [v for v in json_keys.split(',')] if ',' in json_keys else [json_keys]

                                for json_key in json_key_list:
                                    value = item.get(json_key)                                    

                                    if field_name == 'store_location_id' and value:
                                        if mapping_line.python_code:                                   
                                            value = rec.apply_python_transform(mapping_line.python_code,value)                                                                                                      
                                        
                                        location_id = self.env['scraper.store.town'].search([('name','=',value)],limit=1)                                        
                                        if not location_id:
                                            location_id = self.env['scraper.store.town'].create({
                                                'scraper_store_ids' :  [(4, rec.scraper_store_id.id)] ,
                                                'name' : value
                                                })                                        
                                            line_val[field_name] = location_id.id
                                          
                                        else :
                                            location_id.scraper_store_ids = [(4, rec.scraper_store_id.id)]
                                            line_val[field_name] = location_id.id  
                                        break                                      
                                        

                                    if value :         
                                        if mapping_line.python_code:    
                                            python_value = rec.apply_python_transform(mapping_line.python_code,value)                                       
                                            line_val[field_name] = python_value
                                        else:      
                                            line_val[field_name] = value
                                        break            
                                    
                                    else:
                                        sub_item = item['data']
                                        
                                        if not sub_item:
                                            if rec.error_message:
                                                rec.write({
                                                    'error_message' : rec.error_message + "\n\n" + f"API In sub Item Data are not availabale. '{self.name}': {e}",
                                                    'status': 'failed'
                                                    })                                          
                                            else :
                                                rec.write({
                                                    'error_message' : f"API In sub Item Data are not availabale. '{self.name}': {e}", 
                                                    'status': 'failed'
                                                    }) 
                                            continue

                                        sub_value = sub_item.get(json_key)                                    
                                        if sub_value == 'In advance':                                           
                                            line_val['competitor_price'] = sub_item.get('Payment Unit Price')
                                            line_val[field_name] = sub_value                                            
                                            break
                                        
                                        if field_name == 'store_location_id' and sub_value:
                                            if mapping_line.python_code:                                   
                                                sub_value = rec.apply_python_transform(mapping_line.python_code,sub_value)                                                                                                      
                                            
                                            location_id = self.env['scraper.store.town'].search([('name','=',sub_value)],limit=1)                                        
                                            if not location_id:
                                                location_id = self.env['scraper.store.town'].create({
                                                    'scraper_store_ids' :  [(4, rec.scraper_store_id.id)] ,
                                                    'name' : sub_value
                                                    })                                        
                                                line_val[field_name] = location_id.id
                                              
                                            else :
                                                location_id.scraper_store_ids = [(4, rec.scraper_store_id.id)]
                                                line_val[field_name] = location_id.id  
                                            break



                                        if sub_value:                                                            
                                            if mapping_line.python_code:                                   
                                                python_value = rec.apply_python_transform(mapping_line.python_code,sub_value)                               
                                                line_val[field_name] = python_value
                                            else:                     
                                                line_val[field_name] = sub_value
                                            break

                        line_vals.append(line_val)

                if line_vals:
                    self.env['scraped.store.data.line'].create(line_vals)                    
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Import Complete'),
                        'message': _('Successfully imported %s items from logs.') % len(line_vals),
                        'type': 'success',
                        'sticky': False,
                    }
                }

            except Exception as e:
                if rec.error_message:
                    rec.write({
                        'error_message' : rec.error_message + "\n\n" + f"Import From Log mapping '{self.name}': {e}",
                        'status': 'failed'
                        })                                          
                else :
                    rec.write({
                        'error_message' : f"Import From Log mapping '{self.name}': {e}", 
                        'status': 'failed'
                        })       
                

        
    def apply_python_transform(self, python_code,value):
        """
        Apply user-defined python code on value safely
        """
        self.ensure_one()

        if not python_code and type(value) == int:
            return value

        local_dict = {
            'value': value,
            'result': value,
        }

        try:
            safe_eval(
                python_code,
                local_dict,
                mode="exec",
                nocopy=True
            )

            return local_dict.get('result')

        except Exception as e:
            if self.error_message:
                    self.write({
                        'error_message' : self.error_message + "\n\n" + f" Import From Log In Python Transform Error in mapping '{self.name}': {e}",
                        'status': 'failed'
                        })                                          
            else :
                self.write({
                    'error_message' : f"Import From Log In Python Transform Error in mapping '{self.name}': {e}", 
                    'status': 'failed'
                    })      
            

class ScrapedStoreDataLine(models.Model):
    _name = 'scraped.store.data.line'
    _description = 'Scraped Store Data Line'

    scraped_store_data_id = fields.Many2one(
        'scraped.store.data', 
        ondelete='cascade',
        help="Link to the parent scraped data record. If the parent is deleted, this line will be automatically removed."
    )
    store_request_id = fields.Many2one(
        'scraper.request',
        related="scraped_store_data_id.store_request_id",
        string="Request ID")

    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id,
        help="Currency used for all monetary values in this record."
    )

    bab_product_id = fields.Many2one(
        'product.product',
        help="The corresponding product in the BookABox system that matches this scraped product."
    )
    bab_price = fields.Float(
        help="The price of the product in the BookABox system."
    )
    active = fields.Boolean(
        default=True,
        help="Indicates if this record is active. Uncheck to archive instead of deleting."
    )
    timestamp = fields.Datetime(
        string="Timestamp",
        readonly=True,
        help="The exact date and time when this data line was created."
    )
    bab_company_id = fields.Many2one('res.company',string="Company",related="bab_product_id.company_id",store=True)

    scraper_store_id = fields.Many2one(
        'scraper.store', 
        string="Store",
        help="The competitor store from which this product data was scraped."
    )
    competitor_product = fields.Char(
        string="Store Product",
        help="The name or identifier of the product as it appears in the competitor's store."
    )
    competitor_price = fields.Float(
        "Store Price",
        help="Uom mapping competitor's Product Price",
        group_operator="avg"
    )
    old_competitor_price = fields.Float(
        string="Old competitor Price",
        help="Without Uom mapping competitor's Product Price"
        )

    scrappy_id = fields.Char(string="Scrappy Id") 

    district_id = fields.Many2one(
            "scraper.store.district",
            string="District",
            related="store_location_id.town_district_id",
            store=True,
        )
    town_name = fields.Char(string='Town Name', related="store_location_id.town_name",store=True)
    town_id = fields.Many2one('compititor.store.towns',related="store_location_id.town_id",store=True)
    address = fields.Char(string='Address', related="store_location_id.address",store=True)
    zip_code = fields.Char(string='Zip Code', related="store_location_id.zip_code",store=True)
    country_id = fields.Many2one("res.country",string="Country", related="store_location_id.country_id",store=True)
    state_id = fields.Many2one("res.country.state",string="State",related="store_location_id.state_id",store=True)
    per_meter_value = fields.Float(string="Per Meter Price", group_operator="avg",
        help="Competitor Product Per Meter Price"
        )

    per_m2_monthly_value = fields.Float(string="Per Meter/Monthly Price", group_operator="avg",
        help="Competitor Product Per Meter/Monthly Price"
        )

    billing_cycle = fields.Char(string="Billing Cycle")
    payment_plan = fields.Char(string="Payment Plan")

    # New fields
    store_location = fields.Char(
        string="Store Location",
        help="The physical location or branch of the store where the product is available."
    )
    store_location_id = fields.Many2one(
        'scraper.store.town',
        string="Store Location ID",
        help="Reference to the store's town/District in the system."
    )
    product_category = fields.Char(
        string="Product Category",
        help="The category of the product in the competitor's store."
    )
    plan = fields.Char(
        string="Plan",
        help="The subscription or rental plan associated with this product."
    )
    timeframe = fields.Char(
        string="Plan Duration",
        help="The duration or rental period for the product."
    )
    per_day_amount = fields.Float(
        string="Per Day Amount",
        help="The calculated daily rate for the product."
    )
    discounted_per_day_amount = fields.Float(
        string="Discounted Per Day Amount",
        help="The discounted daily rate for the product, if applicable."
    )
    insurance = fields.Float(
        string="Insurance",
        help="The insurance cost associated with the product rental."
    )
    product_price = fields.Float(
        string="AVG Product Price",
        help="The average price of the product, calculated based on area per meter and  Bab Area Product.",
        group_operator="avg"
    )
    week_plan_pricing = fields.Float(
        string="Week Plan Pricing",
        help="The pricing for a weekly rental plan of the product."
    )

    # String representation fields for display
    str_per_day_amount = fields.Char(
        string="STR Per Day Amount",
        help="String representation of the per day amount for display purposes."
    )
    str_discounted_per_day_amount = fields.Char(
        string="STR Discounted Per Day Amount",
        help="String representation of the discounted per day amount for display."
    )
    str_insurance = fields.Char(
        string="STR Insurance",
        help="String representation of the insurance cost for display."
    )
    str_competitor_price = fields.Char(
        "STR Store Price",
        help="String representation of the competitor's price for display."
    )
    data_type = fields.Selection(
        related='scraped_store_data_id.data_type',
        store=True,
        readonly=True
    )

    def apply_python_code_store_plan_pricing(self, python_code,plan,price):       
            self.ensure_one()
            if not python_code:
                return price

            local_dict = {
                'plan': plan,
                'price': price,
            }
            try:
                safe_eval(
                    python_code,
                    local_dict,
                    mode="exec",
                    nocopy=True
                )
                return local_dict

            except Exception as e:
                if self.error_message:
                        self.write({
                            'error_message' : self.error_message + "\n\n" + f" Import From Log In Python Transform Error in mapping '{self.name}': {e}",
                            'status': 'failed'
                            })                                          
                else :
                    self.write({
                        'error_message' : f"Import From Log In Python Transform Error in mapping '{self.name}': {e}", 
                        'status': 'failed'
                        })      



    def store_plan_price_calculate(self):  
        for rec in self:
            mapping_id = rec.scraped_store_data_id.mapping_id
            if mapping_id and mapping_id.store_plan and mapping_id.store_rent_plan_python_code:             
                value = rec.apply_python_code_store_plan_pricing(mapping_id.store_rent_plan_python_code,mapping_id.store_plan,rec.competitor_price)
                if value:
                    rec.per_day_amount = value.get('per_day_amount')

    def update_location_details(self):
        for rec in self:
            if rec.store_location_id:
                rec.store_location_id.adress_filtering()

    def extract_float_data(self, value):
        match = re.match(r"[\d,]+(\.\d+)?|[\d,]+", value)
        if not match:
            return None
        num_str = match.group()
        num_str = num_str.replace(',', '.')
        return float(num_str)

    def pricing_avg_find(self, pr_area, cm_area):
        avg_price = 0.0
        if self.competitor_price:
            avg_price = self.competitor_price
        elif self.str_competitor_price and cm_area and cm_area != 0:
            extracted_price = self.extract_float_data(self.str_competitor_price)
            if extracted_price is not None:
                avg_price = extracted_price / cm_area
        
        self.product_price = round(avg_price * pr_area, 2) if pr_area else 0.0 

    def update_bab_product_id_from_mapping(self):
        for rec in self:
            if rec.competitor_product:   
                try:               
                    company_mapping = False
                    product_ids = self.env['product.product']

                    if rec.store_location_id:
                        company_mapping = self.env['scraper.company.town.mapping'].search([
                            ('town_ids', 'in', rec.store_location_id.ids)
                        ], limit=1)


                    if company_mapping and company_mapping.company_id:
                        product_ids = self.env['product.product'].search([                  
                            ('company_id', '=', company_mapping.company_id.id)                    
                        ])

                    if product_ids:
                        store_pro_float = rec.extract_float_data(rec.competitor_product)
                        nearest_product = False
                        min_diff = float('inf')

                        for product in product_ids:
                            bab_pro_float = rec.extract_float_data(product.name)
                            if not bab_pro_float or not store_pro_float:
                                continue
                          
                            diff = abs(bab_pro_float - store_pro_float)
                            if diff < min_diff:
                                min_diff = diff
                                nearest_product = product

                        rec.bab_product_id = nearest_product.id if nearest_product else False
                        rec.bab_price =   rec.bab_product_id.lst_price if rec.bab_product_id else 0
                
                except Exception as e:
                    if rec.scraped_store_data_id.error_message:
                        rec.scraped_store_data_id.write({
                            'error_message' : rec.scraped_store_data_id.error_message + "\n\n" +f"Store Data line Update Product mapping : {e}",
                            })                                          
                    else :
                        rec.scraped_store_data_id.write({
                            'error_message' :f"Store Data line Update Product mapping : {e}",
                            })  
                        
            else:
                if rec.scraped_store_data_id.error_message:
                    rec.scraped_store_data_id.write({
                        'error_message' : rec.scraped_store_data_id.error_message + "\n\n" + f"Store Data line Store Product Not Assighned",
                        })                                          
                else :
                    rec.scraped_store_data_id.write({
                        'error_message' :f"Store Data line Store Product Not Assighned",
                        })                            

    def apply_subscription_python_transform(self, python_code,plan,billing_cycle,pricing,timeframe):
        """
        Apply user-defined python code on value safely
        """
        self.ensure_one()

        if not python_code :
            return value
        
        local_dict = {
            'plan': plan,
            'billing_cycle': billing_cycle,
            'pricing' : pricing,
            'timeframe' : timeframe    
        }

        try:
            safe_eval(
                python_code,
                local_dict,
                mode="exec",
                nocopy=True
            )
            return local_dict

        except Exception as e:
            if self.scraped_store_data_id.error_message:
                self.scraped_store_data_id.write({
                    'error_message' : self.scraped_store_data_id.error_message + "\n\n" + f"Store Data line , Python Transform Error in mapping apply_subscription_python_transform : {e}",
                    })                                          
            else :
                self.scraped_store_data_id.write({
                    'error_message' :f"Store Data line , Python Transform Error in mapping apply_subscription_python_transform : {e}",
                    }) 
           

    def get_subscription_pricing_from_plan(self):
        for rec in self:
            try:
                if (rec.plan and rec.plan == "one_time") or (rec.billing_cycle and rec.billing_cycle == 'Every 3 months') or (rec.payment_plan  and rec.payment_plan == 'In advance') :
                    rec.bab_product_id = False
                    rec.bab_price = 0

                elif rec.plan and (rec.plan == "Flexible" or rec.timeframe =="flexible monthly"):
                    if rec.scraped_store_data_id and rec.scraped_store_data_id.mapping_id:
                        mapping_id = rec.scraped_store_data_id.mapping_id
                        if mapping_id.plan_price_calulate_python_code:
                            value = rec.apply_subscription_python_transform(mapping_id.plan_price_calulate_python_code,rec.plan,rec.billing_cycle,rec.competitor_price,rec.timeframe)
                            print("\n\n\n value=",value)
                            if value:
                                rec.week_plan_pricing = value.get('weekly_price')
                                rec.competitor_price = value.get('result')
                        else:
                            rec.week_plan_pricing = 0

                elif rec.plan and rec.bab_product_id and rec.plan in ("Long-term", "monthly"):                 
                    mapping_line = self.env['subscription.plan.mapping.lines'].search([
                        ('json_uom_key', '=', rec.timeframe)
                    ], limit=1)
                   
                    if mapping_line:
                        pricing_id  = self.env['sale.subscription.pricing'].search([
                            ('product_template_id', '=', rec.bab_product_id.product_tmpl_id.id),
                            ('plan_id', '=', mapping_line.subscription_plan_id.id),
                        ], limit=1)                   
                       
                        if pricing_id:
                            rec.bab_price = pricing_id.price

                        else:
                            rec.bab_product_id = False
                            rec.bab_price = 0
                    else: #if mapping json key has not matched   
                        rec.bab_product_id = False    
                        rec.bab_price = 0

                else:                    
                    rec.week_plan_pricing = 0

            except Exception as e:
                    if rec.scraped_store_data_id.error_message:
                        rec.scraped_store_data_id.write({
                            'error_message' : rec.scraped_store_data_id.error_message + "\n\n" +f"Store Data line Plan Pricing error : {e}",
                            })                                          
                    else :
                        rec.scraped_store_data_id.write({
                            'error_message' :f" Store Data line Plan Pricing error : {e}",
                            }) 


    def apply_python_transform(self, python_code,size,value,bab_product,store_plan):
        """
        Apply user-defined python code on value safely
        """
        self.ensure_one()

        if not python_code :
            return value
        
        local_dict = {
            'value_size': size,
            'value_price': value,
            'store_plan':store_plan,
            'bab_product' : bab_product if bab_product else False        
        }

        try:
            safe_eval(
                python_code,
                local_dict,
                mode="exec",
                nocopy=True
            )
            return local_dict

        except Exception as e:
            if self.scraped_store_data_id.error_message:
                self.scraped_store_data_id.write({
                    'error_message' : self.scraped_store_data_id.error_message + "\n\n" +  f"Stor data line Python Transform Error in mapping : {e}",
                    })                                          
            else :
                self.scraped_store_data_id.write({
                    'error_message' : f"Stor data line Python Transform Error in mapping: {e}",
                    })
           
    def per_m2_monthly_price_calculate(self):
        for rec in self:
            value_size = rec.extract_float_data(rec.competitor_product)
            if rec.scraped_store_data_id.mapping_id.store_plan == 'week':
                rec.per_m2_monthly_value = round( (rec.competitor_price * 4) / value_size, 2)
            else:
                rec.per_m2_monthly_value = round(rec.competitor_price / float(value_size), 2)

    def avg_price_manipulations(self):
        for rec in self:
            if rec.bab_product_id and rec.per_day_amount:
                uom_days = rec.bab_product_id.uom_id.factor_inv
                if uom_days:
                    total_price = uom_days * rec.per_day_amount
                    if total_price != rec.competitor_price:
                        rec.old_competitor_price = rec.competitor_price
                        rec.competitor_price = total_price

            if rec.scraped_store_data_id and rec.scraped_store_data_id.mapping_id:                                        
                
                mapping_id = rec.scraped_store_data_id.mapping_id
                if mapping_id.price_calulate_python_code:
                    
                    value = rec.apply_python_transform(mapping_id.price_calulate_python_code,rec.competitor_product,rec.competitor_price,rec.bab_product_id.name,mapping_id.store_plan)
                    if value:                        
                        rec.product_price = value.get('result')
                        rec.per_meter_value = value.get('per_meter_value')

                else:
                    if rec.scraped_store_data_id.error_message:
                        rec.scraped_store_data_id.write({
                            'error_message' : rec.scraped_store_data_id.error_message + "\n\n" +f"Store Data line  Dont Have Any price manipulations related python code",
                            })                                          
                    else :
                        rec.scraped_store_data_id.write({
                            'error_message' : f"Store Data line  Dont Have Any price manipulations related python code",
                            })
                    
