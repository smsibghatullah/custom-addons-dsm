from odoo import models, fields , api
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from datetime import datetime
import io
import base64
import xlsxwriter

class CustomerStatementLine(models.Model):
    _name = 'custom.customer.statement.line'
    _description = 'Customer Statement Line'

    partner_id = fields.Many2one('res.partner', string='Customer')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_date = fields.Date(related='invoice_id.invoice_date', store=True)
    due_date = fields.Date(related='invoice_id.invoice_date_due', store=True)
    balance = fields.Monetary(string='Balance',compute='_compute_balance')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True)
    balance_footer = fields.Monetary(string="Balance Footer", compute='_compute_balance_footer', store=False)
    invoice_ref = fields.Char(related='invoice_id.ref', string='LPO / REF No', store=True)
    delivery_note = fields.Char(related='invoice_id.name', string='D.N No', store=True)
    invoice_transaction_type = fields.Selection(
        'account.move',
        related='invoice_id.move_type',
        string='TRX Type',
        store=True
    )
    debit = fields.Monetary(string="Debit", compute="_compute_debit_credit", store=True)
    credit = fields.Monetary(string="Credit", compute="_compute_debit_credit", store=True)
    due_days = fields.Integer(string="Due Days", compute="_compute_due_days", store=True)
    amount_total = fields.Monetary(string="Amount Total", compute="_compute_amount_total", store=True)

    @api.depends('debit', 'credit')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = (record.debit or 0.0) - (record.credit or 0.0)

    @api.depends('invoice_date', 'due_date')
    def _compute_due_days(self):
        for rec in self:
            if rec.due_date and rec.invoice_date:
                rec.due_days = (rec.due_date - rec.invoice_date).days
            else:
                rec.due_days = 0


    @api.depends('invoice_id.payment_state', 'invoice_id.amount_total', 'invoice_id.amount_residual')
    def _compute_debit_credit(self):
        for record in self:
            if record.invoice_id:
                paid_amount = record.invoice_id.amount_total - record.invoice_id.amount_residual

                record.credit = paid_amount
                record.debit = record.invoice_id.amount_total  
            else:
                record.credit = 0.0
                record.debit = 0.0

    def _compute_balance_footer(self):
        all_records = self.search([], order='invoice_date asc, id asc')  
        last_id = all_records[-1].id if all_records else False
        for rec in self:
            rec.balance_footer = rec.balance if rec.id == last_id else 0.0

    def print_customer_statement(self):
         return self.env.ref('customer_statement.action_report_customer_statement').report_action(self)

    @api.depends('amount_total', 'partner_id')
    def _compute_balance(self):
        grouped_records = {}

        for rec in self:
            grouped_records.setdefault(rec.partner_id.id, []).append(rec)

        for partner_id, records in grouped_records.items():
            balance = 0.0
            for rec in records:
                balance += rec.amount_total
                rec.balance = balance

    def export_to_excel(self):
            import io
            import base64
            from datetime import datetime
            import xlsxwriter

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('Customer Statement')

            bold = workbook.add_format({'bold': True})
            center_bold = workbook.add_format({'bold': True, 'align': 'center'})
            right_align = workbook.add_format({'align': 'right'})
            money = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
            date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center'})

            sheet.merge_range('A1:L1', 'CUSTOMER STATEMENT', workbook.add_format({'bold': True, 'align': 'center', 'font_size': 14, 'font_color': '#C00000'}))

            partner = self[0].partner_id.name if self else ''
            today = datetime.today().strftime('%d-%m-%Y')
            sheet.write('A3', 'Partner:', bold)
            sheet.write('B3', partner)
            sheet.write('K3', 'Date:', bold)
            sheet.write('L3', today)

            headers = ['Reference', 'Invoice Date', 'Due Date', 'TRX Type', 'LPO / REF No', 'D.N No',
                    'Debit', 'Credit', 'Amount', 'Currency', 'Balance', 'Due Days']
            sheet.set_column('A:L', 15)
            for col, header in enumerate(headers):
                sheet.write(4, col, header, center_bold)

            row = 5
            total_amount = 0.0
            total_balance = 0.0

            for line in self:
                sheet.write(row, 0, line.invoice_id.name or '')
                sheet.write(row, 1, line.invoice_date.strftime('%Y-%m-%d') if line.invoice_date else '', date_fmt)
                sheet.write(row, 2, line.due_date.strftime('%Y-%m-%d') if line.due_date else '', date_fmt)
                sheet.write(row, 3, line.invoice_transaction_type or '')
                sheet.write(row, 4, line.invoice_ref or '')
                sheet.write(row, 5, line.delivery_note or '')
                sheet.write(row, 6, line.debit or 0.0, money)
                sheet.write(row, 7, line.credit or 0.0, money)
                sheet.write(row, 8, line.amount_total or 0.0, money)
                sheet.write(row, 9, line.currency_id.name or '')
                sheet.write(row, 10, line.balance or 0.0, money)
                sheet.write(row, 11, line.due_days or 0, right_align)

                total_amount += line.amount_total or 0.0
                total_balance += line.balance_footer or 0.0
                row += 1

            sheet.write(row + 1, 7, 'Total Amount:', bold)
            sheet.write(row + 1, 8, total_amount, money)
            sheet.write(row + 2, 7, 'Total Balance:', bold)
            sheet.write(row + 2, 8, total_balance, money)
            sheet.write(row + 1, 9, self[0].currency_id.name if self else '', bold)
            sheet.write(row + 2, 9, self[0].currency_id.name if self else '', bold)

            workbook.close()
            output.seek(0)

            filename = f"Customer_Statement_{datetime.today().strftime('%Y-%m-%d')}.xlsx"
            file_data = base64.b64encode(output.read())

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': file_data,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }


class VendorStatementLine(models.Model):
    _name = 'custom.vendor.statement.line'
    _description = 'Vendor Statement Line'

    partner_id = fields.Many2one('res.partner', string='Vendor')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_date = fields.Date(related='invoice_id.invoice_date', store=True)
    due_date = fields.Date(related='invoice_id.invoice_date_due', store=True)
    balance = fields.Monetary(string='Balance',compute='_compute_balance')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True)
    balance_footer = fields.Monetary(string="Balance Footer", compute='_compute_balance_footer', store=False)
    invoice_ref = fields.Char(related='invoice_id.ref', string='LPO / REF No', store=True)
    delivery_note = fields.Char(related='invoice_id.name', string='D.N No', store=True)
    invoice_transaction_type = fields.Selection(
        'account.move',
        related='invoice_id.move_type',
        string='TRX Type',
        store=True
    )
    debit = fields.Monetary(string="Debit", compute="_compute_debit_credit", store=True)
    credit = fields.Monetary(string="Credit", compute="_compute_debit_credit", store=True)
    due_days = fields.Integer(string="Due Days", compute="_compute_due_days", store=True)
    amount_total = fields.Monetary(string="Amount Total", compute="_compute_amount_total", store=True)

    @api.depends('debit', 'credit')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = (record.debit or 0.0) - (record.credit or 0.0)


    @api.depends('invoice_date', 'due_date')
    def _compute_due_days(self):
        for rec in self:
            if rec.due_date and rec.invoice_date:
                rec.due_days = (rec.due_date - rec.invoice_date).days
            else:
                rec.due_days = 0


    @api.depends('invoice_id.payment_state', 'invoice_id.amount_total', 'invoice_id.amount_residual')
    def _compute_debit_credit(self):
        for record in self:
            if record.invoice_id:
                paid_amount = record.invoice_id.amount_total - record.invoice_id.amount_residual

                record.credit = paid_amount
                record.debit = record.invoice_id.amount_total  
            else:
                record.credit = 0.0
                record.debit = 0.0


    @api.depends('balance')
    def _compute_balance_footer(self):
        for rec in self:
            rec.balance_footer = 0.0

        if self:
            last_id = self.sorted(key=lambda r: (r.invoice_date, r.id))[-1].id
            for rec in self:
                rec.balance_footer = rec.balance if rec.id == last_id else 0.0


    def print_vendor_statement(self):
         return self.env.ref('customer_statement.action_report_vendor_statement').report_action(self)

    @api.depends('amount_total', 'partner_id')
    def _compute_balance(self):
        grouped_records = {}

        for rec in self:
            grouped_records.setdefault(rec.partner_id.id, []).append(rec)

        for partner_id, records in grouped_records.items():
            balance = 0.0
            for rec in records:
                balance += rec.amount_total
                rec.balance = balance

    def export_to_excel(self):
            import io
            import base64
            from datetime import datetime
            import xlsxwriter

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('Vendor Statement')

            bold = workbook.add_format({'bold': True})
            center_bold = workbook.add_format({'bold': True, 'align': 'center'})
            right_align = workbook.add_format({'align': 'right'})
            money = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
            date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center'})

            sheet.merge_range('A1:L1', 'VENDOR STATEMENT', workbook.add_format({'bold': True, 'align': 'center', 'font_size': 14, 'font_color': '#C00000'}))

            partner = self[0].partner_id.name if self else ''
            today = datetime.today().strftime('%d-%m-%Y')
            sheet.write('A3', 'Partner:', bold)
            sheet.write('B3', partner)
            sheet.write('K3', 'Date:', bold)
            sheet.write('L3', today)

            headers = ['Reference', 'Invoice Date', 'Due Date', 'TRX Type', 'LPO / REF No', 'D.N No',
                    'Debit', 'Credit', 'Amount', 'Currency', 'Balance', 'Due Days']
            sheet.set_column('A:L', 15)
            for col, header in enumerate(headers):
                sheet.write(4, col, header, center_bold)

            row = 5
            total_amount = 0.0
            total_balance = 0.0

            for line in self:
                sheet.write(row, 0, line.invoice_id.name or '')
                sheet.write(row, 1, line.invoice_date.strftime('%Y-%m-%d') if line.invoice_date else '', date_fmt)
                sheet.write(row, 2, line.due_date.strftime('%Y-%m-%d') if line.due_date else '', date_fmt)
                sheet.write(row, 3, line.invoice_transaction_type or '')
                sheet.write(row, 4, line.invoice_ref or '')
                sheet.write(row, 5, line.delivery_note or '')
                sheet.write(row, 6, line.debit or 0.0, money)
                sheet.write(row, 7, line.credit or 0.0, money)
                sheet.write(row, 8, line.amount_total or 0.0, money)
                sheet.write(row, 9, line.currency_id.name or '')
                sheet.write(row, 10, line.balance or 0.0, money)
                sheet.write(row, 11, line.due_days or 0, right_align)

                total_amount += line.amount_total or 0.0
                total_balance += line.balance_footer or 0.0
                row += 1

            sheet.write(row + 1, 7, 'Total Amount:', bold)
            sheet.write(row + 1, 8, total_amount, money)
            sheet.write(row + 2, 7, 'Total Balance:', bold)
            sheet.write(row + 2, 8, total_balance, money)
            sheet.write(row + 1, 9, self[0].currency_id.name if self else '', bold)
            sheet.write(row + 2, 9, self[0].currency_id.name if self else '', bold)

            workbook.close()
            output.seek(0)

            filename = f"Vendor_Statement_{datetime.today().strftime('%Y-%m-%d')}.xlsx"
            file_data = base64.b64encode(output.read())

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': file_data,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }



class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_statement_count = fields.Integer(
        string='Customer Statement Count',
        compute='_compute_customer_statement_count'
    )
    vendor_statement_count = fields.Integer(
        string='Customer Statement Count',
        compute='_compute_vendor_statement_count'
    )

    def _compute_vendor_statement_count(self):
        for partner in self:
            partner.vendor_statement_count = self.env['account.move'].search_count([
                        ('partner_id', '=', self.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund','in_receipt']),  
                        ('state', '=', 'posted'),
                        ('invoice_origin', 'ilike', 'P%')
                    ])

    def _compute_customer_statement_count(self):
        for partner in self:
            partner.customer_statement_count = self.env['account.move'].search_count([
                        ('partner_id', '=', self.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund','out_receipt']),  
                        ('state', '=', 'posted'),
                        ('invoice_origin', 'ilike', 'S%')
                    ])

    def action_view_vendor_statement(self):
        self.ensure_one()

        self.env['custom.vendor.statement.line'].search([('partner_id', '=', self.id)]).unlink()

        invoices = self.env['account.move'].search([
                        ('partner_id', '=', self.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund','in_receipt']),  
                        ('state', '=', 'posted'),
                        ('invoice_origin', 'ilike', 'P%')
        ])

        for invoice in invoices:
            self.env['custom.vendor.statement.line'].create({
                'partner_id': self.id,
                'invoice_id': invoice.id,
                'balance': invoice.amount_residual,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Statement',
            'res_model': 'custom.vendor.statement.line',
            'view_mode': 'tree',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

          

    def action_view_customer_statement(self):
        self.ensure_one()

        self.env['custom.customer.statement.line'].search([('partner_id', '=', self.id)]).unlink()

        invoices = self.env['account.move'].search([
                        ('partner_id', '=', self.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund','out_receipt']),  
                        ('state', '=', 'posted'),
                        ('invoice_origin', 'ilike', 'S%')
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


class ReportCustomerStatement(models.AbstractModel):
    _name = 'report.customer_statement.report_customer_statement'
    _description = 'Customer Statement Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['custom.customer.statement.line'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'custom.customer.statement.line',
            'docs': docs,
            'datetime': datetime,  
        }

class ReportVendorStatement(models.AbstractModel):
    _name = 'report.customer_statement.report_vendor_statement'
    _description = 'Vendor Statement Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['custom.vendor.statement.line'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'custom.vendor.statement.line',
            'docs': docs,
            'datetime': datetime,  
        }