"""Unpromote: what goes, what stays, and what is refused."""

ROTATE = ['Xfrotate', 'Cxfrotate', 'Bcxfrotate', 'Abcxfrotate']


def test_removes_every_master_and_keeps_the_value(t):
    t.xf.par.rotate = 40
    t.promote.Promote(t.xf.par.rotate, t.root)
    removed = t.promote.Unpromote(t.xf.par.rotate)
    t.eq(len(removed), 4, 'removed levels')
    for lvl in t.levels():
        t.eq(t.iface(lvl), None, lvl.path + ' page')
    t.eq(t.xf.par.rotate.mode, ParMode.CONSTANT)
    t.near(t.xf.par.rotate.eval(), 40, 'built-in keeps its value')
    t.no_errors()


def test_drag_from_the_top_master(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.root.par[ROTATE[-1]] = 77
    t.promote.Unpromote(t.root.par[ROTATE[-1]])
    t.eq(t.iface(t.root), None, 'dragged level is gone')
    below = t.a.par[ROTATE[2]]
    t.eq(below.mode, ParMode.CONSTANT, 'direct slave becomes constant')
    t.near(below.eval(), 77, 'value survives')
    t.eq(t.xf.par.rotate.mode, ParMode.BIND, 'lower links stay')
    t.chain_ok(t.xf.par.rotate, below)
    t.no_errors()


def test_middle_master_cuts_above_and_frees_the_slave(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.promote.Unpromote(t.b.par[ROTATE[1]])
    t.eq(t.iface(t.b), None, 'dragged level')
    t.eq(t.iface(t.a), None, 'above')
    t.eq(t.iface(t.root), None, 'top')
    t.eq(t.c.par[ROTATE[0]].mode, ParMode.CONSTANT, 'slave becomes constant')
    t.eq(t.xf.par.rotate.mode, ParMode.BIND, 'lower link stays')
    t.chain_ok(t.xf.par.rotate, t.c.par[ROTATE[0]])
    t.no_errors()


def test_one_axis_of_a_group_leaves_the_other(t):
    t.promote.Promote(t.xf.parGroup.t, t.root)
    t.xf.par.ty = 0.3
    t.promote.Unpromote(t.xf.par.tx)
    for lvl, base in zip(t.levels(), ['Xft', 'Cxft', 'Bcxft', 'Abcxft']):
        t.eq(t.names(lvl), [base + 'y'], lvl.path)
    t.eq(t.xf.par.tx.mode, ParMode.CONSTANT, 'x is free')
    t.chain_ok(t.xf.par.ty, t.root.par.Abcxfty)
    t.no_errors()


def test_axis_left_from_a_numbered_group_keeps_its_label(t):
    # An Int group has no letter suffixes, so its masters are numbered.
    rect = t.c.create(rectangleTOP, 'rect')
    t.promote.Promote(rect.parGroup.resolution, t.root)
    t.eq(t.names(t.root), ['Abcrectresolution1', 'Abcrectresolution2'])
    t.promote.Unpromote(rect.par.resolutionh)
    for lvl, name in zip(t.levels(), ['Rectresolution1', 'Crectresolution1',
                                      'Bcrectresolution1',
                                      'Abcrectresolution1']):
        t.eq(t.names(lvl), [name], lvl.path)
        t.eq(lvl.par[name].label, 'Resolution W', lvl.path)
    t.no_errors()


def test_group_drag_removes_every_axis(t):
    t.promote.Promote(t.xf.parGroup.t, t.root)
    t.promote.Unpromote(t.xf.parGroup.t)
    for lvl in t.levels():
        t.eq(t.iface(lvl), None, lvl.path)
    t.eq((t.xf.par.tx.mode, t.xf.par.ty.mode),
         (ParMode.CONSTANT, ParMode.CONSTANT))


def test_group_drag_catches_axes_promoted_apart(t):
    t.promote.Promote(t.xf.par.tx, t.root)
    t.promote.Promote(t.xf.par.ty, t.root)
    t.promote.Unpromote(t.xf.parGroup.t)
    for lvl in t.levels():
        t.eq(t.iface(lvl), None, lvl.path)


def test_keeps_other_chains_on_the_page(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.promote.Promote(t.xf.par.tx, t.root)
    t.promote.Unpromote(t.xf.par.rotate)
    for lvl, name in zip(t.levels(),
                         ['Xftx', 'Cxftx', 'Bcxftx', 'Abcxftx']):
        t.eq(t.names(lvl), [name], lvl.path)
    t.chain_ok(t.xf.par.tx, t.root.par.Abcxftx)


def test_custom_par_without_a_chain_is_deleted(t):
    page = t.b.appendCustomPage(t.page)
    page.appendFloat('Mine')
    page.appendFloat('Other')
    removed = t.promote.Unpromote(t.b.par.Mine)
    t.eq(removed, ['Mine'])
    t.eq(t.names(t.b), ['Other'])


def test_builtin_outside_a_chain_is_left_alone(t):
    before = t.snapshot()
    t.eq(t.promote.Unpromote(t.xf.par.rotate), None)
    t.eq(t.snapshot(), before)


def test_refuses_when_a_master_has_another_bind(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.a.create(transformTOP, 'extra')
    extra = t.a.op('extra')
    extra.par.rotate.bindExpr = 'parent().par.' + ROTATE[2]
    extra.par.rotate.mode = ParMode.BIND
    t.raises(t.promote.Unpromote, t.xf.par.rotate)


def test_one_undo_step_is_enough(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    before = t.snapshot()
    t.promote.Unpromote(t.xf.par.rotate)
    ui.undo.undo()
    t.eq(t.snapshot(), before, 'after one undo')
    ui.undo.redo()
    t.eq(t.iface(t.root), None, 'after redo')
    ui.undo.undo()
    t.no_errors()
