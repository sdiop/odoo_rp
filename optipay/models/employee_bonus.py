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
from datetime import datetime
from dateutil import relativedelta
from odoo import models, fields, api, _
from odoo.tools import  DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class EmployeeBonus(models.Model):
    _name = 'hr.employee.bonus'
    _description = 'Employee Bonus'

    salary_rule = fields.Many2one('hr.salary.rule', string="Salary Rule" ,required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    amount = fields.Float(string='Amount', required=True)
    date_from = fields.Date(string='Date From',
                            default=time.strftime('%Y-%m-%d'), required=True)
    date_to = fields.Date(string='Date To',
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10], required=True)
    state = fields.Selection([('active', 'Active'),
                              ('expired', 'Expired'), ],
                             default='active', string="State", compute='get_status')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    contract_id = fields.Many2one('hr.contract', string='Contract')

    def get_status(self):
        current_datetime = datetime.now()
        for i in self:
            x = datetime.strptime(str(i.date_from), '%Y-%m-%d')
            y = datetime.strptime(str(i.date_to), '%Y-%m-%d')
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
    ir_changed = fields.Boolean(default=False)


    def process_scheduler_check_employee_child_grown(self):
        for empl_obj in self.env['hr.employee'].search([]):
            empl_obj.get_ir_trimf()

    @api.multi
    @api.depends('relation_ids')
    def get_ir_trimf(self):
        server_dt = DEFAULT_SERVER_DATE_FORMAT
        for value in self:
            old_ir = value.ir
            value.ir = 1
            value.trimf = 1
            for line in value.relation_ids:
                if line.type == 'enfant':
                    now = datetime.now()
                    dur = now - line.birth
                    if dur.days < 7670 :# check if child is grown
                        value.ir += 0.5
                if line.type == 'conjoint' and line.salari == 0:
                    value.ir += 1
                    value.trimf += 1
                if line.type == 'conjoint' and line.salari == 1:
                    value.ir += 0.5
            if value.ir >= 5:
                value.ir = 5
            if value.trimf >= 5:
                value.trimf = 5
            if value != value.ir:
                value.ir_changed = True


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

    @api.onchange('bonus.amount')
    def get_bonus_amount(self):
        current_datetime = datetime.now()
        for contract in self:
            bonus_amount = 0
            for bonus in contract.bonus:
                x = datetime.strptime(str(bonus.date_from), '%Y-%m-%d')
                y = datetime.strptime(str(bonus.date_to), '%Y-%m-%d')
                if x <= current_datetime and y >= current_datetime:
                    bonus_amount = bonus_amount + bonus.amount
                contract.total_bonus = bonus_amount

    total_bonus = fields.Float(string="Total Bonus", compute=get_bonus_amount)
    bonus = fields.One2many('hr.employee.bonus', 'contract_id', string="Bonus",
                            domain=[('state', '=', 'active')])
    nb_days = fields.Integer(string="Anciennete")
    cumul_jour = fields.Float("Cumul jours anterieur")
    cumul_conges = fields.Float("Cumul conges anterieur")
    nbj_alloue = fields.Float("Nombre de jour alloue", default="2.5")
    nbj_travail = fields.Float("Nombre de jour de travail", default="30")
    nbj_aquis = fields.Float("Nombre de jour aquis", store=True)
    convention_id = fields.Many2one('line.optesis.convention','Categorie')
    nbj_pris = fields.Float("Nombre de jour pris", default="0")
    cumul_mesuel = fields.Float("Cumul mensuel conges")
    last_date = fields.Date("derniere date")
    alloc_conges = fields.Float("Allocation conges", compute="_get_alloc")


    @api.cr_uid_ids_context
    def reinit(self, contract_ids):
        for record in self.browse(contract_ids):
            record.cumul_mesuel = record.cumul_mesuel - record.alloc_conges
            record.alloc_conges = 0
            record.nbj_aquis = record.nbj_aquis - record.nbj_pris
            #record.employee_id.update({'remaining_leaves':record.nbj_aquis})
            record.nbj_pris = 0

    @api.onchange("convention_id")
    def onchange_categ(self):
        if self.convention_id:
            self.wage = self.convention_id.wage


    @api.multi
    def _get_droit(self,date):
        for record in self:
            if record.cumul_conges == 0:
                if date is None:
                    record.last_date = date = datetime.now().strftime('%Y-%m-%d')
                else:
                    record.last_date = date
                code = "BRUT"
                self.env.cr.execute("SELECT (case when hp.credit_note = False then (pl.total) else (-pl.total) end) \
                            FROM hr_payslip as hp, hr_payslip_line as pl \
                            WHERE pl.employee_id = %s \
                            AND pl.slip_id = hp.id \
                            AND hp.date_from <= %s AND hp.date_to >= %s AND pl.code = %s",
                            (record.employee_id.id, date, date, code))
                result = self.env.cr.fetchone()[0] or 0.0
                cumul_mesuel = (result * record.nbj_alloue) / record.nbj_travail
                record.cumul_mesuel += cumul_mesuel
                record.nbj_aquis += record.nbj_alloue
                record.employee_id.update({'remaining_leaves':record.nbj_aquis})
            else:
                if date is None:
                    record.last_date = date = datetime.now().strftime('%Y-%m-%d')
                else:
                    record.last_date = date
                code = "BRUT"
                self.env.cr.execute("SELECT (case when hp.credit_note = False then (pl.total) else (-pl.total) end) \
                            FROM hr_payslip as hp, hr_payslip_line as pl \
                            WHERE hp.employee_id = %s \
                            AND pl.slip_id = hp.id \
                            AND hp.date_from <= %s AND hp.date_to >= %s AND pl.code = %s",
                            (record.employee_id.id, date, date, code))
                result = self.env.cr.fetchone()[0] or 0.0
                cumul_mesuel = (result * record.nbj_alloue) / record.nbj_travail
                record.cumul_mesuel +=  record.cumul_conges + cumul_mesuel
                record.nbj_aquis += record.nbj_alloue
                record.employee_id.update({'remaining_leaves':record.nbj_aquis})
                record.cumul_conges = 0

    @api.multi
    @api.depends("cumul_mesuel","nbj_pris","nbj_aquis")
    def _get_alloc(self):
        for record in self:
            # if record.nbj_pris > (record.nbj_aquis + 2.5):
            #     raise Warning('le nombre de jour pris ne doit pas etre supperieur au nombre de jour aquis')
            if record.nbj_pris == 0 and record.cumul_mesuel==0:
                return True
            if record.nbj_pris == 0 and record.cumul_mesuel!=0:
                return True
            if record.nbj_pris != 0 and record.cumul_mesuel==0:
                return True
            if record.nbj_pris != 0 and record.cumul_mesuel!=0:
                if record.nbj_aquis == 0:
                    return True
                else:
                    record.alloc_conges = (record.cumul_mesuel * record.nbj_pris)/record.nbj_aquis
            if record.nbj_aquis >= record.nbj_travail:
                record.alloc_conges = (record.cumul_mesuel * record.nbj_pris)/record.nbj_travail

    @api.multi
    def _get_duration(self,date):
        for record in self:
            server_dt = DEFAULT_SERVER_DATE_FORMAT
            date_from = datetime.strptime(str(date), server_dt)
            date_start = datetime.strptime(str(record.date_start), server_dt)
            dur = date_from - date_start
            record.nb_days = dur.days


class BonusRuleInput(models.Model):
    _inherit = 'hr.payslip'

    # @api.model
    # def create(self,vals):
    #     server_dt = DEFAULT_SERVER_DATE_FORMAT
    #     date = datetime.strptime(vals.get('date_from'),server_dt)
    #     for line in self.env['hr.payslip'].search([('employee_id', '=', vals.get('employee_id'))]):
    #         if datetime.strptime(str(line.date_from),server_dt).month == date.month and datetime.strptime(str(line.date_from),server_dt).year == date.year:
    #             raise ValidationError(_("Le "+line.name+" existe déjà"))
    #     result = super(BonusRuleInput, self).create(vals)
    #     return result


    @api.model
    def create(self, vals):
        res = super(BonusRuleInput, self).create(vals)
        if not res.credit_note:
            cr = self._cr
            if not (res.date_from >= res.contract_id.date_start or res.date_to <= res.contract_id.date_end):
                raise ValidationError(_("You cannot create payslip for the dates out of the contract period"))
            query = """SELECT date_from, date_to FROM "hr_payslip" WHERE employee_id = %s AND state = 'done'"""
            cr.execute(query, ([res.employee_id.id]))
            date_from_to = cr.fetchall()
            for items in date_from_to:
                if res.date_from == items[0] and res.date_to == items[1]:
                    raise ValidationError(_("You cannot create payslip for the same period"))
                else:
                    if not (items[1] <= res.date_from >= items[0] or items[0] >= res.date_to <= items[1]):
                        raise ValidationError(_("You cannot create payslip for the same period"))

        return res


    @api.multi
    def action_payslip_done(self):

        #add by cybrocys
        if not self.credit_note:
            if not (self.date_from >= self.contract_id.date_start or
                            self.date_to <= self.contract_id.date_end):
                raise ValidationError(_("You cannot create payslip for the dates out of the contract period"))

            cr = self._cr
            query = """SELECT date_from, date_to FROM "hr_payslip" WHERE employee_id = %s AND state = 'done'"""
            cr.execute(query, ([self.employee_id.id]))
            date_from_to = cr.fetchall()
            for items in date_from_to:
                if self.date_from == items[0] and self.date_to == items[1]:
                    raise ValidationError(_("You cannot create payslip for the same period"))
                else:
                    if not (items[1] <= self.date_from >= items[0]
                            or items[0] >= self.date_to <= items[1]):
                        raise ValidationError(_("You cannot create payslip for the same period"))

            #end add cybrocys

        for payslip in self:
            payslip.contract_id._get_droit(payslip.date_from)
        self.compute_sheet()
        contract_ids = self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
        for line in payslip.line_ids:
            if line.code == "ALLOC_C":
                self.env['hr.contract'].reinit(contract_ids)
                break
        return self.write({'state': 'done'})

    @api.multi
    def update_recompute_ir(self,contract_ids):
        server_dt = DEFAULT_SERVER_DATE_FORMAT
        for payslip in self:
            year = datetime.strptime(str(payslip.date_from),server_dt).year

            # compute ir recal
            for line in self.env['hr.payslip'].search([('employee_id', '=', payslip.employee_id.id)]):
                if datetime.strptime(str(line.date_from),server_dt).year == year:
                    br_val = 0.0
                    cumul_tranche_ipm = 0.0
                    deduction = 0.0
                    ir_val_recal = 0.0
                    ir_val = 0.0
                    ir_val_regul = 0.0
                    for payslip_line in self.get_payslip_lines(contract_ids, payslip.id):
                        if payslip_line.get('code') == "BASE":
                            _logger.info("la valeur de base "+str(payslip_line.get('amount')))
                        if payslip_line.get('code') == "C_IMP":
                            br_val += float(payslip_line.get('amount')) * float(payslip_line.get('rate')) / 100
                        if payslip_line.get('code') == "CTIR":
                            cumul_tranche_ipm += float(payslip_line.get('amount')) * float(payslip_line.get('rate')) / 100
                        if payslip_line.get('code') == "IR":
                            ir_val += float(payslip_line.get('amount')) * float(payslip_line.get('rate')) / 100

                    _logger.info('la valeur du brut fiscale est de '+str(br_val))

                    # if br_val != 0.0:
                    for payslip_line in self.get_payslip_lines(contract_ids, payslip.id):
                        if payslip_line.get('code') == "IR_RECAL":
                            obj_empl = self.env['hr.employee'].browse(payslip.employee_id.id)
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
                                #update ir_recal
                                obj = self.env['hr.payslip.line'].search([('code', '=', payslip_line.get('code')),('slip_id', '=' ,line.id)], limit=1)
                                if obj:
                                    obj.write({'amount': ir_val_recal})

            ir_payslip = 0.0
            net_payslip = 0.0
            for payslip_line in payslip.details_by_salary_rule_category:
                if payslip_line.code == "IR":
                    ir_payslip = payslip_line.total
                if payslip_line.code == "NET":
                    net_payslip = payslip_line.total
                if ir_payslip != 0.0 and net_payslip != 0.0:
                    break

            # update the ir_regul of current payslip by doing sum(ir) - sum(ir_regul) of previous payslip
            if payslip.employee_id.ir_changed:
                ir_annuel = 0.0
                ir_recal_annuel = 0.0
                for line in self.env['hr.payslip'].search([('employee_id', '=', payslip.employee_id.id)]):
                    # if line.id != payslip.id:
                    if datetime.strptime(str(line.date_from),server_dt).year == year:
                        for payslip_line in line.details_by_salary_rule_category:
                            if payslip_line.code == "IR":
                                ir_annuel += payslip_line.total
                            if payslip_line.code == "IR_RECAL":
                                ir_recal_annuel += payslip_line.total

                for payslip_line in payslip.details_by_salary_rule_category:
                    if payslip_line.code == "IR_REGUL":
                        payslip_line.write({'amount' : ir_annuel - ir_recal_annuel})
                        break

                for payslip_line in payslip.details_by_salary_rule_category:
                    if payslip_line.code == "IR_FIN":
                        payslip_line.write({'amount' : ir_payslip - (ir_annuel - ir_recal_annuel)})
                        break
                payslip.employee_id.ir_changed = False
            else:
                for payslip_line in payslip.details_by_salary_rule_category:
                    if payslip_line.code == "IR_FIN":
                        payslip_line.write({'amount' : ir_payslip})
                        break

            #defalquer ir_fin du net
            ir_fin = 0.0
            for payslip_line in payslip.details_by_salary_rule_category:
                if payslip_line.code == "IR_FIN":
                    ir_fin = payslip_line.total
                    break
            for payslip_line in payslip.details_by_salary_rule_category:
                if payslip_line.code == "NET":
                    payslip_line.write({'amount' : net_payslip - ir_fin})
                    break


    def get_inputs(self, contract_ids, date_from, date_to):
        res = super(BonusRuleInput, self).get_inputs(contract_ids, date_from, date_to)
        for bonus in self.contract_id.bonus:
            if not ((bonus.date_to < self.date_from or bonus.date_from > self.date_to) \
                            or (bonus.date_to <= self.date_from or bonus.date_from >= self.date_to)):
                bonus_line = {
                    'name': str(bonus.salary_rule.name),
                    'code': bonus.salary_rule.code,
                    'contract_id': self.contract_id.id,
                    'amount': bonus.amount,

                }
                res += [bonus_line]
        return res

    @api.multi
    def compute_sheet(self):
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            #delete old payslip lines
            payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
            payslip.contract_id._get_duration(payslip.date_from)
            lines = [(0, 0, line) for line in self.get_payslip_lines(contract_ids, payslip.id)]
            payslip.write({'line_ids': lines, 'number': number})

            self.update_recompute_ir(contract_ids)

        return True

    @api.model
    def get_payslip_lines(self, contract_ids, payslip_id):
        for record in self:
            def _sum_salary_rule_category(localdict, category, amount):
                if category.parent_id:
                    localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
                if category.code in localdict['categories'].dict:
                    amount += localdict['categories'].dict[category.code]
                localdict['categories'].dict[category.code] = amount
                return localdict

            class BrowsableObject(object):
                def __init__(record, employee_id, dict, env):
                    record.employee_id = employee_id
                    record.dict = dict
                    record.env = env

                def __getattr__(record, attr):
                    return attr in record.dict and record.dict.__getitem__(attr) or 0.0

            class InputLine(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def sum(record, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = fields.Date.today()
                    record.env.cr.execute("""
                            SELECT sum(amount) as sum
                            FROM hr_payslip as hp, hr_payslip_input as pi
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                        (record.employee_id, from_date, to_date, code))
                    return self.env.cr.fetchone()[0] or 0.0

            class WorkedDays(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def _sum(record, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = fields.Date.today()
                    record.env.cr.execute("""
                            SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                            FROM hr_payslip as hp, hr_payslip_worked_days as pi
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                        (record.employee_id, from_date, to_date, code))
                    return record.env.cr.fetchone()

                def sum(record, code, from_date, to_date=None):
                    res = record._sum(code, from_date, to_date)
                    return res and res[0] or 0.0

                def sum_hours(record, code, from_date, to_date=None):
                    res = record._sum(code, from_date, to_date)
                    return res and res[1] or 0.0

            class Payslips(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def sum(record, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = fields.Date.today()
                    record.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                                    FROM hr_payslip as hp, hr_payslip_line as pl
                                    WHERE hp.employee_id = %s AND hp.state = 'done'
                                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                                        (record.employee_id, from_date, to_date, code))
                    res = record.env.cr.fetchone()
                    return res and res[0] or 0.0

            # we keep a dict with the result because a value can be overwritten by another rule with the same code
            result_dict = {}
            rules_dict = {}
            worked_days_dict = {}
            inputs_dict = {}
            blacklist = []
            payslip = record.env['hr.payslip'].browse(payslip_id)
            for worked_days_line in payslip.worked_days_line_ids:
                worked_days_dict[worked_days_line.code] = worked_days_line
            for input_line in payslip.input_line_ids:
                inputs_dict[input_line.code] = input_line

            categories = BrowsableObject(payslip.employee_id.id, {}, record.env)
            inputs = InputLine(payslip.employee_id.id, inputs_dict, record.env)
            worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, record.env)
            payslips = Payslips(payslip.employee_id.id, payslip, record.env)
            rules = BrowsableObject(payslip.employee_id.id, rules_dict, record.env)

            baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days,
                             'inputs': inputs}
            # get the ids of the structures on the contracts and their parent id as well
            contracts = record.env['hr.contract'].browse(contract_ids)
            structure_ids = contracts.get_all_structures()
            # get the rules of the structure and thier children
            rule_ids = record.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
            # run the rules by sequence
            # Appending bonus rules from the contract
            for contract in contracts:
                for bonus in contract.bonus:
                    if not ((bonus.date_to < record.date_from or bonus.date_from > record.date_to)
                            or (bonus.date_to <= record.date_from or bonus.date_from >= record.date_to)):
                        bonus.salary_rule.write({
                            'amount_fix': bonus.amount, })
                        rule_ids.append((bonus.salary_rule.id, bonus.salary_rule.sequence))

            sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
            sorted_rules = record.env['hr.salary.rule'].browse(sorted_rule_ids)

            for contract in contracts:
                employee = contract.employee_id
                localdict = dict(baselocaldict, employee=employee, contract=contract)
                for rule in sorted_rules:
                    key = rule.code + '-' + str(contract.id)
                    localdict['result'] = None
                    localdict['result_qty'] = 1.0
                    localdict['result_rate'] = 100
                    # check if the rule can be applied
                    if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                        # compute the amount of the rule
                        amount, qty, rate = rule._compute_rule(localdict)
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
                # payslips.contract_id._get_duration(payslips.date_from)

            return [value for code, value in result_dict.items()]

class HrPayslipRunExtend(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')

    def pay_payslip(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')

        line_ids = []
        for slip in self.slip_ids:

            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to
            if slip.state != 'done':
                for line in slip.details_by_salary_rule_category:
                    amount = slip.credit_note and -line.total or line.total
                    if float_is_zero(amount, precision_digits=precision):
                        continue
                    debit_account_id = line.salary_rule_id.account_debit.id
                    credit_account_id = line.salary_rule_id.account_credit.id

                    if debit_account_id:
                        debit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=False),
                            'account_id': debit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                    if credit_account_id:
                        credit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=True),
                            'account_id': credit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                    acc_id = slip.journal_id.default_credit_account_id.id
                    if not acc_id:
                        raise UserError(
                            _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                slip.journal_id.name))
                    adjust_credit = (0, 0, {
                        'name': _('Adjustment Entry'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': 0.0,
                        'credit': debit_sum - credit_sum,
                    })
                    line_ids.append(adjust_credit)

                elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                    acc_id = slip.journal_id.default_debit_account_id.id
                    if not acc_id:
                        raise UserError(
                            _('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                                slip.journal_id.name))
                    adjust_debit = (0, 0, {
                        'name': _('Adjustment Entry'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': credit_sum - debit_sum,
                        'credit': 0.0,
                    })
                    line_ids.append(adjust_debit)

        name = _('Payslips of  Batch %s') % (self.name)
        move_dict = {
                'narration': name,
                'ref': self.name,
                'journal_id': self.journal_id.id,
                'date': date,
        }

        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        move.write({'batch_id': slip.payslip_run_id.id})
        for slips in self.slip_ids:
            if slip.state != 'done':
                slips.write({'move_id': move.id, 'date': date, 'state': 'done'})
        move.post()
        self.write({'state': 'done'})
