"""Undo and redo of Promote leave no half-built chain behind."""

ROTATE = ['Xfrotate', 'Cxfrotate', 'Bcxfrotate', 'Abcxfrotate']


def test_promote_undo_redo(t):
    before = t.snapshot()
    t.promote.Promote(t.xf.par.rotate, t.root)
    after = t.snapshot()
    ui.undo.undo()
    t.eq(t.snapshot(), before, 'after undo')
    for lvl in t.levels():
        t.eq(t.iface(lvl), None, lvl.path)
    ui.undo.redo()
    t.eq(t.snapshot(), after, 'after redo')
    t.chain_ok(t.xf.par.rotate, t.root.par[ROTATE[-1]])
    t.no_errors()


def test_group_promote_undo(t):
    before = t.snapshot()
    t.promote.Promote(t.xf.parGroup.t, t.root)
    ui.undo.undo()
    t.eq(t.snapshot(), before)
    t.no_errors()


def test_refused_promote_leaves_the_undo_stack_alone(t):
    t.promote.Promote(t.xf.par.rotate, t.b)
    side = t.root.create(baseCOMP, 'side')
    t.raises(t.promote.Promote, t.xf.par.tx, side)
    ui.undo.undo()                     # must undo the first Promote
    for lvl in t.levels():
        t.eq(t.iface(lvl), None, lvl.path)


def test_reshaping_promote_is_one_undo_step(t):
    t.promote.Promote(t.xf.par.tx, t.root)
    t.promote.Promote(t.xf.par.ty, t.root)
    before = t.snapshot()
    t.promote.Promote(t.xf.parGroup.t, t.root)
    ui.undo.undo()
    t.eq(t.snapshot(), before, 'axes promoted apart come back')
    t.no_errors()
