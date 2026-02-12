from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
from io import BytesIO
import openpyxl


class ImportAddressWizard(models.TransientModel):
    _name = 'import.address.wizard'
    _description = 'Import Address from Excel'

    file = fields.Binary(string="Excel File", required=True)
    file_name = fields.Char()

    def action_import(self):
        if not self.file:
            raise ValidationError("Please upload an Excel file.")

        workbook = openpyxl.load_workbook(
            filename=BytesIO(base64.b64decode(self.file)),
            data_only=True
        )
        sheet = workbook.active

        Address = self.env['scraper.store.town']
        Town = self.env['compititor.store.towns']
        District = self.env['scraper.store.district']
        State = self.env['res.country.state']
        Country = self.env['res.country']
        Company = self.env['res.company']

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue  # skip empty rows

            row = row[:8]
            
            (
                name,
                town_name,
                district_name,
                state_name,
                zip_code,
                country_name,
                company_name,
                address
            ) = row


            # -------------------------
            # Many2one resolution
            # -------------------------

            address_id = Address.search([('name','=',name),('scraper_store_ids', 'in', [4])], limit=1)

            if address_id:
                town_id = Town.search([('name', '=', town_name)], limit=1)
                if town_id:
                    address_id.town_id = town_id.id
                else:
                    if town_name:
                        town_id = Town.create({'name': town_name})
                        address_id.town_id = town_id.id                    

                
                district_id = District.search([('name', '=', district_name)], limit=1)
                if district_id :
                    address_id.town_district_id = district_id.id
                else:
                    if district_name:
                        district_id = District.create({
                                'name': district_name                   
                            })                   
                        address_id.town_district_id = district_id.id


                country_id = Country.search([('name', '=', country_name)], limit=1)
                if country_id:
                    address_id.country_id = country_id.id
                
                state_id = State.search([('name', '=', state_name)], limit=1)
                
                if state_id:                  
                    address_id.state_id = state_id.id
                else:
                    if country_id and state_name:                        
                        state_id = State.create({
                            'name': state_name,
                            'code' : country_id.code + "".join(state_name.strip().split()[:2]),
                            'country_id' : country_id.id                    
                        })
                        address_id.state_id = state_id.id
                
                        
                if zip_code:
                    address_id.zip_code = zip_code
                if name:
                    address_id.address = name
                
                company_json_id = company_name
                mapping = self.env['scraper.company.town.mapping']
               
                old_company = address_id.company_id.id if address_id.company_id else False
                
                if old_company and old_company != company_json_id:
                    old_mapping = mapping.search(
                        [('company_id', '=', old_company)],
                        limit=1
                    )
                    if old_mapping:
                        old_mapping.town_ids = [(3, address_id.id)]
               
                if not address_id.company_id or address_id.company_id.id != company_json_id:
                    address_id.company_id = company_json_id
               
                new_mapping = mapping.search(
                    [('company_id', '=', company_json_id)],
                    limit=1
                )
                if new_mapping:
                    new_mapping.town_ids = [(4, address_id.id)]
               
                print("\n\n\n\n ----Address Successful---",name)
            else:
                print("\n\n\n\n ----Address failed---",name)
        
