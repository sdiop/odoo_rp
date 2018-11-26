from odoo import models, fields, api, _
from odoo.tools import  DEFAULT_SERVER_DATE_FORMAT

class hr_holidays(models.Model):
    _inherit = "hr.leave"

    def holidays_validate(self):
        obj_emp = self.env['hr.employee']
        obj_contract = self.env['hr.contract']
        ids2 = obj_emp.search([('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        self.write({'state':'validate'})
        # data_holiday = self
        for record in self:
            id_contract = obj_contract.search([('employee_id', '=', record.employee_id.id)])
            contract = obj_contract.browse(id_contract)
            contract.write({'nbj_pris':+record.number_of_days_temp})
            if record.double_validation:
                record.write({'manager_id2': manager})
            else:
                record.write({'manager_id': manager})
            if record.holiday_type == 'employee' and record.type == 'remove':
                meeting_obj = self.env['calendar.event']
                meeting_vals = {
                    'name': record.name or _('Leave Request'),
                    'categ_ids': record.holiday_status_id.categ_id and [(6,0,[record.holiday_status_id.categ_id.id])] or [],
                    'duration': record.number_of_days_temp * 8,
                    'description': record.notes,
                    'user_id': record.user_id.id,
                    'start': record.date_from,
                    'stop': record.date_to,
                    'allday': False,
                    'state': 'open',            # to block that meeting date in the calendar
                    'class': 'confidential'
                }
                #Add the partner_id (if exist) as an attendee
                if record.user_id and record.user_id.partner_id:
                    meeting_vals['partner_ids'] = [(4,record.user_id.partner_id.id)]

                ctx_no_email = dict(context or {}, no_email=True)
                meeting_id = meeting_obj.create(meeting_vals)
                self._create_resource_leave([record])
                self.write({'meeting_id': meeting_id})
            elif record.holiday_type == 'category':
                emp_ids = obj_emp.search([('category_ids', 'child_of', [record.category_id.id])])
                leave_ids = []
                for emp in obj_emp.browse(emp_ids):
                    vals = {
                        'name': record.name,
                        'type': record.type,
                        'holiday_type': 'employee',
                        'holiday_status_id': record.holiday_status_id.id,
                        'date_from': record.date_from,
                        'date_to': record.date_to,
                        'notes': record.notes,
                        'number_of_days_temp': record.number_of_days_temp,
                        'parent_id': record.id,
                        'employee_id': emp.id
                    }
                    leave_ids.append(self.create(vals))
                for leave_id in leave_ids:
                    # TODO is it necessary to interleave the calls?
                    for sig in ('confirm', 'validate', 'second_validate'):
                        self.signal_workflow([leave_id])
        return True
