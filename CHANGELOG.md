# Changelog

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
