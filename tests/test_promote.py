"""Promote: names, binds, values, headers, refusals."""

ROTATE = ['Xfrotate', 'Cxfrotate', 'Bcxfrotate', 'Abcxfrotate']


def test_naming(t):
    m = t.mod
    t.eq(m.par_name('xf', 'rotate'), 'Xfrotate')
    t.eq(m.par_name('Trans-form1', 'Rot_ate'), 'Transform1rotate')
    t.eq(m.par_name('1a'), 'P1a')
    t.eq(m.header_name('c.xf'), 'Hdrcxf')
    t.eq(m.rel_parts(t.root, t.xf), ['a', 'b', 'c', 'xf'])
    t.eq(m.rel_parts(t.c, t.xf), ['xf'])
    t.raises(m.par_name, '___')


def test_single_par_to_top(t):
    names = t.promote.Promote(t.xf.par.rotate, t.root)
    t.eq(names, ROTATE, 'returned names')
    for lvl, name in zip(t.levels(), ROTATE):
        t.eq(t.names(lvl), [name], lvl.path)
    t.no_errors()


def test_binds_point_one_level_down(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    below = t.xf.par.rotate
    for lvl, name in zip(t.levels(), ROTATE):
        master = lvl.par[name]
        t.eq(below.mode, ParMode.BIND, below.owner.path)
        t.eq(below.bindExpr, 'parent().par.' + name, 'bind expression')
        assert below.bindMaster.isSamePar(master), 'bindMaster'
        below = master
    t.eq(t.root.par[ROTATE[-1]].mode, ParMode.CONSTANT, 'top is the master')


def test_value_flows_both_ways(t):
    t.xf.par.rotate = 33
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.near(t.root.par[ROTATE[-1]].eval(), 33, 'promoted value')
    t.root.par[ROTATE[-1]] = 90
    t.near(t.xf.par.rotate.eval(), 90, 'top -> source')
    t.xf.par.rotate = 12
    t.near(t.root.par[ROTATE[-1]].eval(), 12, 'source -> top')
    t.near(t.b.par[ROTATE[1]].eval(), 12, 'middle level')


def test_stops_at_destination(t):
    t.promote.Promote(t.xf.par.rotate, t.b)
    t.eq(t.names(t.c), ['Xfrotate'])
    t.eq(t.names(t.b), ['Cxfrotate'])
    t.eq(t.names(t.a), [])
    t.eq(t.names(t.root), [])


def test_headers(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    for lvl, label in zip(t.levels(), ['xf', 'c.xf', 'b.c.xf', 'a.b.c.xf']):
        t.eq(t.headers(lvl), [label], lvl.path)
        head = t.iface(lvl).parGroups[0][0]
        t.eq(head.startSection, False, 'first par of the page')


def test_second_header_starts_section(t):
    other = t.c.create(transformTOP, 'other')
    t.xf.outputConnectors[0].connect(other)
    t.promote.Promote(t.xf.par.rotate, t.c)
    t.promote.Promote(other.par.rotate, t.c)
    heads = [pg[0] for pg in t.iface(t.c).parGroups if pg[0].style == 'Header']
    t.eq([h.label for h in heads], ['xf', 'other'])
    t.eq([h.startSection for h in heads], [False, True])


def test_promote_is_idempotent(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    before = t.snapshot()
    names = t.promote.Promote(t.xf.par.rotate, t.root)
    t.eq(names, ROTATE)
    t.eq(t.snapshot(), before, 'state after a repeat')


def test_extend_chain_upward(t):
    t.promote.Promote(t.xf.par.rotate, t.b)
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.eq([t.names(l) for l in t.levels()], [[n] for n in ROTATE])
    t.chain_ok(t.xf.par.rotate, t.root.par[ROTATE[-1]])


def test_drag_of_promoted_par_follows_to_source(t):
    t.promote.Promote(t.xf.par.rotate, t.b)
    before = t.snapshot()
    t.promote.Promote(t.c.par[ROTATE[0]], t.b)
    t.eq(t.snapshot(), before, 'dragging the promoted copy')
    t.promote.Promote(t.c.par[ROTATE[0]], t.root)
    t.eq(t.names(t.root), [ROTATE[-1]])
    t.chain_ok(t.xf.par.rotate, t.root.par[ROTATE[-1]])


def test_group_is_one_group(t):
    t.promote.Promote(t.xf.parGroup.t, t.root)
    for lvl, base in zip(t.levels(),
                         ['Xft', 'Cxft', 'Bcxft', 'Abcxft']):
        t.eq(t.names(lvl), [base + 'x', base + 'y'], lvl.path)
        t.eq(len(lvl.parGroup[base]), 2, 'group size')
    t.xf.par.tx = 0.1
    t.xf.par.ty = 0.2
    top = t.root.parGroup.Abcxft
    t.near(top[0].eval(), 0.1, 'x')
    t.near(top[1].eval(), 0.2, 'y')
    top[0].val = -0.4
    t.near(t.xf.par.tx.eval(), -0.4, 'x back down')
    t.no_errors()


def test_one_axis_stays_one_axis(t):
    names = t.promote.Promote(t.xf.par.tx, t.root)
    t.eq(names, ['Xftx', 'Cxftx', 'Bcxftx', 'Abcxftx'])
    t.eq(t.names(t.root), ['Abcxftx'])
    t.eq(len(t.root.parGroup.Abcxftx), 1, 'single axis')
    t.eq(t.xf.par.ty.mode, ParMode.CONSTANT, 'ty is untouched')
    t.chain_ok(t.xf.par.tx, t.root.par.Abcxftx)


def test_axes_promoted_apart_then_group_replaces_them(t):
    t.promote.Promote(t.xf.par.tx, t.root)
    t.promote.Promote(t.xf.par.ty, t.root)
    t.promote.Promote(t.xf.parGroup.t, t.root)
    for lvl, base in zip(t.levels(), ['Xft', 'Cxft', 'Bcxft', 'Abcxft']):
        t.eq(t.names(lvl), [base + 'x', base + 'y'], lvl.path)
        t.eq(len(lvl.parGroup[base]), 2, 'one group')
    t.no_errors()


def test_axis_pulled_out_of_a_group(t):
    t.promote.Promote(t.xf.parGroup.t, t.root)
    t.promote.Promote(t.xf.par.tx, t.root)
    for lvl, base in zip(t.levels(), ['Xft', 'Cxft', 'Bcxft', 'Abcxft']):
        t.eq(sorted(t.names(lvl)), [base + 'x', base + 'y'], lvl.path)
        t.eq(len(lvl.parGroup[base + 'x']), 1, 'x alone')
        t.eq(len(lvl.parGroup[base + 'y']), 1, 'y alone')
    t.chain_ok(t.xf.par.tx, t.root.par.Abcxftx)
    t.chain_ok(t.xf.par.ty, t.root.par.Abcxfty)
    t.no_errors()


def test_axis_of_a_numbered_custom_group_is_labeled_by_its_number(t):
    page = t.c.appendCustomPage('Controls')
    page.appendInt('Count', label='Count', size=2)
    t.promote.Promote(t.c.par.Count2, t.root)
    for lvl, name in zip([t.b, t.a, t.root],
                         ['Ccount2', 'Bccount2', 'Abccount2']):
        t.eq(t.names(lvl), [name], lvl.path)
        t.eq(lvl.par[name].label, 'Count 2', lvl.path)
    t.no_errors()


def test_menu_toggle_string_and_int(t):
    cases = [(t.xf.par.extend, 'extend'), (t.xf.par.npasses, 'npasses')]
    for par, base in cases:
        name = t.promote.Promote(par, t.root)[-1]
        top = t.root.par[name]
        t.eq(top.isMenu, par.isMenu, base + ' menu')
        t.eq(top.isInt, par.isInt, base + ' int')
        t.eq(top.default, par.default, base + ' default')
    t.root.par.Abcxfextend = 'mirror'
    t.eq(t.xf.par.extend.eval(), 'mirror', 'menu value flows down')


def test_color_keeps_rgba_style(t):
    ramp = t.c.create(constantTOP, 'color')
    top = t.promote.Promote(ramp.parGroup.color, t.root)[-1]
    t.eq(t.root.parGroup[top].style, 'RGBA')
    t.eq(len(t.root.parGroup[top]), len(ramp.parGroup.color))


def test_refuses_expression(t):
    t.xf.par.rotate.expr = 'absTime.seconds'
    msg = t.raises(t.promote.Promote, t.xf.par.rotate, t.root)
    assert 'expression' in msg, msg
    t.eq(t.names(t.c), [])


def test_refuses_foreign_bind(t):
    t.c.create(transformTOP, 'side')
    t.xf.par.rotate.bindExpr = "op('side').par.rotate"
    t.xf.par.rotate.mode = ParMode.BIND
    t.eq(t.xf.par.rotate.mode, ParMode.BIND, 'fixture bind')
    t.raises(t.promote.Promote, t.xf.par.rotate, t.root)


def test_refuses_op_reference(t):
    ref = next(p for p in t.c.pars() if p.isOP)
    msg = t.raises(t.promote.Promote, ref, t.root)
    assert 'reference' in msg, msg


def test_refuses_dest_that_is_not_an_ancestor(t):
    side = t.root.create(baseCOMP, 'side')
    msg = t.raises(t.promote.Promote, t.xf.par.rotate, side)
    assert 'not an ancestor' in msg, msg


def test_refuses_dest_that_is_not_a_comp(t):
    t.raises(t.promote.Promote, t.xf.par.rotate, t.xf)


def test_refuses_name_taken_by_foreign_par(t):
    page = t.b.appendCustomPage(t.page)
    page.appendFloat('Cxfrotate')
    msg = t.raises(t.promote.Promote, t.xf.par.rotate, t.root)
    assert 'already has' in msg, msg
    t.eq(t.names(t.c), [], 'nothing created below the clash')


def test_status_line(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    assert ui.status.startswith('Promote: '), ui.status
    assert 'Abcxfrotate' in ui.status, ui.status


def test_result_has_no_tool_dependency(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    tool = t.tool.path
    for o in [t.root] + list(t.root.findChildren()):
        for p in o.pars():
            for text in (p.bindExpr, p.expr if p.mode == ParMode.EXPRESSION
                         else ''):
                assert tool not in (text or ''), (o.path, p.name, text)
