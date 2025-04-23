from odoo import models, fields , api
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP

class CustomerStatementLine(models.Model):
    _name = 'custom.customer.statement.line'
    _description = 'Customer Statement Line'

    partner_id = fields.Many2one('res.partner', string='Customer')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_date = fields.Date(related='invoice_id.invoice_date', store=True)
    due_date = fields.Date(related='invoice_id.invoice_date_due', store=True)
    amount_total = fields.Monetary(related='invoice_id.amount_total', store=True)
    balance = fields.Monetary(string='Balance',compute='_compute_balance')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True)

    def _compute_balance(self):
        for record in self:
            balance = 0
            previous_records = self.search([
                ('partner_id', '=', record.partner_id.id),
                ('invoice_date', '<', record.invoice_date)
            ], order='invoice_date')
            for prev_record in previous_records:
                balance += prev_record.amount_total
            record.balance = balance + record.amount_total


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_statement_count = fields.Integer(
        string='Customer Statement Count',
        compute='_compute_customer_statement_count'
    )

    def _compute_customer_statement_count(self):
        for partner in self:
            partner.customer_statement_count = self.env['account.move'].search_count([
                        ('partner_id', '=', self.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),  
                        ('state', '=', 'posted')
                    ])
          

    def action_view_customer_statement(self):
        self.ensure_one()

        self.env['custom.customer.statement.line'].search([('partner_id', '=', self.id)]).unlink()

        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),  
            ('state', '=', 'posted')
        ])

        for invoice in invoices:
            self.env['custom.customer.statement.line'].create({
                'partner_id': self.id,
                'invoice_id': invoice.id,
                'balance': invoice.amount_residual,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Statement',
            'res_model': 'custom.customer.statement.line',
            'view_mode': 'tree',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }


    sale_warn = fields.Selection(WARNING_MESSAGE, 'Sales Warnings', default='no-message', help=WARNING_HELP)
    sale_warn_msg = fields.Text('Message for Sales Order')
