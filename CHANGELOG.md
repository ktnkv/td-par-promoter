# Changelog

## 0.4.0

### Changed

- Dragging one parameter of a group promotes or removes only that parameter. Dragging the group promotes or removes the whole group. Removing one axis of a group that was promoted together leaves the other axes in place. Dropping the group also removes axes that were promoted one by one.

## 0.3.0

### Added

- Drop a promoted parameter onto the empty area at the bottom right of the timeline to delete that parameter and every master above it. The parameter directly below becomes a constant and keeps its value; anything bound below that stays as it was. A built-in parameter cannot be deleted, so dropping it removes only the masters above and the built-in itself becomes the constant. A parameter that is not part of a promote chain is left alone. If there is a bind besides the single chain link, the drop changes nothing.

## 0.2.0

### Changed

- Update all finds every COMP that has the plugin's page at the moment it is pulsed, and re-sorts from the deepest one up. The plugin no longer keeps a tag on those COMPs or a list of their paths.

### Removed

- The Update Interface pulse on each promoted page. Update all on the plugin is how a page is re-sorted.
- The `promote` tag and the parameter execute that watched it.

## 0.1.0

### Changed

- Update rewrites a promoted parameter's script name from the current operator path, and rewrites the binds in that chain to match. Parameter expressions that name the old parameter are updated. Text in DATs and Parameter Execute watch lists is not. If the new name is already taken, the update changes nothing.

## 0.0.1

### Added

- Initial release.
