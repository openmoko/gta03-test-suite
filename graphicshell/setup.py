#!/usr/bin/env python
# -*- coding: utf-8 -*-
# COPYRIGHT: Openmoko Inc. 2008
# LICENSE: GPL Version 2 or later
# DESCRIPTION: Simple frame and dialog box framework
# AUTHOR: Christopher Hall <hsw@openmoko.com>

from distutils.core import setup

setup(name='GraphicTestShell',
      version='1.0',
      description='Graphic Test Shell',
      long_description='A Graphic Test Shell to administer running of test scripts',
      author='Christopher Hall',
      author_email='hsw@openmoko.com',
      license='GPLv2 or Later',
      #url='http://www.openmoko.com/whatever/',
      #download_url='http://www.openmoko.com/somewhere/',
      packages=['GraphicTestShell', 'SimpleFramework'],
      scripts=['scripts/gts'],
      data_files=[
        ('/etc', ['configuration/directfbrc']),
        ('/etc/init.d', ['configuration/gts']),
        ],
      classifiers=[
          'Development Status :: Beta',
          'Environment :: Frame buffer',
          'Environment :: X11',
          'Intended Audience :: End Users',
          'Intended Audience :: Developers',
          'Intended Audience :: Production Test',
          'License :: OSI Approved :: GPLv2 or Later',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Topic :: Hardware :: Testing',
          ],
     )
