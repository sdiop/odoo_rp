# -*- coding: utf-8 -*-
# by khk
import time
from datetime import datetime
from dateutil import relativedelta
from odoo import fields, models, api


class declaration_revenue_wizard(models.TransientModel):

    _name = 'optipay.declaration.revenue.wizard'
    _description = 'declarations des retenues a la source sur les salaires'

    date_from = fields.Date('Date de debut', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date de fin', required=True, default=lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def print_report(self, ids):
        datas = {
             'ids': self.env.context.get('active_ids', []),
             'model': 'hr.contribution.register',
             'form': self.read( ids)[0]
        }
        # return self.env['report'].get_action(self, 'optipay.optesis_bulletin', data=datas)
        return self.env.ref('optipay.optesis_bulletin').report_action([], data=datas)
