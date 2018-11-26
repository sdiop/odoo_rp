# -*- coding: utf-8 -*-
# by khk
from odoo import fields, models, api

class hr_contribution_register(models.Model):
    _inherit = 'hr.contribution.register'
    _name='hr.contribution.register'



    def open_wizard_function(self):
        # if context is None: context = {}
        # active_rec = self.browse(ids[0])
        # Pass in any values here that you want to be pre-defined on the wizard popup
        values = {}
        wizard_id = self.env['optipay.declaration.revenue.wizard'].create(values)
        return {
            'name': 'Période',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'optipay.declaration.revenue.wizard',
            'res_id': wizard_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.env.context,
        }

    def open_wizard_function_css(self, ids):
        # Pass in any values here that you want to be pre-defined on the wizard popup
        values = {}
        wizard_id = self.env['optesis.payslip.lines.securite.sociale'].create(values)
        return {
            'name': 'Période',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'optesis.payslip.lines.securite.sociale',
            'res_id': wizard_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context':{
                'default_wizard_id':self.env.context
            },
        }

    # def open_wizard_function_ipres(self, ids):
    #     values = {}
    #     wizard_id = self.env['optesis.payslip.lines.cotisation.ipres'].create(values)
    #     return {
    #         'name': 'Période',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'optesis.payslip.lines.cotisation.ipres',
    #         'res_id': wizard_id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'new',
    #         'context':{
    #             'default_wizard_id':self.env.context
    #         },
    #     }

    def open_wizard_transfer_order(self):
        values = {}
        wizard_id = self.env['optesis.transfer.order'].create(values)
        return {
            'name': 'Période',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'optesis.transfer.order',
            'res_id': wizard_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context':{
                'default_wizard_id':self.env.context
            },
        }
