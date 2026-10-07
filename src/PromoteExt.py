"""Promote: promote a parameter up through its ancestor COMPs.

Drag a parameter onto an ancestor crumb of the TouchDesigner address bar and
every COMP from owner.parent() up to the dropped-on ancestor receives a custom
parameter (under a Header) that is bound to the level below it.

Dev-time tool only: the result is plain TouchDesigner (custom pars + binds),
nothing depends on this plugin at runtime. The plugin keeps no list of managed
COMPs; Update all finds them by their page at the moment it is pulsed.
"""
import re

HEADER_PREFIX = 'Hdr'      # custom-par name prefix of headers
SKIP_ROOTS = ('ui', 'sys', 'local', 'perform')


class PromoteError(Exception):
    """User-facing refusal; nothing has been changed when this is raised."""


def _settle_paths(isUndo, info):
    """Clear bind errors left while an undo step restored names and expressions.

    Undo puts the name and the expression back together, but the lookup that
    happens between those two steps stays on the operator until it cooks.
    """
    seen = set()
    for path in list(info or []):
        o = op(path)
        if o is None:
            continue
        nodes = [o]
        if o.isCOMP:
            nodes.extend(o.findChildren())
        for node in nodes:
            if node.path in seen:
                continue
            seen.add(node.path)
            if node.errors():
                node.cook(force=True)


# --------------------------------------------------------------------------
# naming helpers
# --------------------------------------------------------------------------
def par_name(*parts):
    """Legal custom-par name from parts: First capital, rest [a-z0-9]."""
    s = re.sub(r'[^0-9a-z]', '', ''.join(parts).lower())
    if not s:
        raise PromoteError('cannot build a parameter name from %r' % (parts,))
    if s[0].isdigit():
        s = 'p' + s
    return s[0].upper() + s[1:]


def header_name(label):
    return par_name(HEADER_PREFIX, label)


def rel_parts(level, op_):
    """Names of the path from `level` down to `op_` (exclusive of level)."""
    lp = [x for x in level.path.split('/') if x]
    op_p = [x for x in op_.path.split('/') if x]
    return op_p[len(lp):]


# --------------------------------------------------------------------------
# ParSpec: everything needed to re-create a parameter (tuplet) as a custom par
# --------------------------------------------------------------------------
class ParSpec:
    _RANGE_ATTRS = ('min', 'max', 'clampMin', 'clampMax', 'normMin', 'normMax')

    # Letters TouchDesigner appends for a vector-style custom parameter.
    _KIND_SUFFIX = {
        'XY': 'xy',
        'XYZ': 'xyz',
        'XYZW': 'xyzw',
        'UV': 'uv',
        'UVW': 'uvw',
        'WH': 'wh',
        'RGB': 'rgb',
        'RGBA': 'rgba',
    }

    def __init__(self, tuplet):
        p0 = tuplet[0]
        self.tuplet = tuple(tuplet)
        self.size = len(tuplet)
        # One axis of a larger tuplet keeps its own name. The whole group,
        # and a parameter that is not part of one, keep tupletName.
        self.solo = self.size == 1 and len(tuple(p0.tuplet)) > 1
        self.base = p0.name if self.solo else p0.tupletName
        group_label = p0.parGroup.label or p0.label or ''
        if self.solo:
            sub = (p0.subLabel or '').strip()
            self.label = ((group_label + ' ' + sub).strip() if sub
                          else p0.name)
        else:
            self.label = group_label or p0.label
        self.help = p0.help
        self.kind = self._kind(p0, self.size)
        self.default = [p.default for p in tuplet]
        self.value = [p.val for p in tuplet]
        self.ranges = [{a: getattr(p, a) for a in self._RANGE_ATTRS}
                       for p in tuplet] if p0.isNumber else None
        self.menu = ((list(p0.menuNames), list(p0.menuLabels))
                     if p0.isMenu else None)

    @staticmethod
    def _kind(p, n):
        if p.isOP:
            raise PromoteError(
                "'%s': reference (OP) parameters are not supported - a "
                "relative path would resolve differently on every level"
                % p.name)
        if p.isPython or p.sequence is not None:
            raise PromoteError("'%s': Python/sequence parameters are not "
                               "supported" % p.name)
        if p.isPulse:
            return 'Pulse'
        if p.isMomentary:
            return 'Momentary'
        if p.isToggle:
            return 'Toggle'
        if p.isMenu:
            return 'StrMenu' if p.isString else 'Menu'
        if p.isString:
            return p.style if p.style in ('File', 'Folder', 'FileSave') \
                else 'Str'
        if p.isInt:
            return 'Int'
        if p.isFloat:
            st = p.style
            if st in ('RGB', 'RGBA', 'UV', 'UVW', 'WH') and \
                    n == len(st):
                return st
            return {1: 'Float', 2: 'XY', 3: 'XYZ', 4: 'XYZW'}.get(n, 'Float')
        raise PromoteError("'%s': unsupported parameter type" % p.name)

    def member_names(self, group_name):
        """Script names `create` will give this parameter on a page."""
        suf = self._KIND_SUFFIX.get(self.kind)
        if suf is not None and len(suf) == self.size:
            return [group_name + c for c in suf]
        if self.size > 1:
            return [group_name + str(i) for i in range(1, self.size + 1)]
        return [group_name]

    def create(self, page, name, label_suffix=''):
        """Append this parameter to `page`; returns the new tuplet of Pars."""
        kind = self.kind
        kw = {'label': self.label + label_suffix}
        if kind in ('Int', 'Float') or (kind == 'Str' and self.size > 1):
            kw['size'] = self.size
        pg = getattr(page, 'append' + kind)(name, **kw)
        tup = pg[0].tuplet
        if len(tup) != self.size:
            raise PromoteError('could not create %s of size %d (got %d)'
                               % (kind, self.size, len(tup)))
        if self.menu:
            tup[0].menuNames, tup[0].menuLabels = self.menu
        for i, p in enumerate(tup):
            if self.ranges:
                for a, v in self.ranges[i].items():
                    setattr(p, a, v)
            p.default = self.default[i]
            p.val = self.value[i]
            p.help = self.help
        return tup


# --------------------------------------------------------------------------
# the extension
# --------------------------------------------------------------------------
class PromoteExt:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp

    # ---- plugin parameters ------------------------------------------------
    @property
    def _pagename(self):
        return self.ownerComp.par.Pagename.eval()

    def _say(self, msg):
        ui.status = 'Promote: ' + msg

    # ======================================================================
    # Promote
    # ======================================================================
    @staticmethod
    def _drag_members(par):
        """Parameters this drop applies to.

        A ParGroup is the whole tuplet, without a unit parameter that shares
        the row. A Par is that parameter alone, even inside a larger tuplet.
        """
        if isinstance(par, ParGroup):
            return tuple(par[0].tuplet)
        return (par,)

    def Promote(self, par, dest):
        """Promote the dragged parameter or group to ancestor COMP `dest`.

        A ParGroup is the whole tuplet. A Par is only that parameter. Either
        one is followed down to the parameter that is not already on the
        Interface page, so dragging a promoted axis is the same as dragging
        its source.

        An axis becomes its own parameter on every level up to `dest`, and is
        pulled out of a custom group that still holds it. A group becomes one
        group on those levels; axes of that tuplet promoted on their own are
        removed and join it. A bind that is not this chain is refused before
        anything is written.

        Returns the custom-par names, top level last.
        """
        dest = op(dest) if isinstance(dest, str) else dest
        dragged = self._drag_members(par)
        sources = tuple(self._follow_to_source(m) for m in dragged)
        if any(s.owner is not sources[0].owner for s in sources):
            raise PromoteError('%s parameters are not on one operator'
                               % sources[0].owner.path)
        owner = sources[0].owner
        spec = ParSpec(sources)
        for src in sources:
            self._refuse_foreign(src, src)
        levels = self._levels(owner, dest)
        plans = self._promote_plans(spec, sources, owner, levels)

        ui.undo.startBlock('Promote %s.%s -> %s'
                           % (owner.name, spec.base, dest.path))
        try:
            names = self._promote_apply(spec, sources, owner, levels, plans)
        except PromoteError:
            ui.undo.endBlock()
            ui.undo.undo()
            raise
        except Exception as e:
            ui.undo.endBlock()
            ui.undo.undo()
            raise PromoteError('%s' % e)
        ui.undo.endBlock()
        self._say('%s.%s -> %s (%d levels)'
                  % (owner.path, spec.base, names[-1], len(levels)))
        return names

    def _follow_to_source(self, par):
        """Walk promote slaves down to a parameter not on the Interface page."""
        cur, seen = par, set()
        while self._on_interface(cur):
            ident = (cur.owner.path, cur.name)
            if ident in seen:
                raise PromoteError('bind cycle at %s.%s' % ident)
            seen.add(ident)
            slaves = [ref for ref in cur.bindReferences
                      if self._is_promote_slave(ref, cur)]
            if len(slaves) != 1:
                break
            cur = slaves[0]
        return cur

    def _refuse_foreign(self, par, source):
        """Expression, export, or a bind that is not this promote chain."""
        if par.mode == ParMode.CONSTANT:
            return
        if par.mode != ParMode.BIND:
            raise PromoteError("'%s' is driven by an expression or export"
                               % par.name)
        master = self._promote_master(par)
        if master is None:
            raise PromoteError("'%s' is already bound or driven elsewhere"
                               % par.name)
        src, steps = self._chain_source(master)
        if steps < 1 or not src.isSamePar(source):
            raise PromoteError("'%s' is already bound or driven elsewhere"
                               % par.name)

    def _promote_plans(self, spec, sources, owner, levels):
        """One action per level. Nothing is written.

        'reuse' keeps a custom parameter whose members are already exactly
        these sources. 'extract' pulls the one dragged axis out of its group.
        'create' builds the group, after removing axes that were promoted apart.
        """
        plans = []
        for lvl in levels:
            found = self._ours_on(lvl, sources)
            seen = {}
            for member, src in found:
                key = (src.owner.path, src.name)
                if key in seen:
                    raise PromoteError(
                        "%s already has a parameter '%s' that is not part of "
                        "this chain" % (lvl.path, member.name))
                seen[key] = member
                self._refuse_foreign(member, src)
            exact = self._exact_group(lvl, sources)
            desired = par_name(*rel_parts(lvl, owner), spec.base)
            if exact is not None:
                plans.append({
                    'lvl': lvl, 'role': 'reuse', 'masters': exact,
                    'rebuilds': [], 'consumed': [None] * len(sources),
                    'desired': desired,
                })
                continue
            rebuilds, consumed = self._rebuilds_for(
                lvl, sources, found, spec, desired)
            role = 'extract' if spec.size == 1 and found else 'create'
            if role == 'create':
                self._names_clear(lvl, spec.member_names(desired), rebuilds)
            plans.append({
                'lvl': lvl, 'role': role, 'masters': None,
                'rebuilds': rebuilds, 'consumed': consumed,
                'desired': desired,
            })
        return plans

    def _ours_on(self, lvl, sources):
        """[(member, source)] on this Interface page for these sources."""
        page = next((p for p in lvl.customPages
                     if p.name == self._pagename), None)
        if page is None:
            return []
        out = []
        for pg in page.parGroups:
            if pg[0].style == 'Header':
                continue
            for member in pg[0].tuplet:
                src, steps = self._chain_source(member)
                if steps < 1:
                    continue
                if any(src.isSamePar(s) for s in sources):
                    out.append((member, src))
        return out

    def _exact_group(self, lvl, sources):
        """Members of a custom group that is already exactly `sources`, in order."""
        page = next((p for p in lvl.customPages
                     if p.name == self._pagename), None)
        if page is None:
            return None
        for pg in page.parGroups:
            if pg[0].style == 'Header':
                continue
            members = tuple(pg[0].tuplet)
            if len(members) != len(sources):
                continue
            ok = True
            for member, src in zip(members, sources):
                found, steps = self._chain_source(member)
                if steps < 1 or not found.isSamePar(src):
                    ok = False
                    break
            if ok:
                return members
        return None

    def _rebuilds_for(self, lvl, sources, found, spec, desired):
        """Groups that lose the dragged axes, and consumed pars in source order."""
        by_src = {(src.owner.path, src.name): member for member, src in found}
        consumed = [by_src.get((s.owner.path, s.name)) for s in sources]
        groups, seen = [], set()
        for member, _src in found:
            group = member.parGroup
            if group.name in seen:
                continue
            seen.add(group.name)
            groups.append(group)
        rebuilds = []
        gesture_names = [] if spec.size == 1 and found else spec.member_names(desired)
        for group in groups:
            members = tuple(group[0].tuplet)
            ours, keepers = [], []
            for member in members:
                src, steps = self._chain_source(member)
                if (steps >= 1 and any(src.isSamePar(s) for s in sources)):
                    ours.append(member)
                else:
                    keepers.append(member)
            extracts = ours if spec.size == 1 else []
            reserved = {m.name for m in extracts}
            reserved.update(gesture_names)
            reserved.update(self._surviving_names(lvl, members))
            rebuilds.append({
                'group_name': group.name,
                'members': members,
                'keepers': self._keeper_plan(
                    lvl, group.name, keepers, reserved),
                'extracts': extracts,
                'extract_names': [p.name for p in extracts],
            })
        return rebuilds, consumed

    def _surviving_names(self, lvl, doomed_members):
        """Custom names on `lvl` that this rebuild will not destroy."""
        doomed = {m.name for m in doomed_members}
        page = next((p for p in lvl.customPages
                     if p.name == self._pagename), None)
        names = set()
        if page is None:
            return names
        for pg in page.parGroups:
            for member in pg:
                if member.name not in doomed:
                    names.add(member.name)
        return names

    def _keeper_plan(self, lvl, group_name, keepers, reserved):
        """How to put the axes that stay back after the group is destroyed.

        One axis keeps its script name. Two or more become one group again.
        Letter suffixes are kept when they do not collide; otherwise the
        group is a numbered float or int and binds are rewritten.
        """
        if not keepers:
            return None
        if len(keepers) == 1:
            return {'solo': True, 'par': keepers[0], 'name': keepers[0].name}
        srcs = []
        for par in keepers:
            src, steps = self._chain_source(par)
            srcs.append(src if steps >= 1 else par)
        kspec = ParSpec(tuple(srcs))
        names = kspec.member_names(group_name)
        if any(n in reserved for n in names):
            if srcs[0].isFloat:
                kspec.kind = 'Float'
            elif srcs[0].isInt:
                kspec.kind = 'Int'
            names = kspec.member_names(group_name)
        for name in names:
            if name in reserved:
                raise PromoteError(
                    "%s already has a parameter '%s' that is not part of "
                    "this chain" % (lvl.path, name))
        return {
            'solo': False, 'pars': keepers, 'sources': srcs, 'spec': kspec,
            'names': names, 'olds': [p.name for p in keepers],
            'group_name': group_name,
        }

    def _names_clear(self, lvl, names, rebuilds):
        """Refuse a new name owned by a parameter this promote does not replace."""
        doomed = set()
        for rb in rebuilds:
            for member in rb['members']:
                doomed.add(member.name)
        for name in names:
            if name in doomed or lvl.par[name] is None:
                continue
            raise PromoteError(
                "%s already has a parameter '%s' that is not part of "
                "this chain" % (lvl.path, name))

    def _promote_apply(self, spec, sources, owner, levels, plans):
        """Reshape, bind bottom-up, then sort. Call inside the undo block."""
        spec.value = [s.eval() for s in sources]
        for plan in plans:
            plan['consumed_names'] = [
                None if p is None else p.name for p in plan['consumed']]
        doomed = []
        for plan in plans:
            for rb in plan['rebuilds']:
                doomed.extend(rb['members'])
            keepers = [rb['keepers'] for rb in plan['rebuilds']]
            for kb in keepers:
                if kb and not kb['solo']:
                    kb['spec'].value = [p.eval() for p in kb['pars']]
        freezes = [self._freeze(p) for p in doomed]
        doomed_keys = {(p.owner.path, p.name) for p in doomed}
        ref_values = {}
        for fr in freezes:
            for ref, _path, _name, _expr in fr['refs']:
                if id(ref) not in ref_values:
                    ref_values[id(ref)] = ref.eval()
        released = set()

        def release(par, value):
            if id(par) in released:
                return
            released.add(id(par))
            self._release_bind(par)
            par.val = value

        for fr in freezes:
            for ref, _path, _name, _expr in fr['refs']:
                release(ref, ref_values[id(ref)])
            release(fr['par'], fr['value'])
        groups, seen_groups = [], set()
        for par in doomed:
            group = par.parGroup
            if group is None:
                continue
            key = (par.owner.path, group.name)
            if key in seen_groups:
                continue
            seen_groups.add(key)
            groups.append(group)
        for group in groups:
            group.destroy()

        replacements = {}
        masters_per_level = []
        tokens = []
        for plan in plans:
            lvl = plan['lvl']
            if plan['role'] == 'reuse':
                masters_per_level.append(plan['masters'])
                continue
            page = self._page(lvl)
            self._header(lvl, page, owner)
            for rb in plan['rebuilds']:
                tokens.extend(self._rebuild(
                    lvl, page, rb, freezes, replacements))
            if plan['role'] == 'create':
                created = spec.create(page, plan['desired'])
                masters = list(created)
                for old, old_name, newp in zip(
                        plan['consumed'], plan['consumed_names'], masters):
                    if old is None:
                        continue
                    replacements[(lvl.path, old_name)] = newp
                    if old_name != newp.name:
                        tokens.append((old_name, newp.name))
            else:
                masters = []
                for old_name in plan['consumed_names']:
                    if old_name is None:
                        raise PromoteError(
                            '%s lost the promoted axis' % lvl.path)
                    masters.append(replacements[(lvl.path, old_name)])
            masters_per_level.append(masters)

        tokens = [(old, new) for old, new in tokens if old != new]
        tokens.sort(key=lambda pair: -len(pair[0]))
        for fr in freezes:
            newp = replacements.get((fr['path'], fr['name']))
            if newp is None:
                continue
            if fr['mode'] == ParMode.BIND and fr['bindExpr']:
                self._bind_expr(newp, self._swap_tokens(fr['bindExpr'], tokens))
            for ref, ref_path, ref_name, expr in fr['refs']:
                if (ref_path, ref_name) in doomed_keys:
                    continue
                updated = expr
                if expr == 'parent().par.' + fr['name']:
                    updated = 'parent().par.' + newp.name
                elif fr['name'] != newp.name:
                    updated = self._swap_tokens(expr, [(fr['name'], newp.name)])
                self._bind_expr(ref, updated)

        below = list(sources)
        names = []
        for masters in masters_per_level:
            for slave, master in zip(below, masters):
                if not self._is_linked(slave, master):
                    self._link(slave, master)
            below = list(masters)
            names.append(masters[0].parGroup.name)
        for lvl in levels:
            self._update_level(lvl)
        return names

    def _freeze(self, par):
        """Bind state captured before a parameter is destroyed."""
        src, steps = self._chain_source(par)
        return {
            'par': par,
            'path': par.owner.path,
            'name': par.name,
            'value': par.eval(),
            'mode': par.mode,
            'bindExpr': par.bindExpr or '',
            'source': src if steps >= 1 else par,
            'refs': [(ref, ref.owner.path, ref.name, ref.bindExpr or '')
                     for ref in list(par.bindReferences)
                     if ref.mode == ParMode.BIND],
        }

    def _rebuild(self, lvl, page, rb, freezes, replacements):
        """Recreate keepers and extracted axes. Consumed axes are not put back.

        Returns rename tokens for keeper script names that changed.
        """
        by_key = {(fr['path'], fr['name']): fr for fr in freezes}
        tokens = []
        kb = rb['keepers']
        if kb and kb['solo']:
            key = (lvl.path, kb['name'])
            fr = by_key[key]
            spec = ParSpec((fr['source'],))
            spec.value = [fr['value']]
            spec.create(page, kb['name'])
            newp = lvl.par[kb['name']]
            if newp is None:
                raise PromoteError('could not restore %s.%s'
                                   % (lvl.path, kb['name']))
            replacements[key] = newp
        elif kb:
            kb['spec'].create(page, kb['group_name'])
            group = lvl.parGroup[kb['group_name']]
            if group is None:
                raise PromoteError('could not restore %s.%s'
                                   % (lvl.path, kb['group_name']))
            made = list(group[0].tuplet)
            if [p.name for p in made] != kb['names']:
                raise PromoteError('could not restore %s.%s'
                                   % (lvl.path, kb['group_name']))
            for old_name, newp in zip(kb['olds'], made):
                replacements[(lvl.path, old_name)] = newp
                if old_name != newp.name:
                    tokens.append((old_name, newp.name))
        for name in rb['extract_names']:
            fr = by_key[(lvl.path, name)]
            spec = ParSpec((fr['source'],))
            spec.value = [fr['value']]
            spec.create(page, fr['name'])
            newp = lvl.par[fr['name']]
            if newp is None:
                raise PromoteError('could not restore %s.%s'
                                   % (lvl.path, fr['name']))
            replacements[(lvl.path, fr['name'])] = newp
        return tokens

    @staticmethod
    def _levels(owner, dest):
        if dest is None or not dest.isCOMP:
            raise PromoteError('drop target is not a COMP')
        chain, c = [], owner.parent()
        while c is not None:
            chain.append(c)
            if c is dest:
                return chain
            c = c.parent()
        raise PromoteError('%s is not an ancestor of %s'
                           % (dest.path, owner.path))

    @staticmethod
    def _is_linked(slave, master):
        if slave is None or master is None or slave.mode != ParMode.BIND:
            return False
        m = slave.bindMaster
        return m is not None and m.owner is master.owner and m.name == master.name

    @staticmethod
    def _link(slave, master):
        PromoteExt._bind_expr(slave, 'parent().par.' + master.name)

    @staticmethod
    def _bind_expr(par, expr):
        par.bindExpr = expr
        par.mode = ParMode.BIND
        if par.bindMaster is None and not par.isPulse:
            raise PromoteError('bind of %s.%s did not resolve (%s)'
                               % (par.owner.path, par.name, expr))

    # ---- custom page / headers --------------------------------------------
    def _page(self, lvl):
        for pg in lvl.customPages:
            if pg.name == self._pagename:
                return pg
        return lvl.appendCustomPage(self._pagename)

    def _header(self, lvl, page, owner):
        label = '.'.join(rel_parts(lvl, owner))
        name = header_name(label)
        if lvl.par[name] is None:
            h = page.appendHeader(name, label=label)
            h[0].startSection = True

    # ======================================================================
    # Unpromote
    # ======================================================================
    def Unpromote(self, par):
        """Cut the promote chain at the dragged parameter or group.

        A ParGroup removes every member that is in a promote chain, whether
        they were promoted together or one by one. A Par removes only that
        parameter. The other axes of a group promoted together stay promoted:
        TouchDesigner cannot delete one member of a custom group, so those
        axes are recreated as their own parameters and keep their binds.

        The dragged parameter and every master above it are deleted. The
        parameter bound directly below becomes a constant and keeps its
        value; anything bound below that is left as it was. A built-in
        parameter cannot be deleted, so it becomes that constant and only
        the masters go.

        A custom parameter that is not in a promote chain is deleted too.
        One axis leaves the other axes of its group in place. The whole
        group goes when the group itself was dragged.

        Returns the removed names, or None when nothing dragged is a custom
        parameter or a promote chain. Raises PromoteError (and changes
        nothing) when the cut would break some other bind.
        """
        members = self._drag_members(par)
        cuts = []
        for m in members:
            cut = self._cut_member(m)
            if cut is not None:
                cuts.append(cut)
        if not cuts:
            return None
        bottoms = [c['up'][0] for c in cuts]
        custom = [m.isCustom for m in bottoms]
        if any(custom) and not all(custom):
            raise PromoteError('%s is not one promote chain'
                               % bottoms[0].owner.path)
        held, groups, owners = self._removal_plan(cuts)
        values = [(p, p.eval()) for p in held]

        stem = (members[0].name if len(members) == 1 and
                len(members[0].tuplet) > 1 else members[0].tupletName)
        ui.undo.startBlock('Unpromote %s.%s'
                           % (members[0].owner.name, stem))
        try:
            for p, value in values:
                self._release_bind(p)
                p.val = value
            for cut in cuts:
                for par in cut['up'][:-1]:
                    self._release_bind(par)
            removed = []
            for ginfo in groups:
                removed.extend(self._cut_group(ginfo))
            for comp in owners:
                self._cleanup_page(comp)
        except Exception as e:
            ui.undo.endBlock()
            ui.undo.undo()
            raise PromoteError('%s' % e)
        ui.undo.endBlock()
        self._say('removed %s (%d levels)'
                  % (', '.join(removed), len(removed)))
        return removed

    def _removal_plan(self, cuts):
        """Parameters that become constants, groups that lose members, owners.

        Groups are unique and ordered parent-first, so a kept axis is
        recreated upstairs before the level below binds to it again.
        """
        held = []
        buckets, order = {}, []
        for cut in cuts:
            bottom = cut['up'][0]
            if bottom.isCustom:
                if cut['slave'] is not None:
                    held.append(cut['slave'])
            else:
                held.append(bottom)
            depth = len(cut['up'])
            levels = range(0 if bottom.isCustom else 1, depth)
            for level in levels:
                par = cut['up'][level]
                group = par.parGroup
                if group is None:
                    raise PromoteError('%s.%s has no parameter group'
                                       % (par.owner.path, par.name))
                key = (par.owner.path, group.name)
                if key not in buckets:
                    page = par.page
                    buckets[key] = {
                        'owner': par.owner,
                        'page': None if page is None else page.name,
                        'group_name': group.name,
                        'cutting': [],
                    }
                    order.append(key)
                buckets[key]['cutting'].append(par)
        order.sort(key=lambda k: (k[0].count('/'), k[0], k[1]))
        groups = [buckets[k] for k in order]
        owners, seen = [], set()
        for ginfo in groups:
            path = ginfo['owner'].path
            if path not in seen:
                seen.add(path)
                owners.append(ginfo['owner'])
        return held, groups, owners

    def _cut_group(self, ginfo):
        """Delete the cut members of one custom group. Keep the other axes.

        Returns the names that went away. A group that loses every member
        is named once. A group that keeps an axis reports the removed
        member names; those axes come back as their own parameters.
        """
        comp = ginfo['owner']
        group = comp.parGroup[ginfo['group_name']]
        if group is None:
            raise PromoteError("%s has no '%s' to remove"
                               % (comp.path, ginfo['group_name']))
        tuplet = tuple(group[0].tuplet)
        cutting = ginfo['cutting']
        keepers = [p for p in tuplet
                   if not any(p.isSamePar(c) for c in cutting)]
        if not keepers:
            name = group.name
            group.destroy()
            return [name]
        snaps = [self._snap_keeper(p) for p in keepers]
        removed = []
        seen = set()
        for p in cutting:
            if p.name not in seen:
                seen.add(p.name)
                removed.append(p.name)
        page_name = ginfo['page'] or self._pagename
        group.destroy()
        page = next((pg for pg in comp.customPages if pg.name == page_name),
                    None)
        if page is None:
            page = comp.appendCustomPage(page_name)
        for snap in snaps:
            self._restore_keeper(comp, page, snap)
        return removed

    def _snap_keeper(self, par):
        """Enough to rebuild one axis after its group is destroyed.

        Slaves are parked as constants first. Destroying the group would
        otherwise leave their binds pointing at a name that is gone.
        """
        spec = ParSpec((par,))
        spec.value = [par.eval()]
        refs = []
        for ref in list(par.bindReferences):
            if ref.mode != ParMode.BIND:
                continue
            refs.append((ref, ref.bindExpr or ''))
            self._release_bind(ref)
        return {
            'spec': spec,
            'name': par.name,
            'mode': par.mode,
            'bindExpr': par.bindExpr or '',
            'refs': refs,
        }

    @staticmethod
    def _release_bind(par):
        """Leave a constant and drop the expression.

        Setting the mode alone keeps the old bind expression. Destroying the
        master then makes the whole group look that name up and log an error.
        """
        if par.mode != ParMode.CONSTANT:
            par.mode = ParMode.CONSTANT
        if par.bindExpr:
            par.bindExpr = ''

    def _restore_keeper(self, comp, page, snap):
        snap['spec'].create(page, snap['name'])
        newp = comp.par[snap['name']]
        if newp is None:
            raise PromoteError('could not restore %s.%s'
                               % (comp.path, snap['name']))
        if snap['mode'] == ParMode.BIND and snap['bindExpr']:
            newp.bindExpr = snap['bindExpr']
            newp.mode = ParMode.BIND
            if newp.bindMaster is None and not newp.isPulse:
                raise PromoteError('bind of %s.%s did not resolve (%s)'
                                   % (newp.owner.path, newp.name, snap['bindExpr']))
        for ref, expr in snap['refs']:
            ref.bindExpr = expr
            ref.mode = ParMode.BIND
            if ref.bindMaster is None and not ref.isPulse:
                raise PromoteError('bind of %s.%s did not resolve (%s)'
                                   % (ref.owner.path, ref.name, expr))

    def _cut_member(self, par):
        """{'up': [par, master, ...], 'slave': par or None}, or None.

        None means this parameter is built-in and not in a promote chain.
        A custom parameter with no chain is still a cut: only that parameter
        goes. An extra bind raises, so the caller can refuse before writing.
        """
        up = self._masters_including(par)
        slaves, extras = self._down_links(par)
        has_master = len(up) > 1
        # A lone custom parameter has no promote master and no promote slave.
        # It is still removed. A built-in in that spot, or a slave link that
        # is not on the Interface page, is not a chain.
        if not has_master and (not self._on_interface(par) or not slaves):
            if not (par.isCustom and not slaves):
                return None
        if len(slaves) > 1 or (par.isCustom and extras):
            raise PromoteError('%s.%s has other binds'
                               % (par.owner.path, par.name))
        for i in range(1, len(up)):
            master = up[i]
            below = up[i - 1]
            m_slaves, m_extras = self._down_links(master)
            if (m_extras or len(m_slaves) != 1
                    or not self._same_par(m_slaves[0], below)
                    or not master.isCustom):
                raise PromoteError('%s.%s is not a single promote link'
                                   % (master.owner.path, master.name))
        return {'up': up, 'slave': slaves[0] if slaves else None}

    def _masters_including(self, par):
        """`par`, then each promote master above it, up to the top."""
        chain, seen = [], set()
        cur = par
        while cur is not None and len(chain) < 32:
            ident = (cur.owner.path, cur.name)
            if ident in seen:
                raise PromoteError('bind cycle at %s.%s' % ident)
            seen.add(ident)
            chain.append(cur)
            cur = self._promote_master(cur)
        return chain

    def _promote_master(self, par):
        """Master on the Interface page that `par` is bound to, or None."""
        if par.mode != ParMode.BIND:
            return None
        master = par.bindMaster
        if master is None or not self._on_interface(master):
            return None
        if par.owner.parent() is not master.owner:
            return None
        if par.bindExpr != 'parent().par.' + master.name:
            return None
        return master

    def _down_links(self, par):
        """(promote slaves, other bind references) of `par`."""
        slaves, extras = [], []
        for ref in par.bindReferences:
            if self._is_promote_slave(ref, par):
                slaves.append(ref)
            else:
                extras.append(ref)
        return slaves, extras

    @staticmethod
    def _is_promote_slave(slave, master):
        if slave.mode != ParMode.BIND or slave.owner.parent() is not master.owner:
            return False
        if slave.bindExpr != 'parent().par.' + master.name:
            return False
        bound = slave.bindMaster
        return (bound is not None and bound.owner is master.owner
                and bound.name == master.name)

    @staticmethod
    def _same_par(a, b):
        return a is not None and b is not None and a.owner is b.owner and a.name == b.name

    def _cleanup_page(self, comp):
        """Drop empty headers, then the page itself when nothing is left."""
        self._update_level(comp)
        page = next((p for p in comp.customPages
                     if p.name == self._pagename), None)
        if page is not None and not list(page.parGroups):
            page.destroy()

    # ======================================================================
    # Update
    # ======================================================================
    def Updateall(self):
        """Re-sort every managed page, deepest COMP first.

        A COMP is managed when it has a custom page named Pagename. That set
        is collected here, so a rename or a copy is seen without a stored
        list. Deepest first: a parent reads its child's page order while
        sorting its own.
        """
        comps = self._managed_comps()
        comps.sort(key=lambda c: -c.path.count('/'))
        self._update_comps(comps)

    def _update_comps(self, comps):
        """Rename to the current paths, then sort. Deepest comp first.

        The plan is validated before anything is written. A collision or a
        failed bind rolls the whole update back.
        """
        plans = []
        for comp in comps:
            pairs, err = self._rename_plan(comp)
            if err:
                self._say('REFUSED - ' + err)
                return
            plans.append(pairs)
        if not any(plans):
            for comp in comps:
                self._update_level(comp)
            return
        ui.undo.startBlock('Update Interface')
        # First callback runs last on undo, after the names and expressions
        # are back. The second runs last on redo. Both share the path list.
        settle = [c.path for c in comps]
        ui.undo.addCallback(_settle_paths, settle)
        try:
            renamed = []
            announced = []
            touched = []
            for comp, pairs in zip(comps, plans):
                tokens, owners = self._rename_groups(comp, pairs)
                renamed += tokens
                touched += owners
                announced += pairs
            touched += self._rewrite_name_refs(renamed)
            for comp in comps:
                self._update_level(comp)
                touched.append(comp)
            for o in touched:
                if o is not None and o.path not in settle:
                    settle.append(o.path)
            ui.undo.addCallback(_settle_paths, settle)
        except Exception as e:
            ui.undo.endBlock()
            ui.undo.undo()
            self._settle(comps)
            self._say('REFUSED - %s' % e)
            return
        ui.undo.endBlock()
        self._settle(touched)
        groups = ['%s -> %s' % pair for pair in announced]
        if groups:
            self._say('renamed ' + ', '.join(groups[:8])
                      + (' ...' if len(groups) > 8 else ''))

    def _rename_plan(self, lvl):
        """[(old group name, new group name)] for one page, or an error string.

        Nothing is written. A parameter whose bind chain no longer reaches a
        descendant is left alone.
        """
        page = next((p for p in lvl.customPages
                     if p.name == self._pagename), None)
        if page is None:
            return [], None
        pairs, claimed = [], {}
        for g in page.parGroups:
            p0 = g[0]
            if p0.style == 'Header':
                continue
            source, steps = self._chain_source(p0)
            if steps < 1 or not source.owner.path.startswith(lvl.path + '/'):
                continue
            # A size-1 custom par bound to one axis of a larger tuplet is
            # named from that axis. A whole group keeps tupletName.
            solo = (len(tuple(g[0].tuplet)) == 1 and len(source.tuplet) > 1)
            stem = source.name if solo else source.tupletName
            new = par_name(*rel_parts(lvl, source.owner), stem)
            if new == g.name:
                continue
            if new in claimed:
                return [], ("%s: '%s' and '%s' would both become '%s'"
                            % (lvl.path, claimed[new], g.name, new))
            claimed[new] = g.name
            pairs.append((g.name, new))
        moving = {old for old, _new in pairs}
        for _old, new in pairs:
            if lvl.parGroup[new] is not None and new not in moving:
                return [], "%s already has '%s'" % (lvl.path, new)
        return pairs, None

    def _on_interface(self, par):
        page = par.page
        return page is not None and page.name == self._pagename

    def _chain_source(self, member):
        """Follow the promote binds down to the original parameter.

        Returns (parameter, steps). steps == 0 means there is nothing to
        rename: the bind does not reach a parameter outside the Interface
        page. A bind that continues past that original parameter belongs to
        whatever the user attached there, and does not change the name.
        """
        cur, steps, seen = member, 0, set()
        while steps < 32:
            ident = (cur.owner.path, cur.name)
            if ident in seen:
                break
            seen.add(ident)
            if steps > 0 and not self._on_interface(cur):
                break
            slaves = [ref for ref in cur.bindReferences
                      if ref.owner.parent() is cur.owner
                      and ref.bindExpr == 'parent().par.' + cur.name]
            if len(slaves) != 1:
                break
            cur = slaves[0]
            steps += 1
        if self._on_interface(cur):
            return cur, 0
        return cur, steps

    def _rename_groups(self, comp, pairs):
        """Rename each group, rewriting slave binds immediately.

        Every group goes through a temporary name so two groups can exchange
        names. Returns the original-to-final tokens, and the operators whose
        binds were rewritten.
        """
        if not pairs:
            return [], []
        finals = {new for _old, new in pairs}
        originals = [(old, new, [p.name for p in comp.parGroup[old]])
                     for old, new in pairs]
        staged, owners, n = [], [], 0
        for old, new, old_members in originals:
            n += 1
            tmp = self._temp_name(comp, n, finals)
            owners += self._rename_one(comp, old, tmp)
            staged.append((tmp, new, old, old_members))
        tokens = []
        for tmp, new, old, old_members in staged:
            owners += self._rename_one(comp, tmp, new)
            g = comp.parGroup[new]
            tokens.append((old, new))
            for old_member, member in zip(old_members, g):
                if old_member != member.name:
                    tokens.append((old_member, member.name))
        return tokens, owners

    @staticmethod
    def _temp_name(comp, n, reserved):
        while True:
            name = 'Tmp%d' % n
            if comp.parGroup[name] is None and name not in reserved:
                return name
            n += 1

    def _rename_one(self, comp, old, new):
        if old == new:
            return []
        g = comp.parGroup[old]
        if g is None:
            raise PromoteError("%s has no '%s' to rename" % (comp.path, old))
        old_members = [p.name for p in g]
        # Drop the bind before the name changes. TouchDesigner evaluates the
        # old expression the moment baseName is set, and that failed lookup
        # stays on the operator until something cooks it again.
        slaves = []
        for i, member in enumerate(g):
            held = []
            for ref in list(member.bindReferences):
                if ref.mode != ParMode.BIND:
                    continue
                held.append((ref, ref.bindExpr or ''))
                self._release_bind(ref)
            slaves.append((i, held))
        g.baseName = new
        g2 = comp.parGroup[new]
        if g2 is None:
            raise PromoteError("rename of %s.%s failed" % (comp.path, old))
        owners = []
        for i, held in slaves:
            new_member = g2[i].name
            old_member = old_members[i]
            for ref, expr in held:
                if expr == 'parent().par.' + old_member:
                    updated = 'parent().par.' + new_member
                else:
                    updated = self._swap_tokens(expr, [(old_member, new_member)])
                ref.bindExpr = updated
                ref.mode = ParMode.BIND
                owners.append(ref.owner)
                if ref.bindMaster is None and not ref.isPulse:
                    raise PromoteError(
                        'bind of %s.%s did not resolve (%s)'
                        % (ref.owner.path, ref.name, ref.bindExpr))
        return owners

    def _rewrite_name_refs(self, tokens):
        """Point parameter expressions at the new names.

        DAT text and parexec watch-lists are left alone: those are not
        parameter expressions, and a blind edit there is worse than a stale name.
        """
        tokens = [(old, new) for old, new in tokens if old != new]
        owners = []
        if not tokens:
            return owners
        tokens.sort(key=lambda pair: -len(pair[0]))
        for top in self._root_comps():
            for o in [top] + list(top.findChildren()):
                for p in o.pars():
                    if p.mode == ParMode.EXPRESSION:
                        nxt = self._swap_tokens(p.expr, tokens)
                        if nxt != p.expr:
                            p.expr = nxt
                            owners.append(p.owner)
                    elif p.mode == ParMode.BIND:
                        nxt = self._swap_tokens(p.bindExpr, tokens)
                        if nxt != p.bindExpr:
                            p.bindExpr = nxt
                            owners.append(p.owner)
        return owners

    def _settle(self, ops):
        """Cook operators that logged a bind error during the rename."""
        seen = set()
        for o in ops:
            if o is None or o.path in seen:
                continue
            seen.add(o.path)
            if o.errors():
                o.cook(force=True)

    @staticmethod
    def _swap_tokens(expr, tokens):
        if not expr:
            return expr
        for old, new in tokens:
            expr = re.sub(
                r'(\.parGroup\.)' + re.escape(old) + r'(?![0-9A-Za-z])',
                lambda m, new=new: m.group(1) + new, expr)
            expr = re.sub(
                r'(\.par\.)' + re.escape(old) + r'(?![0-9A-Za-z])',
                lambda m, new=new: m.group(1) + new, expr)
            for attr in ('par', 'parGroup'):
                expr = expr.replace(".%s['%s']" % (attr, old),
                                    ".%s['%s']" % (attr, new))
                expr = expr.replace('.%s["%s"]' % (attr, old),
                                    '.%s["%s"]' % (attr, new))
        return expr

    def _children_topo(self, lvl):
        """Direct children of lvl in signal-flow order (Kahn, tie: x, name)."""
        kids = list(lvl.children)
        paths = {c.path for c in kids}
        up = {c.path: set() for c in kids}
        for c in kids:
            conns = list(c.inputConnectors)
            if c.isCOMP:
                conns += list(c.inputCOMPConnectors)
            for conn in conns:
                for cc in conn.connections:
                    if cc.owner.path in paths and cc.owner is not c:
                        up[c.path].add(cc.owner.path)
        key = {c.path: (c.nodeX, c.name) for c in kids}
        out, left = [], set(paths)
        while left:
            ready = [p for p in left if not (up[p] & left)]
            if not ready:                     # cycle: break it deterministically
                ready = list(left)
            nxt = min(ready, key=lambda p: key[p])
            out.append(op(nxt))
            left.discard(nxt)
        return out

    def _update_level(self, lvl):
        page = next((p for p in lvl.customPages
                     if p.name == self._pagename), None)
        if page is None:
            return
        present = {pg.name for pg in page.parGroups}
        # desired: ordered [(headerLabel, parName)]
        wanted = []
        for d in self._children_topo(lvl):
            wanted += self._entries_from_child(lvl, d, present)
        seq = []
        seen_pars, blocks = set(), {}
        for label, name in wanted:
            if name in seen_pars:
                continue
            seen_pars.add(name)
            blocks.setdefault(label, []).append(name)
        for label, names in blocks.items():
            hname = header_name(label)
            if lvl.par[hname] is None:
                page.appendHeader(hname, label=label)
            seq.append(hname)
            seq += names
        # orphans: keep their existing relative order after everything else
        known = set(seq)
        # pars whose source vanished stay where their old header put them
        # (after everything else); headers that head nothing are removed
        blocks_old, headerless, cur = [], [], None
        for pg in page.parGroups:
            is_header = pg[0].style == 'Header'
            if is_header:
                cur = None if pg.name in known else [pg, []]
                if cur:
                    blocks_old.append(cur)
            elif pg.name not in known:
                (cur[1] if cur else headerless).append(pg.name)
        for hg, names in blocks_old:
            if names:
                seq.append(hg.name)
                seq += names
            else:
                hg.destroy()
        seq += headerless
        if not seq:
            return
        page.sort(*seq)
        # The first parameter on the page does not open a section. Each later
        # header does, so a block is separated from the one above it.
        first = True
        for name in seq:
            p = lvl.par[name]
            if p is None:
                continue
            if p.style == 'Header':
                p.startSection = not first
            first = False

    @staticmethod
    def _promoted_name(slave, lvl):
        """Parameter on `lvl` that `slave` is bound to.

        Identity is the bind, not the script name. After an operator rename the
        name derived from the current path no longer matches the parameter
        created at promote time, and a name lookup would drop it out of the
        signal order.
        """
        master = slave.bindMaster
        if master is None or master.owner is not lvl:
            return None
        return master.parGroup.name

    @staticmethod
    def _fallback_names(child_name, par):
        """Names to try when the bind does not resolve.

        A whole group is stored under tupletName. One axis of that group is
        stored under the axis name. Try the group first; the two cannot both
        exist, because the group's member name is the axis name.
        """
        names = [par_name(child_name, par.tupletName)]
        if len(par.tuplet) > 1:
            member = par_name(child_name, par.name)
            if member not in names:
                names.append(member)
        return names

    def _entries_from_child(self, lvl, d, present):
        """[(headerLabel, levelParName)] contributed by direct child d."""
        out = []
        # d's own (non-Interface) parameters promoted straight to this level
        iface = d.customPages and next(
            (p for p in d.customPages if p.name == self._pagename), None)
        seen = set()
        for p in d.pars():
            if self._on_interface(p):
                continue
            name = self._promoted_name(p, lvl)
            if name is None:
                candidates = self._fallback_names(d.name, p)
            else:
                candidates = [name]
            for cand in candidates:
                if cand in seen or cand not in present:
                    continue
                seen.add(cand)
                out.append((d.name, cand))
                break
        # what flowed up through d's Interface page, in d's own order
        if iface:
            label = d.name
            for pg in iface.parGroups:
                if pg[0].style == 'Header':
                    label = d.name + '.' + pg[0].label
                    continue
                resolved = []
                for member in pg[0].tuplet:
                    name = self._promoted_name(member, lvl)
                    if name is None or name not in present or name in seen:
                        continue
                    seen.add(name)
                    resolved.append(name)
                if resolved:
                    for name in resolved:
                        out.append((label, name))
                    continue
                name = par_name(d.name, pg.name)
                if name in present and name not in seen:
                    seen.add(name)
                    out.append((label, name))
        return out

    # ======================================================================
    # who is managed
    # ======================================================================
    def _managed_comps(self):
        """COMPs that carry this plugin's page, as of this call."""
        name = self._pagename
        me = self.ownerComp.path
        found = []
        for top in self._root_comps():
            for c in [top] + list(top.findChildren()):
                if not c.isCOMP or c.path == me or c.path.startswith(me + '/'):
                    continue
                if any(pg.name == name for pg in c.customPages):
                    found.append(c)
        return found

    @staticmethod
    def _root_comps():
        """Top-level COMPs Update all may walk. A DAT at root has no children."""
        for top in op('/').children:
            if top.name in SKIP_ROOTS or not top.isCOMP:
                continue
            yield top

    # ======================================================================
    # install / uninstall (address bar and timeline track)
    # ======================================================================
    @staticmethod
    def _crumb_containers():
        found = []
        panebar = op('/ui/panes/panebar')
        if panebar is not None:
            found += [c.op('panenav/path') for c in panebar.children]
        tmpl = op('/ui/dialogs/panebar/panebar_default')
        if tmpl is not None:
            found.append(tmpl.op('panenav/path'))
        return [c for c in found if c is not None]

    @staticmethod
    def _timeline_pads():
        """The empty area to the right of the transport buttons.

        It fills the right side of the bottom bar. The ruler and the buttons
        sit on top of it, so a drop on them does not land here.
        """
        pad = op('/ui/dialogs/timeline/transportpanel')
        return [] if pad is None else [pad]

    def _bind_drop(self, comp, callbacks):
        # re-assigning the same path string is a no-op for TD, so after
        # the plugin was recreated the old (destroyed) DAT would stay
        # bound: clear first to force a fresh resolve
        comp.par.dragdropcallbacks = ''
        comp.par.dragdropcallbacks = callbacks
        comp.par.drop = 'usecallbacks'

    def Install(self):
        if not self.ownerComp.par.Active:
            return 0
        cb = self.ownerComp.op('dropCallbacks')
        n = 0
        for c in self._crumb_containers():
            self._bind_drop(c, cb)
            n += 1
        for c in self._timeline_pads():
            self._bind_drop(c, cb)
            n += 1
        return n

    def Uninstall(self):
        n = 0
        for c in self._crumb_containers():
            c.par.drop = 'legacy'
            c.par.dropscript = c.parent().op('drop')
            c.par.dragdropcallbacks = ''
            n += 1
        for c in self._timeline_pads():
            c.par.drop = 'dropparent'
            c.par.dragdropcallbacks = ''
            n += 1
        return n

    # ======================================================================
    # drop entry points
    # ======================================================================
    def OnTimelineDrop(self, items):
        """A parameter was dropped on the empty area of the bottom bar.

        A custom parameter is deleted even when it is not in a promote chain.
        In a chain, every master above it goes too, and the parameter directly
        below becomes a constant. A built-in parameter that is not in a chain
        is left alone.
        """
        pars = [i for i in items if isinstance(i, (Par, ParGroup))]
        if not pars:
            return
        try:
            removed = self.Unpromote(pars[0])
            if removed is None:
                dragged = pars[0]
                raise PromoteError('%s.%s is not a promote chain'
                                   % (dragged.owner.path, dragged.name))
        except PromoteError as e:
            self._say('REFUSED - %s' % e)

    def OnCrumbDrop(self, crumbs, items, cell):
        """Handle a drop onto the crumb container `crumbs`, hovered cell id."""
        pane = ui.panes[crumbs.path.split('/')[4]]
        pars = [i for i in items if isinstance(i, (Par, ParGroup))]
        if not pars:                       # reproduce stock crumb behaviour
            if len(items) == 1 and isinstance(items[0], OP):
                tgt = items[0] if items[0].isCOMP else items[0].parent()
                pane.owner = tgt
            return
        try:
            if cell < 0:
                raise PromoteError('drop onto a crumb of the address bar')
            names = [x for x in pane.owner.path.split('/') if x]
            if cell > 0 and cell % 2 == 0:
                raise PromoteError('drop onto a crumb name, not a separator')
            depth = (cell + 1) // 2
            dest = op('/' + '/'.join(names[:depth]))
            self.Promote(pars[0], dest)
        except PromoteError as e:
            self._say('REFUSED - %s' % e)
