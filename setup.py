import setuptools
from os import path

this_directory = path.abspath(path.dirname(__file__))

with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
  long_description = f.read()

setuptools.setup(
    name='pima',
    version='0.7.2.8',
    description='Interface for negotiation with PIMA Hunter Pro alarms.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/deiger/Alarm',
    author='Dror Eiger',
    author_email='droreiger@gmail.com',
    license='GPL 3.0',
    packages=setuptools.find_packages(),
    install_requires=['crcmod', 'paho-mqtt==1.6.1', 'pyserial'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Topic :: Home Automation',
    ],
)
