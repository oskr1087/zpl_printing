{
    "name": "PLS Etiquetas ZPL",
    "version": "19.0.1.1.0",
    "summary": "Etiquetas ZPL de bulto parcial, ubicaciones y trazabilidad",
    "category": "Inventory/Inventory",
    "author": "Oscar Morocho",
    "website": "https://gatewayresources.com",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "sale_stock",
        "qz_tray_base",
        "qz_tray_report",
    ],
    "data": [
        "views/stock_location_views.xml",
        "views/stock_move_line_views.xml",
        "views/stock_quant_package_views.xml",
        "report/zpl_report_actions.xml",
        "report/zpl_report_templates.xml",
    ],
    "installable": True,
    "application": False,
}
