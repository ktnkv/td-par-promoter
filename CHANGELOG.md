# Changelog

## 0.6.3

### Fixed

- An axis that stays after another axis of a numbered group is removed keeps the label of the original parameter, for example `Resolution W`. It used to get the script name in its label, like `Resolution Rectresolution1`. One axis promoted from a numbered custom group is labeled by its number, like `Count 2`.

## 0.6.2

### Added

- `.tox Save Build` on the About page. Export has to set it, and its default, to `app.build` before saving the tox. The value is the TouchDesigner build the file was exported from.

### Changed

- Promote is a tool. Text that called it a plugin now says tool.

## 0.6.1

### Fixed

- Promoting an RGBA parameter keeps that style and however many channels it currently has. A three-channel color is no longer turned into an XYZW vector. Dragging one channel of a color still promotes that channel alone.

## 0.6.0

### Changed

- Dropping a custom parameter onto the empty area at the bottom right of the timeline deletes that parameter even when it is not part of a promote chain. A built-in parameter that is not in a chain is still left alone. A bind that is not the single chain link still refuses the drop.

## 0.5.0

### Changed

- Promoting an axis or a group finishes a chain that already exists in the other shape. Dragging one axis pulls that axis out of a custom group on every level up to the drop, and the axes that remain stay together. Dragging the group builds the whole group and removes axes of that group that were promoted on their own. The header is the path to the source operator, including when the drag starts from an axis that was already promoted.

### Fixed

- Update all no longer stops on a non-COMP at the project root. Renaming a parameter clears the bind expression before the name changes, so a failed lookup is not left on the operator.

## 0.4.0

### Changed

- Dragging one parameter of a group promotes or removes only that parameter. Dragging the group promotes or removes the whole group. Removing one axis of a group that was promoted together leaves the other axes in place. Dropping the group also removes axes that were promoted one by one.

## 0.3.0

### Added

- Drop a promoted parameter onto the empty area at the bottom right of the timeline to delete that parameter and every master above it. The parameter directly below becomes a constant and keeps its value; anything bound below that stays as it was. A built-in parameter cannot be deleted, so dropping it removes only the masters above and the built-in itself becomes the constant. A parameter that is not part of a promote chain is left alone. If there is a bind besides the single chain link, the drop changes nothing.

## 0.2.0

### Changed

- Update all finds every COMP that has the tool's page at the moment it is pulsed, and re-sorts from the deepest one up. The tool no longer keeps a tag on those COMPs or a list of their paths.

### Removed

- The Update Interface pulse on each promoted page. Update all on the tool is how a page is re-sorted.
- The `promote` tag and the parameter execute that watched it.

## 0.1.0

### Changed

- Update rewrites a promoted parameter's script name from the current operator path, and rewrites the binds in that chain to match. Parameter expressions that name the old parameter are updated. Text in DATs and Parameter Execute watch lists is not. If the new name is already taken, the update changes nothing.

## 0.0.1

### Added

- Initial release.
