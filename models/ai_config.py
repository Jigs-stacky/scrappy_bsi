from odoo import api, fields, models, _
import openai


class AiConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_key = fields.Char(string="Open Ai Secreat Api Key",config_parameter='scrapper.ai_key')
    keyword_trend_url = fields.Char(string="Keywords Trend Url",config_parameter='scrapper.keywords_url',default="https://api.hasdata.com/scrape/google-trends/search",readonly=True)   
    keywords_trend_api_key =  fields.Char(string="Keywords Trend Api Key",config_parameter='scrapper.keywords_key')            
    


