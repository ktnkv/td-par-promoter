# Promote

Promote is a TouchDesigner plugin that lifts a parameter up through its ancestor COMPs in one drag.

Exposing a control on a parent by hand means creating a custom parameter, copying its type, range, and menu, and binding it — then repeating that on every COMP in between. Promote does the whole chain at once.

## What it does

Drag a parameter onto an ancestor in the address bar. On every COMP from the owner's parent up to that ancestor, Promote creates a matching custom parameter, places it under a header, and binds the levels together:

- the top parameter is the master;
- each level below is bound to the parameter on its parent (`parent().par.<Name>`);
- the original parameter is the bottom of the chain.

A change on any level reaches the others. The result is ordinary custom parameters and binds: a saved project does not need the plugin to keep working.

Parameters land on a custom page (default name `Interface`), grouped under a header whose label is the relative path, for example `processing.transform1`. The first item on that page is a `Reorder` pulse.

## How to use

1. Drop `Promote.tox` into the project.
2. Leave **Active** on. While it is on, the address-bar hook is applied when the project starts.
3. Drag a parameter onto an ancestor's name in the address bar. Drop on the name, not on a `/` separator, and only onto an ancestor of the parameter's owner.
4. Open the custom page (`Pagename`, default `Interface`) on any COMP along the chain and edit the new parameter.
5. Pulse **Reorder** on a COMP, or **Reorderall** on the plugin, to sort that page by signal flow: children ordered by wires (then by node X, then by name), and within each child its own parameters first, then anything promoted through its page.
6. Turn **Active** off to restore the stock address-bar drop behavior. Do this before deleting the plugin. There is no cleanup when the component is deleted; with **Active** left on, crumb drops stay pointed at a missing callback until the next TouchDesigner start.

Dragging something that is not a parameter still navigates as usual: a COMP opens, any other operator opens its parent.

## Limitations

- **Ancestor only.** The drop target must be a COMP above the parameter's owner. A drop on the operator itself, a non-ancestor, a separator, or a non-COMP is refused and changes nothing.
- **Whole tuplet.** Dragging one member of a group (for example `tx`) promotes the whole group.
- **Not supported:** OP references (a relative path would resolve differently on each level), Python and sequence parameters, and parameters driven by an expression or an export.
- **Names are sanitized.** A custom name is built from the relative path and the parameter name: the first letter is capital, everything that is not `[a-z0-9]` is removed (`processing` / `transform1` / `rotate` becomes `Processingtransform1rotate`). If that name already exists and is not this chain, Promote refuses. It does not add a numeric suffix.
- **Repeating a promote is safe** when the chain is already in place. If the source was renamed, or it is already bound somewhere else, a second promote is refused. Existing binds keep working after a rename; **Reorder** will not follow the new operator name, because order is derived from the name.
- **Reorder is manual.** It runs for the levels touched by a promote, and when you pulse **Reorder** or **Reorderall**. Parameters whose source disappeared stay at the end of the page with their header; a header with nothing under it is removed.
- **The hook is reapplied on startup** while **Active** is on, because `/ui` is not stored in the `.toe`.
