"""Update all: renaming to the current path, signal-flow order, orphans.

These call _update_comps on the scratch COMPs only. Updateall itself walks
every COMP in the project, and that would rewrite the user's own patch.
"""


def scratch_comps(t):
    return sorted((c for c in [t.root] + list(t.root.findChildren())
                   if c.isCOMP and t.iface(c) is not None),
                  key=lambda c: -c.path.count('/'))


def update(t):
    t.promote._update_comps(scratch_comps(t))


def test_managed_comps_are_found_by_their_page(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    found = {c.path for c in t.promote._managed_comps()}
    for lvl in t.levels():
        assert lvl.path in found, lvl.path
    assert t.tool.path not in found


def test_managed_comps_skip_the_tool_itself(t):
    found = {c.path for c in t.promote._managed_comps()}
    assert not any(p.startswith(t.tool.path) for p in found)


def test_operator_rename_is_picked_up(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.xf.name = 'warp'
    t.eq(t.xf.par.rotate.bindExpr, 'parent().par.Xfrotate', 'bind survives')
    update(t)
    t.eq(t.names(t.c), ['Warprotate'])
    t.eq(t.names(t.root), ['Abcwarprotate'])
    t.eq(t.headers(t.c), ['warp'])
    t.eq(t.headers(t.root), ['a.b.c.warp'])
    t.chain_ok(t.xf.par.rotate, t.root.par.Abcwarprotate)
    t.no_errors()


def test_comp_rename_changes_every_level_above(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.c.name = 'cc'
    update(t)
    t.eq(t.names(op(t.b.path + '/cc')), ['Xfrotate'])
    t.eq(t.names(t.b), ['Ccxfrotate'])
    t.eq(t.names(t.root), ['Abccxfrotate'])
    t.chain_ok(t.xf.par.rotate, t.root.par.Abccxfrotate)
    t.no_errors()


def test_group_rename_keeps_member_binds(t):
    t.promote.Promote(t.xf.parGroup.t, t.root)
    t.xf.name = 'warp'
    update(t)
    t.eq(t.names(t.root), ['Abcwarptx', 'Abcwarpty'])
    t.xf.par.tx = 0.6
    t.near(t.root.par.Abcwarptx.eval(), 0.6)
    t.no_errors()


def test_rename_rewrites_expressions_that_read_the_par(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    reader = t.root.create(transformTOP, 'reader')
    reader.par.rotate.expr = 'parent().par.Abcxfrotate * 2'
    t.xf.name = 'warp'
    update(t)
    t.eq(reader.par.rotate.expr, 'parent().par.Abcwarprotate * 2')


def test_nothing_to_rename_changes_nothing(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    before = t.snapshot()
    update(t)
    t.eq(t.snapshot(), before)


def test_rename_collision_writes_nothing(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.c.appendCustomPage('Extra').appendFloat('Warprotate')
    t.xf.name = 'warp'
    before = t.snapshot()
    update(t)
    t.eq(t.snapshot(), before, 'state after a refused update')
    assert 'REFUSED' in ui.status, ui.status


def test_rename_undo_restores_names_and_binds(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.xf.name = 'warp'
    before = t.snapshot()
    update(t)
    t.eq(t.names(t.root), ['Abcwarprotate'])
    ui.undo.undo()
    t.eq(t.snapshot(), before, 'after undo')
    t.no_errors()
    ui.undo.redo()
    t.eq(t.names(t.root), ['Abcwarprotate'], 'after redo')
    t.no_errors()
    ui.undo.undo()


def test_order_follows_the_wires(t):
    late = t.c.create(transformTOP, 'late')
    t.xf.outputConnectors[0].connect(late)
    t.promote.Promote(late.par.rotate, t.root)
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.eq(t.names(t.c), ['Xfrotate', 'Laterotate'])
    t.eq(t.headers(t.c), ['xf', 'late'])
    t.eq(t.names(t.root), ['Abcxfrotate', 'Abclaterotate'])


def test_order_changes_when_the_wiring_does(t):
    late = t.c.create(transformTOP, 'late')
    t.xf.outputConnectors[0].connect(late)
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.promote.Promote(late.par.rotate, t.root)
    t.eq(t.names(t.c), ['Xfrotate', 'Laterotate'])
    late.inputConnectors[0].disconnect()
    t.xf.inputConnectors[0].disconnect()
    late.outputConnectors[0].connect(t.xf)
    update(t)
    t.eq(t.names(t.c), ['Laterotate', 'Xfrotate'])
    t.eq(t.names(t.root), ['Abclaterotate', 'Abcxfrotate'])
    t.chain_ok(t.xf.par.rotate, t.root.par.Abcxfrotate)


def test_orphan_stays_at_the_end(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    keep = t.c.create(transformTOP, 'keep')
    t.promote.Promote(keep.par.rotate, t.root)
    keep.destroy()
    update(t)
    t.eq(t.names(t.c)[0], 'Xfrotate')
    assert 'Keeprotate' in t.names(t.c), t.names(t.c)
    t.eq(t.names(t.c)[-1], 'Keeprotate')


def test_header_without_children_is_removed(t):
    t.promote.Promote(t.xf.par.rotate, t.c)
    keep = t.c.create(transformTOP, 'keep')
    t.xf.outputConnectors[0].connect(keep)
    t.promote.Promote(keep.par.rotate, t.c)
    t.eq(t.headers(t.c), ['xf', 'keep'])
    keep.par.rotate.mode = ParMode.CONSTANT
    keep.par.rotate.bindExpr = ''
    t.c.parGroup.Keeprotate.destroy()
    update(t)
    t.eq(t.headers(t.c), ['xf'])
    t.eq(t.names(t.c), ['Xfrotate'])
