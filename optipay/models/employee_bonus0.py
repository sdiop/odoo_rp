# -*- coding: utf-8 -*-
###################################################################################
#    A part of OpenHRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Treesa Maria Jude (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

import time
from datetime import datetime, timedelta
from dateutil import relativedelta
from openerp import models, fields, api, _
from openerp.tools import  DEFAULT_SERVER_DATE_FORMAT

import logging
_logger = logging.getLogger(__name__)


class EmployeeBonus(models.Model):
    _name = 'hr.employee.bonus'
    _description = 'Employee Bonus'

    salary_rule = fields.Many2one('hr.salary.rule', string="Salary Rule")
    employee_id = fields.Many2one('hr.employee', string='Employee')
    amount = fields.Float(string='Amount', required=True)
    date_from = fields.Date(string='Date From',
                            default=time.strftime('%Y-%m-%d'))
    date_to = fields.Date(string='Date To',
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    state = fields.Selection([('active', 'Active'),
                              ('expired', 'Expired'), ],
                             default='active', string="State", compute='get_status')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    contract_id = fields.Many2one('hr.contract', string='Contract')

    def get_status(self):
        current_datetime = datetime.now()
        for i in self:
            x = datetime.strptime(i.date_from, '%Y-%m-%d')
            y = datetime.strptime(i.date_to, '%Y-%m-%d')
            if x <= current_datetime and y >= current_datetime:
                i.state = 'active'
            else:
                i.state = 'expired'

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    matricule_cnss = fields.Integer('Matricule CNSS', size=10)
    ipres = fields.Integer('Numero IPRES', size=10)
    mutuelle = fields.Integer('Numero mutuelle', size=10)
    compte = fields.Integer('Compte contribuable', size=10)
    num_chezemployeur = fields.Integer('Numero chez l\'employeur')
    relation_ids = fields.One2many('optesis.relation','employee_id','Relation')
    ir = fields.Float('Nombre de parts IR', compute="get_ir_trimf", store=True, default=1)
    trimf = fields.Float('Nombre de parts TRIMF', compute="get_ir_trimf", store=True, default=1)


    @api.multi
    @api.depends('relation_ids')
    def get_ir_trimf(self):
        self.ir = 1
        self.trimf = 1
        for line in self.relation_ids:
            if line.type == 'enfant':
                self.ir += 0.5
            if line.type == 'conjoint' and line.salari == 0:
                self.ir += 1
                self.trimf += 1
            if line.type == 'conjoint' and line.salari == 1:
                self.ir += 0.5
        if self.ir >= 5:
            self.ir = 5
        if self.trimf >= 5:
            self.trimf = 5


class OptesisRelation(models.Model):
    _name = 'optesis.relation'
    _description = "les relation familiale"

    type = fields.Selection([('conjoint','Conjoint'),('enfant','Enfant'),('pere','Pere'),('mere','Mere'),('autre','Autre parent')],'Type de relation')
    nom = fields.Char('Nom')
    prenom = fields.Char('Prenom')
    birth = fields.Datetime('Date de naissance')
    date_mariage = fields.Datetime('Date de mariage')
    salari = fields.Boolean('Salarie', default=0)
    employee_id = fields.Many2one('hr.employee')



class HrContractBonus(models.Model):
    _inherit = 'hr.contract'

    @api.multi
    @api.depends('bonus.amount')
    def get_bonus_amount(self):
        current_datetime = datetime.now()
        for contract in self:
            bonus_amount = 0
            for bonus in contract.bonus:
                x = datetime.strptime(bonus.date_from, '%Y-%m-%d')
                y = datetime.strptime(bonus.date_to, '%Y-%m-%d')
                if x <= current_datetime and y >= current_datetime:
                    bonus_amount = bonus_amount + bonus.amount
                contract.total_bonus = bonus_amount

    total_bonus = fields.Float(string="Total Bonus", compute=get_bonus_amount)
    bonus = fields.One2many('hr.employee.bonus', 'contract_id', string="Bonus",
                            domain=[('state', '=', 'active')])
    nb_days = fields.Integer(string="Anciennete")

    @api.multi
    def _get_duration(self,date):
        for record in self:
            server_dt = DEFAULT_SERVER_DATE_FORMAT
            date_from = datetime.strptime(date, server_dt)
            date_start = datetime.strptime(record.date_start, server_dt)
            dur = date_from - date_start
            record.nb_days = dur.days



class BonusRuleInput(models.Model):
    _inherit = 'hr.payslip'

    month = fields.Integer()


    def update_recompute_ir(self, cr, uid, ids, context=None):
        server_dt = DEFAULT_SERVER_DATE_FORMAT
        for payslip in self.browse(cr, uid, ids, context=context):
            year = datetime.strptime(payslip.date_from,server_dt).year

            # compute ir recal
            for id_line in self.pool.get('hr.payslip').search(cr, uid, [('employee_id', '=', payslip.employee_id.id)], context=context):
                line = self.pool.get('hr.payslip').browse(cr, uid, id_line, context=context)
                if datetime.strptime(line.date_from,server_dt).year == year:
                    br_val = 0.0
                    cumul_tranche_ipm = 0.0
                    deduction = 0.0
                    ir_val_recal = 0.0
                    ir_val = 0.0
                    ir_val_regul = 0.0
                    for payslip_line in line.details_by_salary_rule_category:
                        if payslip_line.code == "C_IMP":
                            br_val += payslip_line.total
                        if payslip_line.code == "CTIR":
                            cumul_tranche_ipm += payslip_line.total
                        if payslip_line.code == "IR":
                            ir_val += payslip_line.total

                    if br_val != 0.0:
                        for payslip_line in line.details_by_salary_rule_category:
                            if payslip_line.code == "IR_RECAL":
                                obj_empl = self.pool.get('hr.employee').browse(cr, uid, payslip.employee_id.id, context=context)
                                if obj_empl:
                                    if obj_empl.ir == 1:
                                        deduction = 0.0

                                    if obj_empl.ir == 1.5:
                                        if cumul_tranche_ipm * 0.1 < 8333:
                                            deduction = 8333
                                        elif cumul_tranche_ipm * 0.1 > 25000:
                                            deduction = 25000
                                        else:
                                            deduction = cumul_tranche_ipm * 0.1

                                    if obj_empl.ir == 2:
                                        if cumul_tranche_ipm * 0.15 < 16666.66666666667:
                                            deduction = 16666.66666666667
                                        elif cumul_tranche_ipm * 0.15 > 54166.66666666667:
                                            deduction = 54166.66666666667
                                        else:
                                            deduction = cumul_tranche_ipm * 0.15

                                    if obj_empl.ir == 2.5:
                                        if cumul_tranche_ipm * 0.2 < 25000:
                                            deduction = 25000
                                        elif cumul_tranche_ipm * 0.2 > 91666.66666666667:
                                            deduction = 91666.66666666667
                                        else:
                                            deduction = cumul_tranche_ipm * 0.2

                                    if obj_empl.ir == 3:
                                        if cumul_tranche_ipm * 0.25 < 33333.33333333333:
                                            deduction = 33333.33333333333
                                        elif cumul_tranche_ipm * 0.25 > 137500:
                                            deduction = 137500
                                        else:
                                             deduction = cumul_tranche_ipm * 0.25

                                    if obj_empl.ir == 3.5:
                                        if cumul_tranche_ipm * 0.3 < 41666.66666666667:
                                            deduction = 41666.66666666667
                                        elif cumul_tranche_ipm * 0.3 > 169166.6666666667:
                                            deduction = 169166.6666666667
                                        else:
                                            deduction = cumul_tranche_ipm * 0.3

                                    if cumul_tranche_ipm - deduction > 0:
                                        ir_val_recal = cumul_tranche_ipm - deduction

                                    self.pool.get('hr.payslip.line').write(cr, uid, payslip_line.id ,{'amount': ir_val_recal},context=context)

            # get sum ir and ir_recal
            ir_recal_total = 0.0
            ir_total = 0.0
            for id_line in self.pool.get('hr.payslip').search(cr, uid, [('employee_id', '=', payslip.employee_id.id)], context=context):
                line = self.pool.get('hr.payslip').browse(cr, uid, id_line, context=context)
                if datetime.strptime(line.date_from,server_dt).year == year:
                    for payslip_line in line.details_by_salary_rule_category:
                        if payslip_line.code == "IR":
                            ir_total += payslip_line.total
                        if payslip_line.code == "IR_RECAL":
                            ir_recal_total += payslip_line.total

            # update ir regul
            for id_line in self.pool.get('hr.payslip').search(cr, uid, [('employee_id', '=', payslip.employee_id.id)], context=context):
                line = self.pool.get('hr.payslip').browse(cr, uid, id_line, context=context)
                if datetime.strptime(line.date_from,server_dt).year == year:
                    for payslip_line in line.details_by_salary_rule_category:
                        if payslip_line.code == "IR_REGUL":
                            if ir_total - ir_recal_total > 0:
                                self.pool.get('hr.payslip.line').write(cr, uid, payslip_line.id ,{'amount':ir_total - ir_recal_total},context=context)
                            else:
                                self.pool.get('hr.payslip.line').write(cr, uid, payslip_line.id ,{'amount': 0.0},context=context)

            # update ir final
            for id_line in self.pool.get('hr.payslip').search(cr, uid, [('employee_id', '=', payslip.employee_id.id)], context=context):
                line = self.pool.get('hr.payslip').browse(cr, uid, id_line, context=context)
                if datetime.strptime(line.date_from,server_dt).year == year:
                    ir = 0.0
                    ir_reg = 0.0
                    for payslip_line in line.details_by_salary_rule_category:
                        if payslip_line.code == "IR":
                            ir = payslip_line.total
                        if payslip_line.code == "IR_REGUL":
                            ir_reg = payslip_line.total

                    for payslip_line in line.details_by_salary_rule_category:
                        if payslip_line.code == "IR_FIN":
                            self.pool.get('hr.payslip.line').write(cr, uid, payslip_line.id ,{'amount': ir - ir_reg},context=context)
                            break



    def get_inputs(self, cr, uid, contract_ids, date_from, date_to, context=None):
        res = super(BonusRuleInput, self).get_inputs(cr, uid, contract_ids, date_from, date_to, context=context)
        for record in self.browse(cr, uid, context=context):
            for bonus in record.contract_id.bonus:
                if not ((bonus.date_to < record.date_from or bonus.date_from > record.date_to) \
                                or (bonus.date_to <= record.date_from or bonus.date_from >= record.date_to)):
                    bonus_line = {
                        'name': str(bonus.salary_rule.name),
                        'code': bonus.salary_rule.code,
                        'contract_id': record.contract_id.id,
                        'amount': bonus.amount,

                    }
                    res += [bonus_line]
        return res

    def compute_sheet(self, cr, uid, ids, context=None):
        slip_line_pool = self.pool.get('hr.payslip.line')
        sequence_obj = self.pool.get('ir.sequence')

        for payslip in self.browse(cr, uid, ids, context=context):
            number = payslip.number or sequence_obj.get(cr, uid, 'salary.slip')
            #delete old payslip lines
            old_slipline_ids = slip_line_pool.search(cr, uid, [('slip_id', '=', payslip.id)], context=context)
#            old_slipline_ids
            if old_slipline_ids:
                slip_line_pool.unlink(cr, uid, old_slipline_ids, context=context)
            if payslip.contract_id:
                #set the list of contract for which the rules have to be applied
                contract_ids = [payslip.contract_id.id]
            else:
                #if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                contract_ids = self.get_contract(cr, uid, payslip.employee_id, payslip.date_from, payslip.date_to, context=context)
            lines = [(0,0,line) for line in self.pool.get('hr.payslip').get_payslip_lines(cr, uid, contract_ids, payslip.id, context=context)]
            self.write(cr, uid, [payslip.id], {'line_ids': lines, 'number': number,}, context=context)

            # to compute the number of months that the emplyé worked in the year
            # server_dt = DEFAULT_SERVER_DATE_FORMAT
            # date_payslip = datetime.strptime(payslip.date_from,server_dt)
            # obj_contract = self.pool.get('hr.contract').browse(cr, uid,payslip.id,context=context)
            # if obj_contract:
            #     for obj in obj_contract:
            #         date_contract = datetime.strptime(obj.date_start,server_dt)
            #     if date_payslip.year > date_contract.year:
            #         month = date_payslip.month
            #         self.write(cr, uid, [payslip.id], {'month': month,}, context=context)
            #     else:
            #         month_debut = date_contract.month
            #         month_payslip = date_payslip.month
            #         month = month_payslip - month_debut
            #         month += 1
            #         self.write(cr, uid, [payslip.id], {'month': month,}, context=context)

            self.update_recompute_ir(cr, uid, ids, context=context)
        return True

    def get_payslip_lines(self, cr, uid, contract_ids, payslip_id, context):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            if category.code in localdict['categories'].dict:
                amount += localdict['categories'].dict[category.code]
            localdict['categories'].dict[category.code] = amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, pool, cr, uid, employee_id, dict):
                self.pool = pool
                self.cr = cr
                self.uid = uid
                self.employee_id = employee_id
                self.dict = dict

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.cr.execute("""
                        SELECT sum(amount) as sum
                        FROM hr_payslip as hp, hr_payslip_input as pi
                        WHERE hp.employee_id = %s AND hp.state = 'done'
                        AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                return self.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.cr.execute("""
                        SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                        FROM hr_payslip as hp, hr_payslip_worked_days as pi
                        WHERE hp.employee_id = %s AND hp.state = 'done'
                        AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                return self.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                                FROM hr_payslip as hp, hr_payslip_line as pl
                                WHERE hp.employee_id = %s AND hp.state = 'done'
                                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        categories_dict = {}
        blacklist = []
        payslip_obj = self.pool.get('hr.payslip')
        inputs_obj = self.pool.get('hr.payslip.worked_days')
        obj_rule = self.pool.get('hr.salary.rule')
        payslip = payslip_obj.browse(cr, uid, payslip_id, context=context)
        worked_days = {}
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days[worked_days_line.code] = worked_days_line
        inputs = {}
        for input_line in payslip.input_line_ids:
            inputs[input_line.code] = input_line

        categories = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, categories_dict)
        inputs = InputLine(self.pool, cr, uid, payslip.employee_id.id, inputs)
        worked_days = WorkedDays(self.pool, cr, uid, payslip.employee_id.id, worked_days)
        payslips = Payslips(self.pool, cr, uid, payslip.employee_id.id, payslip)
        rules = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, rules_dict)

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days,
                         'inputs': inputs}
        # get the ids of the structures on the contracts and their parent id as well
        structure_ids = self.pool.get('hr.contract').get_all_structures(cr, uid, contract_ids, context=context)
        #get the rules of the structure and thier children
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
        # run the rules by sequence
        # Appending bonus rules from the contract
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            for bonus in contract.bonus:
                if not ((bonus.date_to < payslips.date_from or bonus.date_from > payslips.date_to)
                        or (bonus.date_to <= payslips.date_from or bonus.date_from >= payslips.date_to)):
                    bonus.salary_rule.write({
                        'amount_fix': bonus.amount, })
                    rule_ids.append((bonus.salary_rule.id, bonus.salary_rule.sequence))

        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        #sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            for rule in obj_rule.browse(cr, uid, sorted_rule_ids, context=context):
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                # check if the rule can be applied
                if obj_rule.satisfy_condition(cr, uid, rule.id, localdict, context=context) and rule.id not in blacklist:
                    # compute the amount of the rule
                    amount, qty, rate = obj_rule.compute_rule(cr, uid, rule.id, localdict, context=context)
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]
            payslips.contract_id._get_duration(payslips.date_from)

        return [value for code, value in result_dict.items()]
