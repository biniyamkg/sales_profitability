from odoo import http
from odoo.http import request
import io
import xlsxwriter

class SalesProfitReportController(http.Controller):

    @http.route('/web/binary/download_sales_profit_excel', type='http', auth='user')
    def download_pos_profit_excel(self, wizard_id=None, **kwargs):
        wizard = request.env['sales.profit.report.wizard'].sudo().browse(int(wizard_id))
        data = wizard._get_report_data()

        lines = data['lines']
        top_products = data.get('top_products', [])
        bottom_products = data.get('least_profitable_products', [])
        category_summary = data.get('category_summary', [])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Profitability Report')

        # Styles
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        number_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        percent_format = workbook.add_format({'num_format': '0.00%', 'align': 'right'})
        text_format = workbook.add_format({'align': 'left'})
        center_format = workbook.add_format({'align': 'center'})
        bold_format = workbook.add_format({'bold': True})
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        kpi_label_format = workbook.add_format({'bold': True, 'align': 'left'})
        kpi_value_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'align': 'right'})
        kpi_percent_format = workbook.add_format({'bold': True, 'num_format': '0.00%', 'align': 'right'})

        # Title and metadata
        sheet.merge_range('A1:I1', 'Profitability Report', title_format)
        # pos_names = ', '.join(wizard.config_ids.mapped('name')) or 'All POS'
        # sheet.merge_range('A2:I2', f"POS: {pos_names}", text_format)
        sheet.merge_range('A3:I3', f"Date: {wizard.date_start} to {wizard.date_end}", text_format)

        # KPIs
        total_qty = sum(float(line['qty']) for line in lines)
        total_sales = sum(float(line['subtotal']) for line in lines)
        total_cost = sum(float(line['total_cost']) for line in lines)
        total_margin = sum(float(line['margin']) for line in lines)
        avg_margin_percent = (total_margin / total_sales) if total_sales else 0.0

        sheet.write('A4', 'Total Sales', kpi_label_format)
        sheet.write('B4', total_sales, kpi_value_format)
        sheet.write('A5', 'Total Cost', kpi_label_format)
        sheet.write('B5', total_cost, kpi_value_format)
        sheet.write('A6', 'Total Margin', kpi_label_format)
        sheet.write('B6', total_margin, kpi_value_format)
        sheet.write('A7', 'Margin %', kpi_label_format)
        sheet.write('B7', avg_margin_percent, kpi_percent_format)

        # Main Table Headers
        row_offset = 8
        headers = ['Product', 'Category', 'Qty', 'Unit Price', 'Unit Cost', 'Total Cost', 'Subtotal', 'Margin', 'Margin %']
        for col, header in enumerate(headers):
            sheet.write(row_offset, col, header, header_format)

        # Main Data Rows
        for i, line in enumerate(lines, start=row_offset + 1):
            sheet.write(i, 0, line['product'], text_format)
            sheet.write(i, 1, line['category'], text_format)
            sheet.write_number(i, 2, float(line['qty']), number_format)
            sheet.write_number(i, 3, float(line['unit_price']), number_format)
            sheet.write_number(i, 4, float(line['unit_cost']), number_format)
            sheet.write_number(i, 5, float(line['total_cost']), number_format)
            sheet.write_number(i, 6, float(line['subtotal']), number_format)
            sheet.write_number(i, 7, float(line['margin']), number_format)
            sheet.write_number(i, 8, float(line['margin_percent']) / 100.0, percent_format)

        # Footer row for totals
        footer_row = row_offset + 1 + len(lines)
        sheet.write(footer_row, 0, 'Total', bold_format)
        sheet.write_number(footer_row, 2, total_qty, number_format)
        sheet.write_number(footer_row, 5, total_cost, number_format)
        sheet.write_number(footer_row, 6, total_sales, number_format)
        sheet.write_number(footer_row, 7, total_margin, number_format)
        sheet.write_number(footer_row, 8, avg_margin_percent, percent_format)

        # Top 5 Most Profitable Products
        start_row = footer_row + 3
        sheet.write(start_row, 0, 'Top 5 Most Profitable Products', title_format)
        sheet.write_row(start_row + 1, 0, ['Product', 'Category', 'Margin'], header_format)
        for i, p in enumerate(top_products):
            sheet.write(start_row + 2 + i, 0, p['product'], text_format)
            sheet.write(start_row + 2 + i, 1, p['category'], text_format)
            sheet.write_number(start_row + 2 + i, 2, float(p['margin']), number_format)

        # Top 5 Least Profitable Products
        start_row += 8
        sheet.write(start_row, 0, 'Top 5 Least Profitable Products', title_format)
        sheet.write_row(start_row + 1, 0, ['Product', 'Category', 'Margin'], header_format)
        for i, p in enumerate(bottom_products):
            sheet.write(start_row + 2 + i, 0, p['product'], text_format)
            sheet.write(start_row + 2 + i, 1, p['category'], text_format)
            sheet.write_number(start_row + 2 + i, 2, float(p['margin']), number_format)

        # Category Summary
        start_row += 8
        sheet.write(start_row, 0, 'Category Summary', title_format)
        sheet.write_row(start_row + 1, 0, ['Category', 'Qty', 'Revenue', 'Cost', 'Margin', 'Margin %'], header_format)
        for i, cat in enumerate(category_summary):
            sheet.write(start_row + 2 + i, 0, cat['category'], text_format)
            sheet.write_number(start_row + 2 + i, 1, float(cat['qty']), number_format)
            sheet.write_number(start_row + 2 + i, 2, float(cat['revenue']), number_format)
            sheet.write_number(start_row + 2 + i, 3, float(cat['cost']), number_format)
            sheet.write_number(start_row + 2 + i, 4, float(cat['margin']), number_format)
            sheet.write_number(start_row + 2 + i, 5, float(cat['margin_percent']) / 100.0, percent_format)

        # Adjust column widths
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:I', 15)

        workbook.close()
        output.seek(0)

        return request.make_response(output.read(), [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename="sales_profitability_report.xlsx"'),
        ])
