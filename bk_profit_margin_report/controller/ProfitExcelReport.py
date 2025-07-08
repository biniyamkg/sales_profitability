from odoo import http
from odoo.http import request
import io
import xlsxwriter

class POSProfitReportController(http.Controller):

    @http.route('/web/binary/download_pos_profit_excel', type='http', auth='user')
    def download_pos_profit_excel(self, wizard_id=None, **kwargs):
        wizard = request.env['pos.profit.report.wizard'].sudo().browse(int(wizard_id))
        data = wizard._get_report_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Profitability Report')

        # Styles
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9D9D9',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        number_format = workbook.add_format({
            'num_format': '#,##0.00',
            'align': 'right'
        })

        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'align': 'right'
        })

        text_format = workbook.add_format({'align': 'left'})
        center_format = workbook.add_format({'align': 'center'})

        # Add title and metadata
        sheet.merge_range('A1:I1', 'POS Profitability Report', workbook.add_format({'bold': True, 'font_size': 14}))
        pos_names = ', '.join(wizard.config_ids.mapped('name')) or 'All POS'
        sheet.merge_range('A2:I2', f"POS: {pos_names}", text_format)
        sheet.merge_range('A3:I3', f"Date: {wizard.date_start} to {wizard.date_end}", text_format)

        row_offset = 8  # Leave top 8 rows for title/meta

        # Headers
        headers = ['Product', 'Category', 'Qty', 'Unit Price', 'Unit Cost', 'Total Cost', 'Subtotal', 'Margin', 'Margin %']
        for col, header in enumerate(headers):
            sheet.write(row_offset, col, header, header_format)

        # Totals
        total_qty = total_cost = total_sales = total_margin = 0.0

        # Content rows
        for row_idx, line in enumerate(data, start=row_offset + 1):
            qty = float(line['qty'])
            unit_price = float(line['unit_price'])
            unit_cost = float(line['unit_cost'])
            total_cost_val = float(line['total_cost'])
            subtotal = float(line['subtotal'])
            margin = float(line['margin'])
            margin_percent = float(line['margin_percent']) / 100.0  # for percent formatting

            sheet.write(row_idx, 0, line['product'], text_format)
            sheet.write(row_idx, 1, line['category'], text_format)
            sheet.write_number(row_idx, 2, qty, number_format)
            sheet.write_number(row_idx, 3, unit_price, number_format)
            sheet.write_number(row_idx, 4, unit_cost, number_format)
            sheet.write_number(row_idx, 5, total_cost_val, number_format)
            sheet.write_number(row_idx, 6, subtotal, number_format)
            sheet.write_number(row_idx, 7, margin, number_format)
            sheet.write_number(row_idx, 8, margin_percent, percent_format)

            total_qty += qty
            total_cost += total_cost_val
            total_sales += subtotal
            total_margin += margin
        # --- Compute KPI values first ---
        total_sales = sum(float(line['subtotal']) for line in data)
        total_cost = sum(float(line['total_cost']) for line in data)
        total_margin = sum(float(line['margin']) for line in data)
        margin_percent = (total_margin / total_sales) if total_sales else 0.0

        # KPI styles
        kpi_label_format = workbook.add_format({'bold': True, 'align': 'left'})
        kpi_value_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'align': 'right'})
        kpi_percent_format = workbook.add_format({'bold': True, 'num_format': '0.00%', 'align': 'right'})

        # KPI rows (after metadata)
        sheet.write('A4', 'Total Sales', kpi_label_format)
        sheet.write('B4', total_sales, kpi_value_format)

        sheet.write('A5', 'Total Cost', kpi_label_format)
        sheet.write('B5', total_cost, kpi_value_format)

        sheet.write('A6', 'Total Margin', kpi_label_format)
        sheet.write('B6', total_margin, kpi_value_format)

        sheet.write('A7', 'Margin %', kpi_label_format)
        sheet.write('B7', margin_percent, kpi_percent_format)


        # Footer: Totals row
        footer_row = row_idx + 1
        sheet.write(footer_row, 0, 'Total', header_format)
        sheet.write(footer_row, 1, '', header_format)
        sheet.write_number(footer_row, 2, total_qty, number_format)
        sheet.write(footer_row, 3, '', header_format)
        sheet.write(footer_row, 4, '', header_format)
        sheet.write_number(footer_row, 5, total_cost, number_format)
        sheet.write_number(footer_row, 6, total_sales, number_format)
        sheet.write_number(footer_row, 7, total_margin, number_format)

        avg_margin_percent = (total_margin / total_sales) if total_sales else 0.0
        sheet.write_number(footer_row, 8, avg_margin_percent, percent_format)

        # Set column widths
        sheet.set_column('A:A', 25)  # Product
        sheet.set_column('B:B', 20)  # Category
        sheet.set_column('C:I', 15)  # Numbers

        workbook.close()
        output.seek(0)

        return request.make_response(output.read(), [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename="pos_profitability_report.xlsx"'),
        ])
