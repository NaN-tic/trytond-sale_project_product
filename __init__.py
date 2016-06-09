# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .sale import *
from .work import *


def register():
    Pool.register(
        Sale,
        SaleLine,
        Work,
        module='sale_project_product', type_='model')
