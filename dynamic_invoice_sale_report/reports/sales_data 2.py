from odoo import api, models


class SalesReport(models.AbstractModel):
    _name = 'report.dynamic_invoice_sale_report.account_sales_data_view'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']

        domain = [('create_date', '>=', date_from),
                  ('create_date', '<=', date_to),
                  ('state', '!=', 'cancel'),
                  ('move_type', '=', 'out_invoice')]

        account_moves = self.env['account.move'].search(domain)

        user_data = {}  # Dictionary to group invoices by user

        for account in account_moves:
            user = account.user_id.name or "Unknown User"

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
                    'card_total': 0,
                }

            bank_payment = cash_payment = card_payment = 0

            if account.invoice_payments_widget:
                for payment in account.invoice_payments_widget.get('content', []):
                    if payment.get('journal_name') == 'Bank':
                        bank_payment += payment['amount']
                    elif payment.get('journal_name') == 'Cash':
                        cash_payment += payment['amount']
                    elif payment.get('journal_name') == 'Credit Card':
                        card_payment += payment['amount']

            untaxed_total = account.amount_untaxed
            tax_total = account.amount_tax
            grand_total = account.amount_total
            paid_total = grand_total - account.amount_residual
            due_total = account.amount_residual

            user_data[user]['invoices'].append({
                'create_date': account.create_date,
                'order': account.name,
                'cash_payment': cash_payment,
                'card_payment': card_payment,
                'bank_payment': bank_payment,

                'untaxed_total': untaxed_total,
                'tax_total': tax_total,
                'grand_total': grand_total,

                'paid_total': paid_total,
                'due_total': due_total,
            })

            user_data[user]['untaxed_total'] += untaxed_total
            user_data[user]['tax_total'] += tax_total
            user_data[user]['grand_total'] += grand_total
            user_data[user]['paid_total'] += paid_total
            user_data[user]['due_total'] += due_total
            user_data[user]['cash_total'] += cash_payment
            user_data[user]['bank_total'] += bank_payment
            user_data[user]['card_total'] += card_payment

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_from': date_from,
            'date_to': date_to,
            'user_data': user_data,  # Pass grouped data
        }
