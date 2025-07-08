from odoo import models, fields, api
from odoo.exceptions import ValidationError

class POSProfitReportWizard(models.TransientModel):
    _name = 'pos.profit.report.wizard'
    _description = 'POS Profitability Report Wizard'

    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    config_ids = fields.Many2one('pos.config', string='POS Configurations')

    @api.constrains('date_start', 'date_end')
    def _check_date_range(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                if rec.date_start > rec.date_end:
                    raise ValidationError("Start date must be before end date.")
                if (rec.date_end - rec.date_start).days > 31:
                    raise ValidationError("The selected date range cannot exceed 31 days.")

    def _get_report_data(self):
        domain = [
            ('order_id.date_order', '>=', self.date_start),
            ('order_id.date_order', '<=', self.date_end)
        ]
        if self.config_ids:
            domain += [('order_id.session_id.config_id', 'in', self.config_ids.ids)]

        order_lines = self.env['pos.order.line'].search(domain)

        product_map = {}

        for line in order_lines:
            product = line.product_id
            product_key = product.id

            if product_key not in product_map:
                product_map[product_key] = {
                    'product': product.display_name,
                    'category': product.categ_id.name,
                    'total_qty': 0.0,
                    'total_price': 0.0,
                    'total_cost': 0.0,
                    'total_margin': 0.0,
                    'unit_prices': [],
                    'unit_costs': [],
                }

            item = product_map[product_key]
            line_cost = product.standard_price * line.qty
            line_margin = line.price_subtotal - line_cost

            item['total_qty'] += line.qty
            item['total_price'] += line.price_subtotal
            item['total_cost'] += line_cost
            item['total_margin'] += line_margin
            item['unit_prices'].append(line.price_unit)
            item['unit_costs'].append(product.standard_price)

        # Aggregate and round results
        report_data = []
        for item in product_map.values():
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
            # report_data.append({
            #     'product': item['product'],
            #     'category': item['category'],
            #     'qty': f"{qty:,.2f}",
            #     'unit_price': f"{average_unit_price:,.2f}",
            #     'unit_cost': f"{average_unit_cost:,.2f}",
            #     'total_cost': f"{total_cost:,.2f}",
            #     'subtotal': f"{subtotal:,.2f}",
            #     'margin': f"{margin:,.2f}",
            #     'margin_percent': f"{margin_percent:,.2f}",
            # })

        print(f"Aggregated report data: {report_data}")
        return report_data

    def action_export_pdf(self):
        return self.env.ref('bk_profit_margin_report.action_report_pos_profit').report_action(self)

    def action_export_excel(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/binary/download_pos_profit_excel?wizard_id={self.id}',
            'target': 'self',
        }
