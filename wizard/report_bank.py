# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017 Humanytek (<www.humanytek.com>).
#    Rubén Bravo <rubenred18@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
#import xlsxwriter
import xlwt
from os import path
_logger = logging.getLogger(__name__)


class ReportBank(models.TransientModel):
    _name = "report.bank"

    @api.multi
    def print_report(self):

        AccountJournal = self.env['account.journal']
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        report_path = path.join(path.dirname(__file__), 'report/')
        xls_path = report_path + "reporte.xls"
        book = xlwt.Workbook(encoding="utf-8")
        style1 = xlwt.XFStyle()
        font1 = xlwt.Font()
        alignment1 = xlwt.Alignment()
        font1.bold = True
        alignment1.horz = xlwt.Alignment.HORZ_CENTER
        style1.alignment = alignment1
        style1.font = font1
        sheet1 = book.add_sheet("Hoja 1")
        sheet1.write_merge(0, 0, 1, 8, "GRUPO REQUIEZ SA DE CV", style1)
        sheet1.write_merge(1, 1, 1, 8, "FLUJO DE EFECTIVO", style1)
        sheet1.write(2, 1, "DESDE", style1)
        sheet1.write_merge(2, 2, 2, 8, self.date_start)
        sheet1.write(3, 1, "HASTA", style1)
        sheet1.write_merge(3, 3, 2, 8, self.date_end)
        sheet1.write(5, 1, "CUENTAS", style1)
        sheet1.write(5, 2, "INICIAL", style1)
        sheet1.write(5, 3, "TRASPASOS", style1)
        sheet1.write(5, 4, "INGRESOS", style1)
        sheet1.write(5, 5, "ENTRADAS", style1)
        sheet1.write(5, 6, "PAGOS", style1)
        sheet1.write(5, 7, "SALIDAS", style1)
        sheet1.write(5, 8, "SALDOS", style1)
        line_sheet = 6

        journals = AccountJournal.search([('type', '=', 'bank'),
                                          ], order='currency_id')
        curr_id = total_in = total_out = total_i = total_f = 0
        band = curr_name = False
        for journal in journals:
            if journal.currency_id.id != curr_id:
                curr_id = journal.currency_id.id
                if band:
                    line_sheet += 1
                    name_c = 'TOTAL BANCOS MONEDA ' + curr_name
                    sheet1.write(line_sheet, 1, name_c, style1)
                    sheet1.write(line_sheet, 5, total_in, style1)
                    sheet1.write(line_sheet, 7, total_out, style1)
                    sheet1.write(line_sheet, 2, total_i, style1)
                    sheet1.write(line_sheet, 8, total_f, style1)
                    line_sheet += 2
                if journal.currency_id:
                    curr_name = journal.currency_id.name
                else:
                    curr_name = 'MX'
                band = True
                total_in = total_out = 0
            sheet1.write(line_sheet, 1, journal.name, style1)
            amount_i = amount_f = 0
            lines_ini = AccountMoveLine.search([('journal_id', '=', journal.id),
                    ('move_id.state', '=', 'posted'),
                    ('date', '<', self.date_start),
                    ('account_id', '=', journal.default_debit_account_id.id)])
            for line_ini in lines_ini:
                amount_i += line_ini.debit - line_ini.credit
            amount_f = amount_i
            total_i += amount_i
            sheet1.write(line_sheet, 2, amount_i, style1)
            sheet1.write(line_sheet, 8, amount_f, style1)
            line_sheet += 1

            lines = AccountMoveLine.search([('journal_id', '=', journal.id),
                    ('move_id.state', '=', 'posted'),
                    ('date', '>=', self.date_start),
                    ('date', '<=', self.date_end),
                    ('account_id', '=', journal.default_debit_account_id.id)])
            for line in lines:
                #sheet1.write(line_sheet, 1, line.account_id.code)
                if line.credit > 0:
                    amount_f -= line.credit
                    sheet1.write(line_sheet, 7, line.credit)
                    total_out += line.credit
                    if line.payment_id:
                        sheet1.write(line_sheet, 6, line.credit)
                    else:
                        sheet1.write(line_sheet, 3, line.credit)
                else:
                    amount_f += line.debit
                    sheet1.write(line_sheet, 5, line.debit)
                    total_in += line.debit
                    if line.payment_id:
                        sheet1.write(line_sheet, 4, line.debit)
                    else:
                        sheet1.write(line_sheet, 3, line.debit)
                sheet1.write(line_sheet, 2, amount_i)
                sheet1.write(line_sheet, 8, amount_f)
                amount_i = amount_f

                line_sheet += 1
            total_f += amount_f
        line_sheet += 1
        if journals:
            name_c = 'TOTAL BANCOS MONEDA ' + curr_name
            sheet1.write(line_sheet, 1, name_c, style1)
            sheet1.write(line_sheet, 5, total_in, style1)
            sheet1.write(line_sheet, 7, total_out, style1)
            sheet1.write(line_sheet, 2, total_i, style1)
            sheet1.write(line_sheet, 8, total_f, style1)
        line_sheet += 1

        book.save(xls_path)

        with open(xls_path, 'rb') as xlsfile:
            b64encoded_xlsfile = base64.b64encode(xlsfile.read())

        result_write = self.write({'state': 'get',
                        'excel': b64encoded_xlsfile,
                        'name': 'Bancos.xls'})

        if result_write:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'report.bank',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'target': 'new',
                }

    name = fields.Char('File Name', readonly=True)
    excel = fields.Binary('Excel file', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                            default='choose')
    date_start = fields.Datetime('Start Date',
                                    required=True)
    date_end = fields.Datetime('End Date',
                                    required=True)
    #account_ids = fields.One2many('account.journal',
                            #'mrp_ii_id',
                            #'Bank')

