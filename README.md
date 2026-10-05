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
- **Repeating a promote is safe** when the chain is already in place. If the source was renamed, or it is already bound somewhere else, a second promote is refused. Existing binds keep working after a rename; **Reorder** will not follow the new operator name, because order is derived from the name.
- **Reorder is manual.** It runs for the levels touched by a promote, and when you pulse **Reorder** or **Reorderall**. Parameters whose source disappeared stay at the end of the page with their header; a header with nothing under it is removed.

