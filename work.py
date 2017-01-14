# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Work']


class Work:
    __name__ = 'project.work'
    __metaclass__ = PoolMeta
    sale_lines = fields.One2Many('sale.line', 'task', 'Sale Lines',
        readonly=True)

    @classmethod
    def copy(cls, works, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['sale_lines'] = None
        return super(Work, cls).copy(works, default=default)
