from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BkSalesProfitReportWizard(models.TransientModel):
    _name = 'sales.profit.report.wizard'
    _description = 'Sales Profitability Report Wizard'

    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    # name = fields.Date(string="Description Name")
    category_ids = fields.Many2many('product.category', string='Product Categories')
    order_id = fields.Many2many('sale.order',  string="Orders")

    @api.constrains('date_start', 'date_end', 'order_id')
    def _check_date_or_order(self):
        for rec in self:
            # Ensure at least date range or sales order is selected
            if not rec.date_start and not rec.date_end and not rec.order_id:
                raise ValidationError("Please provide either a date range or select sales orders.")

            # If both start and end dates are provided, validate the range
            if rec.date_start and rec.date_end:
                if rec.date_start > rec.date_end:
                    raise ValidationError("Start date must be before end date.")
                if (rec.date_end - rec.date_start).days > 31:
                    raise ValidationError("The selected date range cannot exceed 31 days.")

    def _get_report_data(self):
        if not self.date_start and not self.date_end and not self.order_id:
            raise ValidationError("Please select a date range or specific sales orders.")

        domain = [('state', 'in', ['sale', 'done'])]

        if self.order_id:
            domain.append(('order_id', 'in', self.order_id.ids))
        else:
            if self.date_start:
                domain.append(('order_id.date_order', '>=', self.date_start))
            if self.date_end:
                domain.append(('order_id.date_order', '<=', self.date_end))

        if self.category_ids:
            domain.append(('product_id.categ_id', 'in', self.category_ids.ids))

        order_lines = self.env['sale.order.line'].search(domain)

        product_data = {}
        for line in order_lines:
            product = line.product_id
            product_id = product.id

            if product_id not in product_data:
                product_data[product_id] = {
                    'product': product.display_name,
                    'category': product.categ_id.name,
                    'total_qty': 0.0,
                    'total_price': 0.0,
                    'total_cost': 0.0,
                    'total_margin': 0.0,
                    'unit_prices': [],
                    'unit_costs': [],
                }

            item = product_data[product_id]
            line_cost = line.purchase_price * line.product_uom_qty
            margin = line.price_subtotal - line_cost

            item['total_qty'] += line.product_uom_qty
            item['total_price'] += line.price_subtotal
            item['total_cost'] += line_cost
            item['total_margin'] += margin
            item['unit_prices'].append(line.price_unit)
            item['unit_costs'].append(line.purchase_price)

        report_data = []
        for item in product_data.values():
            qty = item['total_qty']
            subtotal = item['total_price']
            total_cost = item['total_cost']
            margin = item['total_margin']
            margin_percent = (margin / subtotal * 100) if subtotal else 0.0
            average_unit_price = sum(item['unit_prices']) / len(item['unit_prices']) if item['unit_prices'] else 0.0
            average_unit_cost = sum(item['unit_costs']) / len(item['unit_costs']) if item['unit_costs'] else 0.0

            report_data.append({
                'product': item['product'],
                'category': item['category'],
                'qty': round(qty, 2),
                'unit_price': round(average_unit_price, 2),
                'unit_cost': round(average_unit_cost, 2),
                'total_cost': round(total_cost, 2),
                'subtotal': round(subtotal, 2),
                'margin': round(margin, 2),
                'margin_percent': round(margin_percent, 2),
            })

        # Top 5 most profitable products
        top_products = sorted(report_data, key=lambda x: x['margin'], reverse=True)[:5]

        # Top 5 least profitable products
        bottom_products = sorted(report_data, key=lambda x: x['margin'])[:5]

        # Category-wise summary
        from collections import defaultdict
        category_summary = defaultdict(lambda: {
            'qty': 0.0,
            'revenue': 0.0,
            'cost': 0.0,
            'margin': 0.0,
        })

        for item in report_data:
            cat = item['category']
            category_summary[cat]['qty'] += item['qty']
            category_summary[cat]['revenue'] += item['subtotal']
            category_summary[cat]['cost'] += item['total_cost']
            category_summary[cat]['margin'] += item['margin']

        # Convert category summary to list format
        category_data = []
        for cat, vals in category_summary.items():
            margin_percent = (vals['margin'] / vals['revenue'] * 100) if vals['revenue'] else 0.0
            category_data.append({
                'category': cat,
                'qty': round(vals['qty'], 2),
                'revenue': round(vals['revenue'], 2),
                'cost': round(vals['cost'], 2),
                'margin': round(vals['margin'], 2),
                'margin_percent': round(margin_percent, 2),
            })

        return {
            'lines': report_data,
            'top_products': top_products,
            'least_profitable_products': bottom_products,
            'category_summary': category_data,
        }

    def action_export_pdf(self):
        return self.env.ref('bk_sales_profit_margin_report.action_report_sales_profit').report_action(self)

    def action_export_excel(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/binary/download_sales_profit_excel?wizard_id={self.id}',
            'target': 'self',
        }
