#-*- coding:utf-8 -*-
# by khk
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class CotisationIpresReport(models.AbstractModel):
    _name = 'report.optipay.report_ipres_view'

    def _get_payslip_lines(self, register_ids, date_from, date_to):
        _logger.error("_get_payslip_lines NEW BEGIN")
        dict = {}
        res = []
        self.env.cr.execute("SELECT DISTINCT hr_payslip_line.id,hr_payslip_line.code,hr_payslip_line.amount_select,"\
                         "hr_payslip_line.sequence,"\
                         "hr_payslip_line.total,"\
                         "hr_payslip_line.employee_id,"\
                         "hr_payslip_line.amount,"\
                         "hr_salary_rule_category.id,"\
                         "hr_salary_rule_category.code,"\
                         "hr_salary_rule_category.name,"\
                         "hr_employee.id,"\
                         "hr_payslip_line.create_date,"\
                         "hr_payslip.id,"\
                         "hr_payslip.date_to,"\
                         "hr_payslip.date_from,"\
                         "hr_payslip.state,"\
                         "hr_payslip_line.register_id,"\
                         "hr_payslip_line.name,"\
                         "hr_payslip_line.amount_percentage_base,"\
                         "hr_employee.name from "\
                         "hr_salary_rule_category as hr_salary_rule_category INNER JOIN hr_payslip_line as hr_payslip_line ON hr_salary_rule_category.id = hr_payslip_line.category_id "\
                         "INNER JOIN hr_employee as hr_employee ON hr_payslip_line.employee_id = hr_employee.id "\
                         "INNER JOIN hr_payslip as hr_payslip ON hr_payslip_line.slip_id = hr_payslip.id "\
                         "AND hr_employee.id = hr_payslip.employee_id where "\
                         "hr_payslip.date_from >=  %s AND "\
                         "hr_payslip.date_to <= %s AND "\
                         "hr_payslip_line.code IN ('C_IMP','BASE','IPRES RC','IPRES RG','IPRES RC Pat','IPRES RG Pat') "\
                         "ORDER BY hr_employee.name ASC, hr_payslip_line.code ASC",
                         (date_from, date_to))
        line_ids = [x[0] for x in self.env.cr.fetchall()]
        for line in self.env['hr.payslip.line'].browse(line_ids):
            if line.employee_id.id in dict:
                if line.code == 'C_IMP':
                    self.line_brut += line.total
                    dict[line.employee_id.id]['Brut'] = self.line_brut
                elif line.code == 'IPRES RC':
                    self.line_ipres_rc += line.total
                    dict[line.employee_id.id]['Ipres_rc'] = self.line_ipres_rc
                    if self.line_base_rc == 0.0:
                        dict[line.employee_id.id]['Base_rc'] = line.total
                elif line.code == 'IPRES RG':
                    self.line_ipres_rg += line.total
                    dict[line.employee_id.id]['Ipres_rg'] = self.line_ipres_rg
                    if self.line_base_rg == 0.0:
                        dict[line.employee_id.id]['Base_rg'] = line.total
                elif line.code == 'IPRES RC Pat':
                    self.line_ipres_rc_pat += line.total
                    dict[line.employee_id.id]['Ipres_rc_pat'] = self.line_ipres_rc_pat
                elif line.code == 'IPRES RG Pat':
                    self.line_ipres_rg_pat += line.total
                    dict[line.employee_id.id]['Ipres_rg_pat'] = self.line_ipres_rg_pat
            else:
                dict[line.employee_id.id] = {}
                employe_data = self.env['hr.employee'].browse(line.employee_id.id)

                dict[line.employee_id.id]['Brut'] = 0
                dict[line.employee_id.id]['Ipres_rc'] = 0
                dict[line.employee_id.id]['Base_rc'] = 0
                dict[line.employee_id.id]['Ipres_rg'] = 0
                dict[line.employee_id.id]['Base_rg'] = 0
                dict[line.employee_id.id]['Ipres_rc_pat'] = 0
                dict[line.employee_id.id]['Ipres_rg_pat'] = 0

                self.line_base_rg = 0.0
                self.line_base_rc = 0.0
                self.line_brut = 0.0
                self.line_ipres_rc = 0.0
                self.line_ipres_rg = 0.0
                self.line_ipres_rc_pat = 0.0
                self.line_ipres_rg_pat = 0.0

                dict[line.employee_id.id]['Name'] = employe_data.name
                dict[line.employee_id.id]['Matricule'] = employe_data.num_chezemployeur

        index = 0
        for key,values in dict.items():

            index +=1
            res.append({
                'index': index,
                'matricule': dict[key]['Matricule'],
                'name':dict[key]['Name'],
                'Brut': dict[key]['Brut'],
                'Base_rg': dict[key]['Base_rg'],
                'Base_rc': dict[key]['Base_rc'],
                'Ipres_rc': dict[key]['Ipres_rc'],
                'Ipres_rg': dict[key]['Ipres_rg'],
                'Ipres_rc_pat': dict[key]['Ipres_rc_pat'],
                'Ipres_rg_pat': dict[key]['Ipres_rg_pat'],
                'total_rg': dict[key]['Ipres_rg'] + dict[key]['Ipres_rg_pat'],
                'total_rc': dict[key]['Ipres_rc'] + dict[key]['Ipres_rc_pat'],
                'Cotisation_totale': (dict[key]['Ipres_rg'] + dict[key]['Ipres_rg_pat']) + (dict[key]['Ipres_rc'] + dict[key]['Ipres_rc_pat']),
            })
        _logger.error("_get_payslip_lines NEW END")
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        register_ids = self.env.context.get('active_ids', [])
        contrib_registers = self.env['hr.contribution.register'].browse(register_ids)
        date_from = data['form'].get('date_from', fields.Date.today())
        date_to = data['form'].get('date_to', str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10])
        lines_data = self._get_payslip_lines(register_ids, date_from, date_to)

        total_cotisation = 0.0
        total_rc = 0.0
        total_rg = 0.0
        total_base_rc = 0.0
        total_base_rg = 0.0
        total_brut = 0.0
        total_ipres_rc = 0.0
        total_ipres_rg = 0.0
        total_ipres_rc_pat = 0.0
        total_ipres_rg_pat = 0.0


        lines_total = []
        for line in lines_data:
            total_cotisation += line.get('Cotisation_totale')
            total_rc += line.get('total_rc')
            total_rg += line.get('total_rg')
            total_base_rc += line.get('Base_rc')
            total_base_rg += line.get('Base_rg')
            total_brut += line.get('Brut')
            total_ipres_rc += line.get('Ipres_rc')
            total_ipres_rg += line.get('Ipres_rg')
            total_ipres_rc_pat += line.get('Ipres_rc_pat')
            total_ipres_rg_pat += line.get('Ipres_rg_pat')

        lines_total.append({
            'total_cotisation' : total_cotisation,
            'total_rc' : total_rc,
            'total_rg' : total_rg,
            'total_base_rc' : total_base_rc,
            'total_base_rg' : total_base_rg,
            'total_brut' : total_brut,
            'total_ipres_rc' : total_ipres_rc,
            'total_ipres_rg' : total_ipres_rg,
            'total_ipres_rc_pat' : total_ipres_rc_pat,
            'total_ipres_rg_pat' : total_ipres_rg_pat,
            'total_brut' : total_brut,
        })

        return {
            'doc_ids': register_ids,
            'doc_model': 'hr.contribution.register',
            'docs': contrib_registers,
            'data': data,
            'lines_data': lines_data,
            'lines_total': lines_total
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
