from odoo import api, models


class InvoicesReport(models.AbstractModel):
    _name = 'report.dynamic_invoice_sale_report.account_sales_data_view_03'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']

        domain = [
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('state', '!=', 'cancel'),
            ('move_type', '=', 'out_invoice')
        ]

        invoices = self.env['account.move'].search(domain)
        report_data = []

        for invoice in invoices:
            for line in invoice.invoice_line_ids:
                report_data.append({
                    'date': invoice.invoice_date,
                    'time': invoice.invoice_date.strftime('%H:%M:%S') if invoice.invoice_date else '',
                    'invoice_no': invoice.name,
                    'product': line.product_id.name or '',
                    'category': line.product_id.categ_id.name or '',
                    'brand': line.product_id.product_brand_id.name if hasattr(line.product_id, 'product_brand_id') else '',
                    'qty': line.quantity,
                    'cost': line.product_id.standard_price,
                    'price': line.price_unit,
                    'vat': line.tax_ids.amount if line.tax_ids else 0.0,
                    'total_amount': line.price_total,
                })

        return {
            'doc_ids': docids,
            'doc_model': data['model'],
            'date_from': date_from,
            'date_to': date_to,
            'report_data': report_data,
        }
