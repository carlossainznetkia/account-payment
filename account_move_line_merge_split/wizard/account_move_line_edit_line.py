# Copyright 2024 NETKIA S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, _


class AccountMoveLineEditLine(models.Model):
    _name = "account_move_line_edit_line"
    
    config_id = fields.Many2one('account_move_line_edit', string=_('Config Ref.'), ondelete='cascade', required=True)

    name = fields.Char(_('Concept'))
    amount = fields.Float(_('Amount'))
    due_date = fields.Date(_('Due Date'))
    customer_id= fields.Many2one('res.partner', _('Customer'))
