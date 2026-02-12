from odoo import models, fields

class CompanyTownMapping(models.Model):
    _name = 'scraper.company.town.mapping'
    _description = 'Company Town Mapping'

    town_ids = fields.Many2many(
        'scraper.store.town',
        'company_store_town_rel',
        'company_id',
        'town_id',
        string='Competitor Towns',
        help="List of competitor towns/cities that are relevant for this company's market analysis."
    )

    company_id = fields.Many2one(
        'res.company',
        string='BAB Company',
        help="The BookABox company that this town mapping configuration belongs to."
    )