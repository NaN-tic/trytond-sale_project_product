# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import sale
from . import work


def register():
    Pool.register(
        sale.Sale,
        sale.SaleLine,
        work.Work,
        module='sale_project_product', type_='model')
