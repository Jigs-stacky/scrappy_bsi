from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import re
import json

class ScraperFieldMapping(models.Model):
    _name = 'scraper.field.mapping'
    _description = 'Competitor Data Mapping'
    _rec_name = "scraper_store_id"

    scraper_store_id = fields.Many2one(
    'scraper.store', 
    string="Store",
    help="The competitor store this field mapping configuration belongs to."
    )
    store_url = fields.Char(
        string="Store URL",
        help="The base URL of the competitor's website being scraped."
    )

    field_mapping_ids = fields.One2many(
        'field.mapping.lines', 
        'scraper_field_mapping_id',
        string="Fields Mapping",
        help="Field mappings for basic product attributes like title, description, etc."
    )
    product_mapping_ids = fields.One2many(
        'product.mapping.lines', 
        'scraper_field_mapping_id',
        string="Product Mapping",
        help="Detailed product attribute mappings for product variants."
    )
    recurring_plan_mapping_ids = fields.One2many(
        'recurring.plan.mapping.lines', 
        'scraper_field_mapping_id',
        string="Recurring Plan Mapping",
        help="Mappings for recurring subscription plan details."
    )
    subscription_plan_mapping_ids = fields.One2many(
        'subscription.plan.mapping.lines', 
        'scraper_field_mapping_id',
        string="Subscription Plan Mapping",
        help="Mappings for subscription plan attributes and pricing."
    )
    price_calulate_python_code = fields.Text(
        help="Python code to calculate product prices from scraped data."
    )
    plan_price_calulate_python_code = fields.Text(
        help="Python code to calculate subscription/recurring plan prices from scraped data."
    )
    store_plan = fields.Selection([ 
                                    ('month','Per Month'),
                                    ('week','Per Week')], 
                                help="Manually Select For Store Planning",
                                string="Store Plan Duration",
                                )


    store_rent_plan_python_code = fields.Text(
        help="Python Code for Manual Selected Stor plan Duration To calculate per day price and monthly or weekly plan"
    )

    def extract_float_data(self, value):
        match = re.match(r"[\d,]+(\.\d+)?|[\d,]+", value)
        if not match:
            return None
        num_str = match.group()
        num_str = num_str.replace(',', '.')
        return float(num_str)

    def variant_run_simplified_pro_name(self):
        variants = self.env['product.product'].search([], order='id desc')
        for variant in variants:
            variant.run_simplified_pro_name()

    def lines_run_json_product_key_simplified_pro_name(self):
        for rec in self:
            if not rec.product_mapping_ids:
                raise ValidationError(_("Missing record in 'Product mapping Lines'"))
            for pro_line in rec.product_mapping_ids:
                if pro_line.json_product_key and not pro_line.no_auto_update:
                    store_pro_float = rec.extract_float_data(pro_line.json_product_key)
                    if store_pro_float:
                        pro_line.simplified_pro_name = store_pro_float

    def find_nearest_product(self, store_pro_float):
        products = self.env['product.product'].search([], order='id desc')
        nearest_product = False
        min_diff = float('inf')
        for product in products:
            try:
                diff = abs(float(product.simplified_pro_name) - store_pro_float)
                if diff < min_diff:
                    nearest_product = product
                    min_diff = diff
            except ValueError:
                continue
        return nearest_product

    def auto_fetch_related_products(self):
        for rec in self:
            if not rec.product_mapping_ids:
                raise ValidationError(_("Missing record in 'Product mapping Lines'"))
            for pro_line in rec.product_mapping_ids:
                if pro_line.json_product_key and pro_line.simplified_pro_name and not pro_line.no_auto_update:
                    nearest_product = rec.find_nearest_product(pro_line.simplified_pro_name)
                    if nearest_product:
                        pro_line.product_id = nearest_product.id
                       
    def run_all_product_mapping_lines_process(self):
        for rec in self:
            rec.variant_run_simplified_pro_name()
            rec.lines_run_json_product_key_simplified_pro_name()
            rec.auto_fetch_related_products()


class FieldMappingLines(models.Model):
    _name = 'field.mapping.lines'
    _description = 'Field Mapping Lines'

    scraper_field_mapping_id = fields.Many2one(
    'scraper.field.mapping',
    help="Link to the parent field mapping configuration this line belongs to."
    )
    scraper_store_id = fields.Many2one(
        'scraper.store', 
        related='scraper_field_mapping_id.scraper_store_id',
        help="The competitor store associated with this mapping (automatically set from parent)."
    )
    json_key = fields.Char(
        string="JSON Key",
        help="The key from the scraped JSON data that maps to the target field."
    )
    target_field_id = fields.Many2one(
        'ir.model.fields', 
        domain=[('model', '=', 'scraped.store.data.line')],
        help="The target field in the scraped data line model where the mapped data will be stored."
    )
    python_code = fields.Text(
        string='Python Code',
        help="""Python code to transform the scraped data before mapping.
        The scraped value is available in the 'value' variable.
        The final result should be assigned to 'result'."""
    )

    @api.model
    def _get_json_key_selection(self, log_id=False):
        """
        Dynamically extract unique keys from the selected scraper log JSON
        or the latest log if none is selected
        """
        domain = []
        if log_id:
            domain = [('id', '=', log_id)]
        else:
            domain = [('response_json', '!=', False)]
        
        log = self.env['scraper.log'].search(
            domain,
            order='created_at desc',
            limit=1
        )
        
        if not log or not log.response_json:
            return []

        try:
            data = json.loads(log.response_json)
        except Exception:
            return []

        keys = set()

        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    keys.update(row.keys())
        elif isinstance(data, dict):
            if 'items' in data and isinstance(data['items'], list):
                for row in data['items']:
                    if isinstance(row, dict):
                        keys.update(row.keys())
            else:
                keys.update(data.keys())

        return [(k, k) for k in sorted(keys)]


class ProductMappingLines(models.Model):
    _name = 'product.mapping.lines'
    _description = 'Product Mapping Lines'

    scraper_field_mapping_id = fields.Many2one(
    'scraper.field.mapping',
    help="Link to the parent field mapping configuration this product mapping belongs to."
    )
    scraper_store_id = fields.Many2one(
        'scraper.store', 
        related='scraper_field_mapping_id.scraper_store_id',
        help="The competitor store associated with this product mapping (automatically set from parent)."
    )
    json_product_key = fields.Char(
        string="JSON Product Key",
        help="The key from the scraped JSON data that identifies the product."
    )
    simplified_pro_name = fields.Float(
        string="Product Simplified Name",
        help="A numerical representation of the product name used for simplified matching."
    )
    product_id = fields.Many2one(
        'product.product',
        help="The Odoo product that corresponds to this mapping."
    )
    no_auto_update = fields.Boolean(
        string="No Auto Update",
        help="If checked, this mapping will not be automatically updated during sync operations."
    )


class RecurringPlanMappingLines(models.Model):
    _name = 'recurring.plan.mapping.lines'
    _description = 'Recurring Plan Mapping Lines'

    scraper_field_mapping_id = fields.Many2one(
    'scraper.field.mapping',
    help="Link to the parent field mapping configuration this recurring plan mapping belongs to."
    )
    scraper_store_id = fields.Many2one(
        'scraper.store', 
        related='scraper_field_mapping_id.scraper_store_id',
        help="The competitor store associated with this recurring plan mapping (automatically set from parent)."
    )
    json_uom_key = fields.Char(
        string="JSON Product Key",
        help="The key from the scraped JSON data that identifies the recurring plan's unit of measure."
    )
    recurring_plan_id = fields.Many2one(
        'sale.subscription.plan',
        help="The Odoo subscription plan that corresponds to this recurring plan mapping."
    )
    no_auto_update = fields.Boolean(
        string="No Auto Update",
        help="If checked, this recurring plan mapping will not be automatically updated during sync operations."
    )



class SubscriptionPlanMappingLines(models.Model):
    _name = 'subscription.plan.mapping.lines'
    _description = 'Subscription Plan Mapping Lines'

    scraper_field_mapping_id = fields.Many2one(
    'scraper.field.mapping',
    help="Link to the parent field mapping configuration this subscription plan mapping belongs to."
    )
    scraper_store_id = fields.Many2one(
        'scraper.store', 
        related='scraper_field_mapping_id.scraper_store_id',
        help="The competitor store associated with this subscription plan mapping (automatically set from parent)."
    )
    json_uom_key = fields.Char(
        string="JSON Product Key",
        help="The key from the scraped JSON data that identifies the subscription plan's unit of measure."
    )
    subscription_plan_id = fields.Many2one(
        'sale.subscription.plan',
        help="The Odoo subscription plan that corresponds to this mapping."
    )
    no_auto_update = fields.Boolean(
        string="No Auto Update",
        help="If checked, this subscription plan mapping will not be automatically updated during sync operations."
    )