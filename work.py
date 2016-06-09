# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, If


__all__ = ['Work']


class Work:
    __name__ = 'project.work'
    __metaclass__ = PoolMeta
    sale_lines = fields.One2Many('sale.line', 'task', 'Sale Lines',
        readonly=True)

    @property
    def sale_line_quantities(self):
        return sum([l.quantity for l in self.sale_lines \
            if l.type == 'line'], 0.0)

    @classmethod
    def __setup__(cls):
        super(Work, cls).__setup__()
        cls.quantity.states['readonly'] = Bool(Eval('sale_lines'))
        if 'sale_lines' not in cls.quantity.depends:
            cls.quantity.depends.append('sale_lines')

    def get_sale_line(self, parent):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        Uom = pool.get('product.uom')
        SaleLine = pool.get('sale.line')

        sale_line = SaleLine()
        type_ = 'line'
        if self.type == 'project':
            type_ = 'title'

        sale_line.type = type_
        sale_line.description = self.name
        sale_line.task = self
        sale_line.childs = []
        if type_ == 'project':
            return sale_line

        sale_line.quantity = 0
        if self.invoice_product_type == 'goods':
            sale_line.product = self.product_goods
            sale_line.on_change_product()
            sale_line.unit = self.uom
            sale_line.unit_price = self.unit_price
        if self.invoice_product_type == 'service':
            sale_line.product = self.product
            sale_line.on_change_product()
            sale_line.unit = Uom(ModelData.get_id('product', 'uom_hour'))
            sale_line.unit_price = self.unit_price

        return sale_line