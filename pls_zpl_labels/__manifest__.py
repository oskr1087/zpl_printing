{
    "name": "PLS Etiquetas ZPL",
    "version": "19.0.1.7.2",
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
        "security/ir.model.access.csv",
        "views/stock_location_views.xml",
        "views/stock_move_line_views.xml",
        "views/stock_picking_views.xml",
                "wizards/zpl_label_preview_wizard_views.xml",
        "report/zpl_report_actions.xml",
        "report/zpl_report_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pls_zpl_labels/static/src/scss/pls_zpl_labels.scss",
        ],
    },
    "installable": True,
    "application": False,
}
