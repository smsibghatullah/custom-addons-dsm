{
    "name": "Customer Statement View",
    "version": "1.0",
    "category": "Accounting",
    "summary": "Custom customer statement linked to partner",
    "author": "Muhammad Mubeen",
    "depends": ["base", "account","sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/customer_statement_view.xml",
        "views/report_customer_statement.xml"
    ],
    "installable": True,
    "application": False,
}
