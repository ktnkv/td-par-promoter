"""Promote test runner. Runs inside a live TouchDesigner.

    exec(open(project.folder + '/tests/run_tests.py').read())

Each tests/test_*.py defines test_* functions that take one argument, `t`
(see Harness). A test gets a fresh scratch COMP and the scratch is destroyed
after it, pass or fail. Nothing outside the scratch is created or removed.
Set ONLY to a substring to run matching tests: ONLY = 'unpromote'.
"""
import glob
import os
import traceback

TOOL_PATH = '/tools/promote'
SCRATCH_NAME = 'promote_test_scratch'


class Harness:
    """What a test sees: the tool, a scratch network, and a few asserts."""

    def __init__(self, tool):
        self.tool = tool
        self.promote = tool.ext.PromoteExt
        self.mod = tool.op('PromoteExt').module
        self.PromoteError = self.mod.PromoteError
        self.page = tool.par.Pagename.eval()
        self.root = None

    # ---- scratch ------------------------------------------------------
    def fresh(self):
        """New scratch: root/a/b/c with a transformTOP `xf` in c."""
        self.drop()
        self.root = op('/').create(baseCOMP, SCRATCH_NAME)
        self.a = self.root.create(baseCOMP, 'a')
        self.b = self.a.create(baseCOMP, 'b')
        self.c = self.b.create(baseCOMP, 'c')
        self.src = self.c.create(constantTOP, 'src')
        self.xf = self.c.create(transformTOP, 'xf')
        self.src.outputConnectors[0].connect(self.xf)
        return self

    def drop(self):
        old = op('/' + SCRATCH_NAME)
        if old is not None:
            old.destroy()
        self.root = None

    def levels(self):
        """Scratch COMPs from the source's parent up to the root."""
        return [self.c, self.b, self.a, self.root]

    # ---- reading state ------------------------------------------------
    def iface(self, comp):
        return next((p for p in comp.customPages if p.name == self.page),
                    None)

    def names(self, comp):
        """Parameter names on the Interface page, headers left out."""
        page = self.iface(comp)
        if page is None:
            return []
        return [p.name for pg in page.parGroups for p in pg
                if p.style != 'Header']

    def headers(self, comp):
        """Header labels on the Interface page, in page order."""
        page = self.iface(comp)
        if page is None:
            return []
        return [pg[0].label for pg in page.parGroups
                if pg[0].style == 'Header']

    def groups(self, comp):
        page = self.iface(comp)
        if page is None:
            return []
        return [pg.name for pg in page.parGroups]

    def snapshot(self):
        """Everything Promote could change, as plain data."""
        out = {}
        for comp in [self.root] + list(self.root.findChildren()):
            for p in comp.pars():
                out[(comp.path, p.name)] = (
                    str(p.mode), p.bindExpr if p.mode == ParMode.BIND else '',
                    str(p.eval()))
        return out

    # ---- asserts ------------------------------------------------------
    def eq(self, got, want, what=''):
        assert got == want, '%s: got %r, want %r' % (what or 'value', got, want)

    def near(self, got, want, what=''):
        assert abs(got - want) < 1e-6, '%s: got %r, want %r' % (
            what or 'value', got, want)

    def no_errors(self):
        for o in [self.root] + list(self.root.findChildren()):
            o.cook(force=True)
        errs = self.root.errors(recurse=True)
        assert not errs, 'errors in scratch: %s' % errs

    def raises(self, fn, *args, **kw):
        """fn must raise PromoteError and leave the scratch unchanged."""
        before = self.snapshot()
        try:
            fn(*args, **kw)
        except self.PromoteError as e:
            self.eq(self.snapshot(), before, 'state after refusal')
            return str(e)
        raise AssertionError('expected PromoteError from %s' % fn)

    def chain_ok(self, source, top):
        """Source is bound up to `top`, and values flow both ways."""
        for new in (0.25, 0.75):
            top.val = new
            self.near(source.eval(), new, 'top -> source')
        source.val = 0.5
        self.near(top.eval(), 0.5, 'source -> top')


def _load(path):
    ns = dict(globals())
    exec(compile(open(path).read(), path, 'exec'), ns)
    return [(os.path.basename(path)[:-3] + '.' + k, v)
            for k, v in ns.items() if k.startswith('test_') and callable(v)]


def run():
    tool = op(TOOL_PATH)
    if tool is None:
        raise RuntimeError('%s not found' % TOOL_PATH)
    t = Harness(tool)
    only = globals().get('ONLY')
    tests = []
    for path in sorted(glob.glob(project.folder + '/tests/test_*.py')):
        tests += _load(path)
    if only:
        tests = [x for x in tests if only in x[0]]
    passed, failed = 0, []
    for name, fn in tests:
        t.fresh()
        try:
            fn(t)
            passed += 1
        except Exception:
            failed.append((name, traceback.format_exc(limit=4)))
        finally:
            t.drop()
    for name, tb in failed:
        print('FAIL', name)
        print(tb)
    print('%d passed, %d failed (%d tests)' % (passed, len(failed), len(tests)))
    return not failed


RESULT = run()
