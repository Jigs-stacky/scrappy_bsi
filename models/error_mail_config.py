from odoo import models, fields

class ErrorMailConfig(models.Model):
    _name = 'error.mail.config'
    _description = 'Error Mail Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string="Subject"
    )

    email_from = fields.Char(default="Administrator <admin@bookabox.com>",string="From")
    email_cc = fields.Char(string="Cc")

    user_ids = fields.Many2many(
        'res.users',
        string="To(Partners)",
        help="Selected users will receive error log emails"
    )

    active = fields.Boolean(default=True)
