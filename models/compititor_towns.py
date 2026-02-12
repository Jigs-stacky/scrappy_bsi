from odoo import models, fields


class CompititorStoreTowns(models.Model):
    _name = 'compititor.store.towns'
    _description = 'Competitor Store Town'
   
    name = fields.Char(
        string='Town',
        help='Competitor Store Towns'
    )