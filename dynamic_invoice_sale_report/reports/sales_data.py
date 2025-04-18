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
                  ('move_type', 'in', ['out_invoice', 'out_refund'])]  # Include credit notes

        account_moves = self.env['account.move'].search(domain)

        user_data = {}
        for account in account_moves:
            user = account.invoice_user_id.name or "Unknown User"  # Use invoice_user_id instead of user_id
            move_type = account.move_type  # Identify invoice or refund

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
                    'cheque_total': 0,
                }

            bank_payment = cash_payment = cheque_payment = card_payment = 0
            payments = self.env['account.payment']
            for line in account.line_ids:
                if line.account_id.internal_type in ('receivable', 'payable'):
                    for payment_line in line.matched_debit_ids + line.matched_credit_ids:
                        if payment_line.debit_move_id.payment_id:
                            payments += payment_line.debit_move_id.payment_id
                        if payment_line.credit_move_id.payment_id:
                            payments += payment_line.credit_move_id.payment_id
            
            print(payments,"pppppppppppppppppppppppppppppppppppppppppppppppppppp")
            for payment in payments:
                journal_name = payment.journal_id.name
                amount = payment.amount

                if journal_name == 'Bank':
                    bank_payment += amount
                elif journal_name == 'Cash':
                    cash_payment += amount
                elif journal_name == 'Credit Card':
                    card_payment += amount
                elif journal_name == 'Cheque':
                    cheque_payment += amount

            grand_total = account.amount_total
            paid_total = grand_total - account.amount_residual
            due_total = account.amount_residual

            # If it's a refund, make the amounts negative
            if move_type == 'out_refund':
                grand_total *= -1
                paid_total *= -1
                due_total *= -1
                cash_payment *= -1
                bank_payment *= -1
                card_payment *= -1
                cheque_payment *= -1

            user_data[user]['invoices'].append({
                'create_date': account.create_date,
                'order': account.name,
                'move_type': "Credit Note" if move_type == 'out_refund' else "Invoice",
                'cash_payment': cash_payment,
                'card_payment': card_payment,
                'bank_payment': bank_payment,
                'cheque_payment': cheque_payment,
                'grand_total': grand_total,
                'paid_total': paid_total,
                'due_total': due_total,
            })

            user_data[user]['grand_total'] += grand_total
            user_data[user]['paid_total'] += paid_total
            user_data[user]['due_total'] += due_total
            user_data[user]['cash_total'] += cash_payment
            user_data[user]['bank_total'] += bank_payment
            user_data[user]['card_total'] += card_payment
            user_data[user]['cheque_total'] += cheque_payment

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_from': date_from,
            'date_to': date_to,
            'user_data': user_data,
        }

