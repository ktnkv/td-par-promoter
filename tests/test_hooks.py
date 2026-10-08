"""The drop hooks in /ui. Read-only: the installed hooks are inspected, not
changed, and no pane owner is moved."""


def hooks(t):
    return t.promote._crumb_containers(), t.promote._timeline_pads()


def test_hooks_are_installed_while_active(t):
    if not t.tool.par.Active.eval():
        return
    crumbs, pads = hooks(t)
    assert crumbs and pads, 'nothing to hook'
    cb = t.tool.op('dropCallbacks')
    for c in crumbs + pads:
        t.eq(c.par.drop.eval(), 'usecallbacks', c.path)
        t.eq(c.par.dragdropcallbacks.eval(), cb.path, c.path)


def test_template_panebar_is_hooked(t):
    if not t.tool.par.Active.eval():
        return
    tmpl = op('/ui/dialogs/panebar/panebar_default/panenav/path')
    assert tmpl is not None
    t.eq(tmpl.par.drop.eval(), 'usecallbacks')


def test_timeline_drop_deletes_a_custom_par(t):
    page = t.b.appendCustomPage(t.page)
    page.appendFloat('Mine')
    t.promote.OnTimelineDrop([t.b.par.Mine])
    t.eq(t.iface(t.b), None)


def test_timeline_drop_unpromotes_a_chain(t):
    t.promote.Promote(t.xf.par.rotate, t.root)
    t.promote.OnTimelineDrop([t.xf.par.rotate])
    for lvl in t.levels():
        t.eq(t.iface(lvl), None, lvl.path)


def test_timeline_drop_of_a_plain_builtin_is_refused(t):
    before = t.snapshot()
    t.promote.OnTimelineDrop([t.xf.par.rotate])
    t.eq(t.snapshot(), before)
    assert 'REFUSED' in ui.status, ui.status


def test_timeline_drop_ignores_non_parameters(t):
    before = t.snapshot()
    t.promote.OnTimelineDrop([t.xf])
    t.eq(t.snapshot(), before)


def test_crumb_drop_on_a_separator_is_refused(t):
    crumbs = next((c for c in t.promote._crumb_containers()
                   if c.path.split('/')[4] in ui.panes), None)
    if crumbs is None:
        return
    before = t.snapshot()
    t.promote.OnCrumbDrop(crumbs, [t.xf.par.rotate], 2)
    t.eq(t.snapshot(), before)
    assert 'REFUSED' in ui.status, ui.status
    t.promote.OnCrumbDrop(crumbs, [t.xf.par.rotate], -1)
    assert 'REFUSED' in ui.status, ui.status
