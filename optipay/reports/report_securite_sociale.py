#-*- coding:utf-8 -*-
# by khk

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class SecuriteSociale(models.AbstractModel):
    _name = 'report.optipay.report_css_view'

    def _get_payslip_lines(self, register_ids, date_from, date_to):
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
                         "hr_payslip_line.code IN ('C_IMP','BASE','PRESTFAM','ACW')  "\
                         "ORDER BY hr_employee.name ASC, hr_payslip_line.code ASC",
                         (date_from,date_to))
        line_ids = [x[0] for x in self.env.cr.fetchall()]
        for line in self.env['hr.payslip.line'].browse(line_ids):
            if line.employee_id.id in dict:
                if line.code == 'C_IMP':
                    self.line_brut += line.total
                    dict[line.employee_id.id]['Brut'] = self.line_brut
                elif line.code == 'PRESTFAM':
                    self.line_prestfam += line.total
                    dict[line.employee_id.id]['Prestfam'] = self.line_prestfam
                elif line.code == 'ACW':
                    self.line_acw += line.total
                    dict[line.employee_id.id]['Acw'] = self.line_acw
                elif line.code == 'BASE':
                    self.line_base += line.total
                    dict[line.employee_id.id]['Base'] = self.line_base
            else:
                dict[line.employee_id.id] = {}
                employe_data = self.env['hr.employee'].browse(line.employee_id.id)

                dict[line.employee_id.id]['Brut'] = 0
                dict[line.employee_id.id]['Prestfam'] = 0
                dict[line.employee_id.id]['Acw'] = 0
                dict[line.employee_id.id]['Base'] = 0

                self.line_brut = 0.0
                self.line_base = 0.0
                self.line_prestfam = 0.0
                self.line_acw = 0.0

                self.line_acw += line.total
                dict[line.employee_id.id]['Acw'] = self.line_acw
                dict[line.employee_id.id]['Name'] = employe_data.name
                dict[line.employee_id.id]['Matricule'] = employe_data.num_chezemployeur

        index = 0
        for key,values in dict.items():
            index +=1
            res.append({
                'index': index,
                'matricule': dict[key]['Matricule'],
                'name': dict[key]['Name'],
                'Brut': dict[key]['Brut'],
                'Base': dict[key]['Base'],
                'Prestfam': dict[key]['Prestfam'],
                'Acw': dict[key]['Acw'],
                'Cotisation': dict[key]['Prestfam'] + dict[key]['Acw'],
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

        total_brut = 0.0
        total_base = 0.0
        total_prestfam = 0.0
        total_acw = 0.0
        total_cotisation = 0.0

        lines_total = []
        for line in lines_data:
            total_brut += line.get('Brut')
            total_base += line.get('Base')
            total_prestfam += line.get('Prestfam')
            total_acw += line.get('Acw')
            total_cotisation += line.get('Cotisation')

        lines_total.append({
            'total_brut' : total_brut,
            'total_base' : total_base,
            'total_prestfam' : total_prestfam,
            'total_acw' : total_acw,
            'total_cotisation' : total_cotisation,
        })

        return {
            'doc_ids': register_ids,
            'doc_model': 'hr.contribution.register',
            'docs': contrib_registers,
            'data': data,
            'lines_data': lines_data,
            'lines_total': lines_total
        }
