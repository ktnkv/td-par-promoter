# Promote

Promote is a TouchDesigner plugin that lifts a parameter up through its ancestor COMPs in one drag.

By hand you open Customize Component, drag the parameter in, place it, and add a header — then repeat that on every COMP up the chain. All that clicking is tedious. Promote does the whole chain at once.

## How to use

1. Drop `Promote.tox` into the project.
2. Leave **Active** on. While it is on, the address-bar hook is applied.
3. Drag a parameter onto an ancestor's name in the address bar.

Done. The chain is in place, and the parameters follow the signal order through the network.

## How it works

A drop builds a chain from the parameter owner's parent up to the ancestor it was dropped on. On each of those COMPs, Promote creates a matching custom parameter under a header and binds that level to the one below:

- the top parameter is the master;
- each level below is bound to the parameter on its parent (`parent().par.<Name>`);
- the original parameter is the bottom of the chain.

A change on any level reaches the others. These are ordinary custom parameters and binds, so a saved project does not need the plugin.

The new parameters sit on a custom page (default name `Interface`), under a header labeled with the relative path, for example `processing.transform1`.

## Limitations

- **Ancestor only.** The drop target must be a COMP above the parameter's owner. A drop on the operator itself, a non-ancestor, a separator, or a non-COMP is refused and changes nothing.
- **Whole tuplet.** Dragging one member of a group (for example `tx`) promotes the whole group.
- **Not supported:** OP references (a relative path would resolve differently on each level), Python and sequence parameters, and parameters driven by an expression or an export.
- **Repeating a promote is safe** when the chain is already in place. A parameter that is already bound somewhere else is refused, and nothing changes.
- **Names follow the operators when you Update.** The script name is taken from the path at the moment of the promote. After you rename an operator, pulse **Update Interface** (or **Update all**): the script name, the header, and the binds in the chain are rewritten from the current path. A parameter expression that still contains the old name (`.par.Oldname`, `.parGroup.Oldname`, or the same name in brackets) is rewritten as well. A name written in a DAT, or in a Parameter Execute DAT's parameter list, is left for you to update. If the new name is already used by a parameter that is not part of this update, the whole update is refused and the page stays as it was. After that update, promoting the same parameter again changes nothing.
- **Update is manual.** It runs for the levels touched by a promote, and when you pulse **Update Interface** on a level or **Update all** on the plugin. Parameters whose source disappeared stay at the end of the page with their header; a header with nothing under it is removed.

