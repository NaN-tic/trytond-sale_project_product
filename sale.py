# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval


class Sale:
    __metaclass__ = PoolMeta
    __name__ = 'sale.sale'
    work = fields.Many2One('project.work', 'Project', domain=[
            ('type', '=', 'project'),
            ('company', '=', Eval('company', -1)),
            ('party', '=', Eval('party', -1)),
            ],
        states={
            'readonly': ((Eval('invoice_method') != 'manual')
                | (Eval('shipment_method') != 'manual')
                | Bool(Eval('create_project'))
                | ~Eval('state').in_(['draft', 'quotation'])),
            },
        depends=['company', 'party', 'invoice_method', 'shipment_method',
            'create_project', 'state'])
    create_project = fields.Boolean('Create Project',
        states={
            'readonly': ((Eval('invoice_method') != 'manual')
                | (Eval('shipment_method') != 'manual')
                | Bool(Eval('work'))
                | ~Eval('state').in_(['draft', 'quotation'])),
            },
        depends=['invoice_method', 'shipment_method', 'work', 'state'])

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
                    'invisible': Eval('state') != 'draft',
                    'readonly': ~Bool(Eval('work')) | Bool(Eval('lines_tree'))
                    },
                })

    @fields.depends('work', 'invoice_method', 'shipment_method')
    def on_change_with_work(self):
        if self.invoice_method != 'manual' or self.invoice_method != 'manual':
            return None
        return self.work.id if self.work else None

    @fields.depends('work')
    def on_change_work(self):
        if self.work:
            self.create_project = False

    @fields.depends('create_project', 'invoice_method', 'shipment_method')
    def on_change_with_create_project(self):
        if self.invoice_method != 'manual' or self.invoice_method != 'manual':
            return False
        return self.create_project

    @fields.depends('create_project')
    def on_change_create_project(self):
        if self.create_project:
            self.work = None

    @classmethod
    def quote(cls, sales):
        super(Sale, cls).quote(sales)
        cls.check_project(sales)

    @classmethod
    def confirm(cls, sales):
        super(Sale, cls).confirm(sales)
        cls.check_project(sales)

    @classmethod
    def check_project(cls, sales):
        for sale in sales:
            if sale.work or sale.create_project:
                if (sale.invoice_method != 'manual' or
                        sale.shipment_method != 'manual'):
                    cls.raise_user_error('check_project_error',
                        (sale.rec_name,))

    @classmethod
    def process(cls, sales):
        super(Sale, cls).process(sales)
        cls.create_projects(sales)

    @classmethod
    def create_projects(cls, sales):
        for sale in sales:
            if not sale.create_project or sale.work != None:
                continue
            project = sale._get_project()
            sale.create_project_from_sales(project)
            sale.work = project
        cls.save(sales)

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
            project.progress_quantity = 0.0
            project.quantity = 0.0
        project.readonly = True
        return project

    def create_project_from_sales(self, parent_project, parent_line=None):
        lines = [x for x in self.lines if parent_line == x.parent]
        for line in lines:
            if line.type != 'line':
                continue
            if line.type == 'line' and line.quantity == 0.00:
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
    @ModelView.button
    def load_project(cls, sales):
        for sale in sales:
            if not sale.work:
                return
            sale.create_lines_from_project(sale.work.children)
        cls.save(sales)

    def create_lines_from_project(self, project, parent_line=None):
        for task in project:
            sale_line = task.get_sale_line(self)
            if parent_line:
                sale_line.parent = parent_line
            sale_line.save()
            if task.children:
                self.create_lines_from_project(task.children, sale_line)

    @classmethod
    def copy(cls, sales, default=None):
        # sales that already created their project
        sales_no_create_project = [s for s in sales
            if s.create_project and s.work]
        if sales_no_create_project:
            if default is None:
                default_no_create_project = {}
            else:
                default_no_create_project = default.copy()
            new_sales = [s for s in sales if s not in sales_no_create_project]
            res = super(Sale, cls).copy(new_sales, default=default)
            res.extend(super(Sale, cls).copy(sales_no_create_project,
                default=default_no_create_project))
            return res
        return super(Sale, cls).copy(sales, default=default)


class SaleLine:
    __metaclass__ = PoolMeta
    __name__ = 'sale.line'
    task = fields.Many2One('project.work', 'Task', readonly=True)

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()
        if hasattr(SaleLine, '_allow_modify_after_draft'):
            cls._allow_modify_after_draft |= set(['task'])

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
            task.quantity = 0.0

        task.name = self.rec_name
        task.company = self.sale.company
        task.project_invoice_method = 'progress'
        task.progress_quantity = 0.0
        if self.type == 'title' or self.product and \
                self.product.type == 'service':
            task.invoice_product_type = 'service'
        else:
            task.invoice_product_type = 'goods'
            task.product_goods = self.product
            task.on_change_product_goods()
            task.list_price = self.unit_price

        return task

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['task'] = None
        return super(SaleLine, cls).copy(lines, default=default)
