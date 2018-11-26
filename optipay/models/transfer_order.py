# -*- coding: utf-8 -*-
# by khk
import time
from datetime import datetime
from dateutil import relativedelta
from odoo import fields, models, api


class optesis_transfer_order(models.TransientModel):
    _name = 'optesis.transfer.order'
    _description = 'order de virement'

    date_from = fields.Date('Date de la paie', required=True, default=lambda *a: time.strftime('%Y-%m-01'))

    def print_report_transfer_order(self,ids):
        datas = {
             'ids': self.env.context.get('active_ids', []),
             'model': 'hr.contribution.register',
             'form': self.read(ids)[0]
        }
        # return self.env['report'].get_action(self, 'optipay.transfer_order', data=datas)
        return self.env.ref('optipay.transfert_order').report_action([], data=datas)
