# Drag/drop callbacks shared by the address-bar crumbs and the timeline track.
#
# Crumbs: tableCOMP `panenav/path`. celloverid 0 is the root `/`, odd ids are
# names, even ids >= 2 are separators.
# Timeline: containerCOMP `transportpanel`, the empty area on the right of the
# bottom bar (beside the transport buttons, under the frame ruler). Only a
# parameter drag is accepted there, so the ruler and the buttons stay as they are.


def onHoverStartGetAccept(comp, info):
    if _timeline(comp):
        return _has_parameter(info)
    return True


def onHoverEnd(comp, info):
    pass


def onDropGetResults(comp, info):
    items = info['dragItems']
    if _timeline(comp):
        parent().OnTimelineDrop(items)
    else:
        parent().OnCrumbDrop(comp, items, int(comp.panel.celloverid))
    return {}


def _timeline(comp):
    return comp.path.endswith('/timeline/transportpanel')


def _has_parameter(info):
    items = info.get('dragItems') if info else None
    if not items:
        return False
    return any(isinstance(item, (Par, ParGroup)) for item in items)
