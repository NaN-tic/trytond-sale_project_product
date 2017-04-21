# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Work']


class Work:
    __name__ = 'project.work'
    __metaclass__ = PoolMeta
    sales = fields.Function(fields.One2Many('sale.sale', None,
        'Sales'), 'get_sales', searcher='search_sales')
    sale_lines = fields.One2Many('sale.line', 'project', 'Sale Lines',
        readonly=True)

    def get_sales(self, name):
        sales = set()
        for line in self.sale_lines:
            if line.sale:
                sales.add(line.sale.id)
        return list(sales)

    @classmethod
    def search_sales(cls, name, clause):
        return [('sale_lines.sale',) + tuple(clause[1:])]

    @classmethod
    def copy(cls, works, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['sale_lines'] = None
        return super(Work, cls).copy(works, default=default)
