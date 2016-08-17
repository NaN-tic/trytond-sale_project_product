==========================================
Project Product Timesheet Service Scenario
==========================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_chart, \
    ...     get_accounts
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     create_payment_term
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install sale_project_product::

    >>> Module = Model.get('ir.module')
    >>> module, = Module.find([
    ...         ('name', '=', 'sale_project_product'),
    ...     ])
    >>> module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create sale user::

    >>> sale_user = User()
    >>> sale_user.name = 'Sale'
    >>> sale_user.login = 'sale'
    >>> sale_user.main_company = company
    >>> sale_group, = Group.find([('name', '=', 'Sales')])
    >>> project_group, = Group.find([('name', '=', 'Project Administration')])
    >>> sale_user.groups.extend([sale_group, project_group])
    >>> sale_user.save()

Create project user::

    >>> project_user = User()
    >>> project_user.name = 'Project'
    >>> project_user.login = 'project'
    >>> project_user.main_company = company
    >>> project_group, = Group.find([('name', '=', 'Project Administration')])
    >>> sale_group, = Group.find([('name', '=', 'Sales')])
    >>> project_user.groups.extend([project_group, sale_group])
    >>> project_user.save()

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create customer::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> hour, = ProductUom.find([('name', '=', 'Hour')])

    >>> Product = Model.get('product.product')
    >>> ProductTemplate = Model.get('product.template')

    >>> product1 = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'Product 1'
    >>> template.default_uom = hour
    >>> template.type = 'service'
    >>> template.list_price = Decimal('20')
    >>> template.cost_price = Decimal('5')
    >>> template.account_revenue = revenue
    >>> template.salable = True
    >>> template.save()
    >>> product1.template = template
    >>> product1.save()

    >>> product2 = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'Product 2'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('100')
    >>> template.cost_price = Decimal('50')
    >>> template.account_revenue = revenue
    >>> template.salable = True
    >>> template.save()
    >>> product2.template = template
    >>> product2.save()

    >>> product3 = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'Product 3'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('50')
    >>> template.cost_price = Decimal('20')
    >>> template.account_revenue = revenue
    >>> template.salable = True
    >>> template.save()
    >>> product3.template = template
    >>> product3.save()

Create sale::

    >>> config.user = sale_user.id
    >>> Sale = Model.get('sale.sale')
    >>> SaleLine = Model.get('sale.line')
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'manual'
    >>> sale.shipment_method = 'manual'
    >>> sale.create_project = True
    >>> sale_line = SaleLine()
    >>> sale.lines.append(sale_line)
    >>> sale_line.product = product1
    >>> sale_line.quantity = 10.0
    >>> sale_line = SaleLine()
    >>> sale.lines.append(sale_line)
    >>> sale_line.product = product2
    >>> sale_line.quantity = 20.0
    >>> sale.click('quote')
    >>> sale.click('confirm')
    >>> sale.click('process')
    >>> sale.reload()
    >>> sale.work != None
    True

Check Project::

    >>> config.user = project_user.id
    >>> ProjectWork = Model.get('project.work')
    >>> project, = ProjectWork().find([('type', '=', 'project')])
    >>> sale.work.id == project.id
    True
    >>> project.type
    u'project'
    >>> project.party == customer
    True
    >>> task1, task2 = project.children
    >>> task1.product_goods
    >>> task1.product_goods == product1
    True
    >>> task1.quantity
    10.0
    >>> task2.product_goods == product2
    True
    >>> task2.quantity
    20.0

Create new sale::

    >>> config.user = sale_user.id
    >>> Sale = Model.get('sale.sale')
    >>> SaleLine = Model.get('sale.line')
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'manual'
    >>> sale.shipment_method = 'manual'
    >>> sale.project = project

Load project::

    >>> config.user = project_user.id
    >>> sale.click('load_project')
    >>> sale_line1, sale_line2 = sale.lines
    >>> sale_line1.product == product1
    True
    >>> sale_line1.quantity
    0.0
    >>> sale_line2.product == product2
    True
    >>> sale_line2.quantity
    0.0

Modify sale lines and add new one::

    >>> config.user = sale_user.id
    >>> sale_line1.quantity = -5.0
    >>> sale_line2.quantity = 20.0
    >>> sale_line = SaleLine()
    >>> sale.lines.append(sale_line)
    >>> sale_line.product = product3
    >>> sale_line.quantity = 100.0
    >>> sale.click('quote')
    >>> sale.click('confirm')

Check Project::

    >>> config.user = project_user.id
    >>> project.reload()
    >>> task1, task2, task3 = project.children
    >>> task1.quantity
    5.0
    >>> task2.quantity
    40.0
    >>> task3.product_goods == product3
    True
    >>> task3.quantity
    100.0