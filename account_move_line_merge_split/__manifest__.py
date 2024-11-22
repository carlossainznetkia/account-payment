{
    "name": "Split and Merge Move Lines",
    "summary": "Adds options to split and merge move lines",
    "category": "Account",
    "version": "16.0.1.0.0",
    "author": "Netkia, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-payment",
    "license": "AGPL-3",
    "depends": [
        "base",
        "account",
        "account_due_list",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/aml_split.xml",
        "wizard/aml_merge.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "development_status": "Production/Stable",
    "maintainers": ["CarlosSainzNetkia"],
}
