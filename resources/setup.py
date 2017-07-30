#!/usr/bin/env python

from distutils.core import setup
import subprocess

setup(  name='itunes-remote-applet',
        version='1.0-beta-1',
        description='iTunes remote control applet for Ubuntu',
        author='Jake Pezaro',
        author_email='jake.pezaro@gmail.com',
        py_modules=[],
        scripts=['src/itunes-remote-applet.py'],
        data_files=[] )

'''
            ('/usr/share/applications', ['data/gm-notify.desktop']),
                    ('/usr/share/applications', ['data/gm-notify-config.desktop']),
                    ('/usr/share/gm-notify', ['data/checking.gif']),
                    ('/usr/share/gm-notify', ['gm-config.glade']),
                    ('/etc/gconf/schemas', ['data/gm-notify.schemas']),
                    ('/usr/share/locale/da/LC_MESSAGES', ['po/da/gm-notify.mo']),
                    ('/usr/share/locale/de/LC_MESSAGES', ['po/de/gm-notify.mo']),
                    ('/usr/share/locale/ca/LC_MESSAGES', ['po/ca/gm-notify.mo']),
                    ('/usr/share/locale/el/LC_MESSAGES', ['po/el/gm-notify.mo']),
                    ('/usr/share/locale/es/LC_MESSAGES', ['po/es/gm-notify.mo']),
                    ('/usr/share/locale/fr/LC_MESSAGES', ['po/fr/gm-notify.mo']),
                    ('/usr/share/locale/he/LC_MESSAGES', ['po/he/gm-notify.mo']),
                    ('/usr/share/locale/hu/LC_MESSAGES', ['po/hu/gm-notify.mo']),
                    ('/usr/share/locale/it/LC_MESSAGES', ['po/it/gm-notify.mo']),
                    ('/usr/share/locale/nl/LC_MESSAGES', ['po/nl/gm-notify.mo']),
                    ('/usr/share/locale/pl/LC_MESSAGES', ['po/pl/gm-notify.mo']),
                    ('/usr/share/locale/pt/LC_MESSAGES', ['po/pt/gm-notify.mo']),
                    ('/usr/share/locale/pt_BR/LC_MESSAGES', ['po/pt_BR/gm-notify.mo']),
                    ('/usr/share/locale/ro/LC_MESSAGES', ['po/ro/gm-notify.mo']),
                    ('/usr/share/locale/ru/LC_MESSAGES', ['po/ru/gm-notify.mo']),
                    ('/usr/share/locale/sk/LC_MESSAGES', ['po/sk/gm-notify.mo']),
                    ('/usr/share/locale/sl/LC_MESSAGES', ['po/sl/gm-notify.mo']),] )
'''
