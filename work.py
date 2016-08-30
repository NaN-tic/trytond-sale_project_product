# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import fields
from trytond.modules.project_product import get_service_goods_aux
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval

__all__ = ['Work']


class Work:
    __name__ = 'project.work'
    __metaclass__ = PoolMeta
    sale_lines = fields.One2Many('sale.line', 'task', 'Sale Lines',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super(Work, cls).__setup__()
        cls.quantity.states['readonly'] = Bool(Eval('sale_lines'))
        if 'sale_lines' not in cls.quantity.depends:
            cls.quantity.depends.append('sale_lines')
        cls._error_messages.update({
                'not_salable_product': (
                    'You cannot load the project "%(project)s" in sale '
                    '"%(sale)s" because the product "%(product)s" of task '
                    '"%(task)s" is not salable.'),
                })

    @property
    def sale_line_quantities(self):
        return sum([l.quantity for l in self.sale_lines
            if l.type == 'line'], 0.0)

    def get_sale_line(self, sale):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        Uom = pool.get('product.uom')
        SaleLine = pool.get('sale.line')

        sale_line = SaleLine()
        type_ = 'line'
        if self.type == 'project':
            type_ = 'title'

        sale_line.sale = sale
        sale_line.type = type_
        sale_line.description = self.name
        sale_line.task = self
        sale_line.childs = []

        if type_ == 'title':
            return sale_line

        sale_line.quantity = 0
        if self.invoice_product_type == 'goods':
            if not self.product_goods.salable:
                self.raise_user_error('not_salable_product', {
                        'project': sale.work.rec_name,
                        'sale': sale.rec_name,
                        'product': self.product_goods.rec_name,
                        'task': self.rec_name,
                        })
            sale_line.product = self.product_goods
            sale_line.on_change_product()
            sale_line.unit = self.uom
            sale_line.unit_price = self.list_price
        if self.invoice_product_type == 'service':
            if not self.product.salable:
                self.raise_user_error('not_salable_product', {
                        'project': sale.work.rec_name,
                        'sale': sale.rec_name,
                        'product': self.product.rec_name,
                        'task': self.rec_name,
                        })
            sale_line.product = self.product
            sale_line.on_change_product()
            sale_line.unit = Uom(ModelData.get_id('product', 'uom_hour'))
            sale_line.unit_price = self.list_price

        return sale_line

    @classmethod
    def _get_cost(cls, works):

        works_s = [x for x in works if x.sale_lines]
        works_c = [x for x in works if not x.sale_lines]

        costs = super(Work, cls)._get_cost(works_c)
        costs.update(get_service_goods_aux(
            works_s,
            super(Work, cls)._get_cost,
            lambda work: (Decimal(str(work.quantity)) *
                Decimal(str(work.sale_lines[0].cost_price or 0.0)))))
        return costs

    @classmethod
    def copy(cls, works, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['sale_lines'] = None
        return super(Work, cls).copy(works, default=default)
