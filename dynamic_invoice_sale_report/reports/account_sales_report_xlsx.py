from odoo import models
from io import BytesIO
import xlsxwriter

class AccountSalesExcelReport(models.AbstractModel):
    _name = 'report.dynamic_invoice_sale_report.report_account_sales_excel'
    _inherit = 'report.report_xlsx.abstract'


    def generate_xlsx_report(self, workbook, data, objects):
        sheet = workbook.add_worksheet('Account Sales')
        bold = workbook.add_format({'bold': True})
        center = workbook.add_format({'align': 'center'})

        row = 0
        sheet.merge_range(row, 0, row, 9, "Account Sales Report", bold)
        row += 2

        # Headers
        headers = [
            'Date & Time', 'Order No.', 'Type', 'Cash', 'Customer Invoice',
            'Cheque', 'Bank', 'Total With VAT', 'Paid Amount', 'Due Amount'
        ]
        for col, header in enumerate(headers):
            sheet.write(row, col, header, bold)
        row += 1

        # Prepare domain & fetch data
        user_data = self._get_data(data)

        for username, vals in user_data.items():
            # User header
            sheet.write(row, 0, f"Salesperson: {username}", bold)
            row += 1

            for inv in vals['invoices']:
                sheet.write(row, 0, inv['create_date'], center)
                sheet.write(row, 1, inv['order'], center)
                sheet.write(row, 2, inv['move_type'], center)
                sheet.write(row, 3, inv['cash_payment'], center)
                sheet.write(row, 4, inv['customer_invoice_total'], center)
                sheet.write(row, 5, inv['cheque_payment'], center)
                sheet.write(row, 6, inv['bank_payment'], center)
                sheet.write(row, 7, inv['grand_total'], center)
                sheet.write(row, 8, inv['paid_total'], center)
                sheet.write(row, 9, inv['due_total'], center)
                row += 1

            # Subtotal per user
            sheet.write(row, 0, 'Subtotal', bold)
            sheet.write(row, 3, vals['cash_total'], center)
            sheet.write(row, 4, vals['customer_invoice_total'], center)
            sheet.write(row, 5, vals['cheque_total'], center)
            sheet.write(row, 6, vals['bank_total'], center)
            sheet.write(row, 7, vals['grand_total'], center)
            sheet.write(row, 8, vals['paid_total'], center)
            sheet.write(row, 9, vals['due_total'], center)
            row += 2

        # Summary headers
        sheet.write(row, 0, 'Salesman Summary', bold)
        row += 1
        sheet.write_row(row, 0, ['Sales Person', 'Credit Card', 'Cash', 'Cheque', 'Bank', 'Due Amount'], bold)
        row += 1

        for username, vals in user_data.items():
            sheet.write_row(row, 0, [
                username, vals['customer_invoice_total'], vals['cash_total'],
                vals['cheque_total'], vals['bank_total'], vals['due_total']
            ])
            row += 1

        # Grand Summary
        sheet.write(row, 0, 'Grand Summary', bold)
        row += 1

        def total_sum(key):
            return sum(u[1][key] for u in user_data.items())

        sheet.write_row(row, 0, ['Total Credit Card', total_sum('customer_invoice_total')])
        row += 1
        sheet.write_row(row, 0, ['Total Cash', total_sum('cash_total')])
        row += 1
        sheet.write_row(row, 0, ['Total Cheque', total_sum('cheque_total')])
        row += 1
        sheet.write_row(row, 0, ['Total Bank', total_sum('bank_total')])
        row += 1
        sheet.write_row(row, 0, ['Grand Total', total_sum('customer_invoice_total') +
                                            total_sum('cash_total') +
                                            total_sum('cheque_total') +
                                            total_sum('bank_total')])
        row += 1

    def _get_data(self, data):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        domain = [
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
            ('state', '!=', 'cancel'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ]

        account_moves = self.env['account.move'].search(domain)
        user_data = {}

        for account in account_moves:
            user = account.invoice_user_id.name or "Unknown User"
            move_type = account.move_type

            if user not in user_data:
                user_data[user] = {
                    'invoices': [],
                    'untaxed_total': 0,
                    'tax_total': 0,
                    'grand_total': 0,
                    'paid_total': 0,
                    'due_total': 0,
                    'cash_total': 0,
                    'bank_total': 0,
                    'customer_invoice_total': 0,
                    'cheque_total': 0,
                }

            payments = self.env['account.payment']
            for line in account.line_ids:
                if line.account_id.internal_type in ('receivable', 'payable'):
                    for matched in line.matched_debit_ids + line.matched_credit_ids:
                        if matched.debit_move_id.payment_id:
                            payments += matched.debit_move_id.payment_id
                        if matched.credit_move_id.payment_id:
                            payments += matched.credit_move_id.payment_id

            cash_payment = bank_payment = cheque_payment = 0
            for p in payments:
                if p.journal_id.type == 'cash':
                    cash_payment += p.amount
                elif p.journal_id.type == 'bank':
                    bank_payment += p.amount
                elif p.journal_id.name.lower().find('cheque') >= 0:
                    cheque_payment += p.amount

            grand_total = account.amount_total
            paid_total = cash_payment + bank_payment + cheque_payment
            due_total = grand_total - paid_total

            inv_data = {
                'create_date': str(account.create_date),
                'order': account.name,
                'move_type': "Invoice" if move_type == 'out_invoice' else "Credit Note",
                'cash_payment': cash_payment,
                'cheque_payment': cheque_payment,
                'bank_payment': bank_payment,
                'customer_invoice_total': account.amount_total if move_type == 'out_invoice' else -account.amount_total,
                'grand_total': grand_total,
                'paid_total': paid_total,
                'due_total': due_total,
            }

            user_data[user]['invoices'].append(inv_data)
            user_data[user]['cash_total'] += cash_payment
            user_data[user]['cheque_total'] += cheque_payment
            user_data[user]['bank_total'] += bank_payment
            user_data[user]['grand_total'] += grand_total
            user_data[user]['paid_total'] += paid_total
            user_data[user]['due_total'] += due_total
            if move_type == 'out_invoice':
                user_data[user]['customer_invoice_total'] += account.amount_total
            elif move_type == 'out_refund':
                user_data[user]['customer_invoice_total'] -= account.amount_total

        return user_data
