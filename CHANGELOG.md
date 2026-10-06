# Changelog

## 0.1.0

### Changed

- Update rewrites a promoted parameter's script name from the current operator path, and rewrites the binds in that chain to match. Parameter expressions that name the old parameter are updated. Text in DATs and Parameter Execute watch lists is not. If the new name is already taken, the update changes nothing.

## 0.0.1

### Added

- Initial release. Drag a parameter onto an ancestor crumb to promote it up the COMP hierarchy as a bound custom-parameter chain.
