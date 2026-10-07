# Execute DAT: (re)apply the address-bar and timeline hooks. /ui is not saved in the .toe,
# so this runs on every project start and when the plugin is loaded.
# Install() itself does nothing while Active is off.
#
# There is no Execute DAT callback for "being deleted". To remove the plugin
# cleanly turn `Active` off first; otherwise the stock crumb behaviour comes
# back at the next TouchDesigner start (/ui is rebuilt then).


def onStart():
    # the UI panes are built a little after onStart
    run('parent().Install()', delayFrames=30, fromOP=me)


def onCreate():
    parent().Install()
