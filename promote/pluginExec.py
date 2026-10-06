# Parameter Execute DAT on the plugin COMP.
# Active turning on calls Install, turning off calls Uninstall.
# The Updateall pulse calls the extension method of the same name.


def onValueChange(par, prev):
    if par.name != 'Active':
        return
    if par.eval():
        parent().Install()
    else:
        parent().Uninstall()


def onPulse(par):
    getattr(parent(), par.name)()
