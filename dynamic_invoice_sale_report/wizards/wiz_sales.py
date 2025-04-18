from datetime import date
from io import BytesIO
import base64
from datetime import datetime
import xlsxwriter
from odoo import api, fields, models


class AccountSaleReportWizard(models.TransientModel):
    _name = "account.sales.report"

    date_from = fields.Date(string='Start Date', default=date.today().replace(day=1), required=True)
    date_to = fields.Date(string='End Date', default=date.today(), required=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id.id)

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
            },
        }

        return self.env.ref('dynamic_invoice_sale_report.action_account_sales_report').report_action(self, data=data)

    def action_print_excel(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Account Sales Report')

        sheet.set_column('A:A', 20)  
        sheet.set_column('B:B', 15)  
        sheet.set_column('C:C', 10) 
        sheet.set_column('D:J', 15)  

        bold = workbook.add_format({'bold': True})
        money = workbook.add_format({'num_format': '#,##0.00'})

        sheet.merge_range('A1:J1', 'Account Sales Report', bold)

        date_from = self.date_from.strftime('%Y-%m-%d') if self.date_from else ''
        date_to = self.date_to.strftime('%Y-%m-%d') if self.date_to else ''
        sheet.write('A2', f'From: {date_from} To: {date_to}')

        report = self.env['report.dynamic_invoice_sale_report.account_sales_data_view']
        report_data = report._get_report_values(
            None,
            {
                'ids': [self.id],
                'model': self._name,
                'form': {
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                }
            }
        )
        user_data = report_data.get('user_data', {})

        row = 4
        for user, vals in user_data.items():
            sheet.write(row, 0, f"Salesperson: {user}", bold)
            row += 1
            headers = ["Date & Time", "Order No.", "Type", "Cash", "Credit Card", "Cheque", "Bank", "Total With VAT", "Paid Amount", "Due Amount"]
            for col, header in enumerate(headers):
                sheet.write(row, col, header, bold)
            row += 1

            for inv in vals['invoices']:
                sheet.write(row, 0, str(inv['create_date']))
                sheet.write(row, 1, inv['order'])
                sheet.write(row, 2, inv['move_type'])
                sheet.write_number(row, 3, inv['cash_payment'], money)
                sheet.write_number(row, 4, inv['card_payment'], money)
                sheet.write_number(row, 5, inv['cheque_payment'], money)
                sheet.write_number(row, 6, inv['bank_payment'], money)
                sheet.write_number(row, 7, inv['grand_total'], money)
                sheet.write_number(row, 8, inv['paid_total'], money)
                sheet.write_number(row, 9, inv['due_total'], money)
                row += 1

            sheet.write(row, 0, f"Total for {user}", bold)
            sheet.write_number(row, 3, vals['cash_total'], money)
            sheet.write_number(row, 4, vals['card_total'], money)
            sheet.write_number(row, 5, vals['cheque_total'], money)
            sheet.write_number(row, 6, vals['bank_total'], money)
            sheet.write_number(row, 7, vals['grand_total'], money)
            sheet.write_number(row, 8, vals['paid_total'], money)
            sheet.write_number(row, 9, vals['due_total'], money)
            row += 2

        sheet.write(row, 0, "Salesman Summary", bold)
        row += 1
        sheet.write_row(row, 0, ["Salesperson", "Card", "Cash", "Cheque", "Bank", "Due"], bold)
        row += 1
        for user, vals in user_data.items():
            sheet.write(row, 0, user)
            sheet.write_number(row, 1, vals['card_total'], money)
            sheet.write_number(row, 2, vals['cash_total'], money)
            sheet.write_number(row, 3, vals['cheque_total'], money)
            sheet.write_number(row, 4, vals['bank_total'], money)
            sheet.write_number(row, 5, vals['due_total'], money)
            row += 1

        row += 2
        sheet.write(row, 0, "Grand Summary", bold)
        row += 1
        total_card = sum(u['card_total'] for u in user_data.values())
        total_cash = sum(u['cash_total'] for u in user_data.values())
        total_cheque = sum(u['cheque_total'] for u in user_data.values())
        total_bank = sum(u['bank_total'] for u in user_data.values())
        total_due = sum(u['due_total'] for u in user_data.values())

        sheet.write_row(row, 0, ['Total Credit Card', total_card], money)
        row += 1
        sheet.write_row(row, 0, ['Total Cash', total_cash], money)
        row += 1
        sheet.write_row(row, 0, ['Total Cheque', total_cheque], money)
        row += 1
        sheet.write_row(row, 0, ['Total Bank', total_bank], money)
        row += 1
        sheet.write_row(row, 0, ['Grand Total', total_card + total_cash + total_cheque + total_bank], money)

        workbook.close()
        output.seek(0)
        excel_data = output.read()

        attachment = self.env['ir.attachment'].create({
            'name': 'account_sales_report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }



class AccountInvoiceReportWizard(models.TransientModel):
    _name = "account.invoices.report"

    date_from = fields.Date(string='Start Date', default=date.today().replace(day=1), required=True)
    date_to = fields.Date(string='End Date', default=date.today(), required=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id.id)

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
            },
        }

        return self.env.ref('dynamic_invoice_sale_report.action_account_invoice_report').report_action(self, data=data)
