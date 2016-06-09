# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Equal, Not, Or


__all__ = ['Sale', 'SaleLine', 'Work']


class Work:
    __metaclass__ = PoolMeta
    __name__ = 'project.work'

    sale_lines = fields.One2Many('sale.line', 'task', 'Sale Lines')


class Sale:
    __metaclass__ = PoolMeta
    __name__ = 'sale.sale'
    work = fields.Many2One('project.work', 'Project',
        states={
            'readonly': Or(Not(Equal(Eval('invoice_method'), 'manual')),
                Not(Equal(Eval('shipment_method'), 'manual'))),
            },
        domain=[
            ('type', '=', 'project'),
            ('company', '=', Eval('company', -1)),
            ('party', '=', Eval('party', -1)),
            ],
        depends=['company', 'party', 'invoice_method', 'shipment_method'])
    create_project = fields.Boolean('Create Project',
        states={
            'readonly': Or(Or(Not(Equal(Eval('invoice_method'), 'manual')),
                Not(Equal(Eval('shipment_method'), 'manual'))),
                Bool(Eval('work'))),
            },
        depends=['work', 'invoice_method', 'shipment_method'])

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls._error_messages.update({
                'check_project_error': ('Invalid combination of shipment and '
                    'invoicing methods on sale "%s" for process Projects.\n'
                    'You must set both to "manual"'),
                'check_sale_back_error': 'You can not set the state of the '
                    'sale "%s" to Draft when it has not been processed with '
                    'both methods (shipment & invoicing) set to "manual".'
                })
        cls._transitions |= set((
                ('done', 'draft'),
                ))
        cls._buttons.update({
                'load_project': {
                    'invisible': ~Eval('state').in_(['draft', 'quotation']),
                    },
                })


    @fields.depends('create_project', 'work', 'invoice_method',
        'shipment_method')
    def on_change_with_create_project(self):
        if (self.work or self.invoice_method != 'manual' or
                self.invoice_method != 'manual'):
            return False
        return self.create_project

    @classmethod
    def check_project(cls, sales):
        for sale in sales:
            if sale.work or sale.create_project:
                if (sale.invoice_method != 'manual' or
                        sale.shipment_method != 'manual'):
                    cls.raise_user_error('check_project_error',
                        (sale.rec_name,))

    @classmethod
    def update_project(cls, sales):
        Line = Pool().get('sale.line')
        for sale in sales:
            if sale.work:
                Line.update_tasks(sale.lines)

    @classmethod
    def quote(cls, sales):
        super(Sale, cls).quote(sales)
        cls.check_project(sales)

    @classmethod
    def confirm(cls, sales):
        super(Sale, cls).confirm(sales)
        cls.check_project(sales)

    @classmethod
    def process(cls, sales):
        super(Sale, cls).process(sales)
        cls.create_projects(sales)

    def _get_project(self):
        project = self.work
        if not project:
            Work = Pool().get('project.work')
            project = Work()
            project.name = self.rec_name
            project.type = 'project'
            project.company = self.company
            project.project_invoice_method = 'progress'
            project.invoice_product_type = 'service'
            project.party = self.party
            project.party_address = self.invoice_address
        project.readonly = True
        return project

    @classmethod
    def create_projects(cls, sales):
        for sale in sales:
            if sale.work is None and not sale.create_project:
                continue
            project = sale._get_project()
            sale.create_project_from_sales(project)
            sale.work = project
        cls.save(sales)

    @fields.depends('task_parent')
    def create_project_from_sales(self, parent_project, parent_line=None):
        lines = [x for x in self.lines if parent_line == x.parent]
        for line in lines:
            print "qty:", line.quantity
            if line.quantity == 0.00:
                continue
            if line.task:
                task = line.task
            else:
                task = line._get_task()
                task.sale_lines = []
                task.sale_lines += (line,)
                if parent_project:
                    task.parent = parent_project

            task.quantity = task.sale_line_quantities
            task.save()
            if line.childs:
                self.create_project_from_sales(task, line)

    @classmethod
    def load_project(cls, sales):
        for sale in sales:
            if not sale.work:
                return
            sale.create_lines_from_project(sale.work.children)
        cls.save(sales)

    def create_lines_from_project(self, project, parent_line=None):
        for task in project:
            sale_line = task.get_sale_line(parent_line)
            if parent_line:
                sale_line.parent = parent_line
            self.lines += (sale_line,)
            if task.children:
                self.create_lines_from_project(task.children, sale_line)


class SaleLine:
    __metaclass__ = PoolMeta
    __name__ = 'sale.line'
    task = fields.Many2One('project.work', 'Task')

    def _get_task(self):
        task = self.task
        if task:
            return task

        Work = Pool().get('project.work')
        task = Work()
        task.quantity = self.quantity
        task.type = 'task'
        if self.type == 'title':
            task.type = 'project'

        task.name = self.rec_name
        task.company = self.sale.company
        task.project_invoice_method = 'progress'
        if self.type == 'title' or self.product and \
                self.product.type == 'service':
            task.invoice_product_type = 'service'
        else:
            task.invoice_product_type = 'goods'
            task.product_goods = self.product
            task.on_change_product_goods()
            task.unit_price = self.unit_price
        return task
