# Promote

Promote is a TouchDesigner plugin that lifts a parameter up through its ancestor COMPs in one drag.

By hand you open Customize Component, drag the parameter in, place it, and add a header — then repeat that on every COMP up the chain. All that clicking is tedious. Promote does the whole chain at once.

## How to use

1. Drop `Promote.tox` into the project.
2. Leave **Active** on. While it is on, the address-bar hook is applied.
3. Drag a parameter onto an ancestor's name in the address bar. The chain is in place, and the parameters follow the signal order through the network.
4. To remove it, drag the parameter onto the empty area at the bottom right of the timeline, to the right of the transport buttons. That parameter and every master above it are deleted. The one directly below becomes a constant and keeps its value.

## How it works

A drop builds a chain from the parameter owner's parent up to the ancestor it was dropped on. On each of those COMPs, Promote creates a matching custom parameter under a header and binds that level to the one below:

- the top parameter is the master;
- each level below is bound to the parameter on its parent (`parent().par.<Name>`);
- the original parameter is the bottom of the chain.

A change on any level reaches the others. These are ordinary custom parameters and binds, so a saved project does not need the plugin.

The new parameters sit on a custom page (default name `Interface`), under a header labeled with the relative path, for example `processing.transform1`.

## Limitations

- **Ancestor only.** The drop target must be a COMP above the parameter's owner. A drop on the operator itself, a non-ancestor, a separator, or a non-COMP is refused and changes nothing.
- **One parameter or the whole group.** Dragging one member of a group promotes or removes only that member. Dragging the group label promotes or removes every member, including axes that were promoted one by one. An axis removed from a group that was promoted together leaves the other axes in place.
- **Not supported:** OP references (a relative path would resolve differently on each level), Python and sequence parameters, and parameters driven by an expression or an export.
- **Repeating a promote is safe** when the chain is already in place. A parameter that is already bound somewhere else is refused, and nothing changes.
- **Names follow the operators when you Update.** The script name is taken from the path at the moment of the promote. After you rename an operator, pulse **Update all** on the plugin: the script name, the header, and the binds in the chain are rewritten from the current path. A parameter expression that still contains the old name (`.par.Oldname`, `.parGroup.Oldname`, or the same name in brackets) is rewritten as well. A name written in a DAT, or in a Parameter Execute DAT's parameter list, is left for you to update. If the new name is already used by a parameter that is not part of this update, the whole update is refused and the page stays as it was. After that update, promoting the same parameter again changes nothing.
- **Update is manual.** Pulsing **Update all** re-sorts every COMP that has the plugin's page, from the deepest one up. A promote also re-sorts the levels it just touched. Parameters whose source disappeared stay at the end of the page with their header; a header with nothing under it is removed.

