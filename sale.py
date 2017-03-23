# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool
from datetime import date

__all__ = ['Sale', 'SaleLine']


class SaleLine:
    __name__ = 'sale.line'
    __metaclass__ = PoolMeta

    project = fields.Many2One('project.work', 'Project', readonly=True,
        select=True)


class Sale:
    __name__ = 'sale.sale'
    __metaclass__ = PoolMeta

    parent_project = fields.Many2One('project.work', 'Parent Project',
        select=True,
        domain=[('party', '=', Eval('party'))],
        states={
            'readonly': Eval('state') != 'draft',
            },
        depends=['state', 'party'])

    @classmethod
    def process(cls, sales):
        super(Sale, cls).process(sales)
        cls.create_projects(sales)

    @classmethod
    def create_projects(cls, sales):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        for sale in sales:
            if not sale.parent_project:
                continue
            project = sale._get_project()
            project.save()
            SaleLine.write([x for x in sale.lines if x.type == 'line'],
                {'project': project.id})

    def _get_project(self):

        project = None
        line = self.lines and self.lines[0]
        if line.project:
            return project
        Work = Pool().get('project.work')
        project = Work()
        project.name = self.rec_name
        project.type = 'project'
        project.product_goods = self.parent_project.product_goods
        project.uom = self.parent_project.uom
        project.company = self.company
        project.project_invoice_method = \
            self.parent_project.project_invoice_method
        project.invoice_product_type = self.parent_project.invoice_product_type
        project.parent = self.parent_project
        project.party = self.party
        project.party_address = self.invoice_address
        project.progress_quantity = 0
        project.quantity = 1
        project.start_date = date.today()
        project.list_price = self.untaxed_amount
        return project
