from odoo import models, fields, api
import re


class ProductProduct(models.Model):
    _inherit = 'product.product'

    competitor_data_count = fields.Integer(
    string="Competitor Data Count", 
    compute='_compute_competitor_data_count',
    help="Number of competitor price entries available for this product."
    )

    simplified_pro_name = fields.Float(
        string="Product Simplified Name",
        help="Numeric representation of the product name for easier matching and comparison."
    )

    product_avg_price = fields.Float(
        string="Avg Price Products",
        compute='_compute_product_price_avg',
        help="Average price of this product across all competitors for the current company's locations."
    )


    def _compute_product_price_avg(self):
       for product in self:
            company_id = product.env['scraper.company.town.mapping'].search([
                                        ('company_id','=',product.env.company.id)
                            ])
                  
            result = product.env['scraped.store.data.line'].read_group([
                                ('bab_product_id', '=', product.id),('store_location_id','in',company_id.town_ids.ids),
                                ('active','=',True)],
                                fields=['product_price:avg'], groupby=[])
                                  
            product.product_avg_price = result[0]['product_price'] if result else 0.0
                                     
            
    def run_simplified_pro_name(self):
        for rec in self:
            if rec.name:
                match = re.match(r"[\d,]+(\.\d+)?|[\d,]+", rec.name)
                if not match:
                    return None
                num_str = match.group()
                # Replace comma with dot
                num_str = num_str.replace(',', '.')
                value = float(num_str)
                rec.simplified_pro_name = value

    def _compute_competitor_data_count(self):
        for product in self:
            company_id = product.env['scraper.company.town.mapping'].search([
                                        ('company_id','=',product.env.company.id)
                            ])
            count = product.env['scraped.store.data.line'].search_count([
                    ('bab_product_id', '=', product.id),('store_location_id', 'in', company_id.town_ids.ids)])
            product.competitor_data_count = count

    def action_view_competitor_prices(self):
        self.ensure_one()
        company_id = self.env['scraper.company.town.mapping'].search([
                                        ('company_id','=',self.env.company.id)
                            ])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Scraped Competitor Data',
            'res_model': 'scraped.store.data.line',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref(
                    'bsi_competitor_scraper.view_scraped_store_data_line_tree'
                ).id, 'tree')
            ],
            'domain': [('store_location_id', 'in', company_id.town_ids.ids),('bab_product_id','=',self.id)],
            'context': {
                "search_default_group_by_store" : 1,"search_default_group_by_store_location" : 1
            }
        }
