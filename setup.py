"""copyright 2017 cisco systems

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

setup_tools file definition for cisco pyang plugins
"""
import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="pyang-plugins",
    version="0.2.0",
    description=("pyang plugins"),
    long_description=read('README.md'),
    packages=['plugins'],
    url="https://github.com/einarnn/pyang-plugins",
    author="Einar Nilsen-Nygaard",
    author_email="einarnn@gmail.com",
    license="Apache",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Telecommunications Industry",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
    ],
    install_requires=[
        'pyang>=1.7.3',
        'redisearch>=0.7.0',
    ],
    include_package_data=True,
    keywords=["yang", "pyang"],
    entry_points={
        'pyang.plugin': [
            'filter_pyang_plugin=plugins.filter:pyang_plugin_init',
            'strip_pyang_plugin=plugins.strip:pyang_plugin_init',
            'xpath_pyang_plugin=plugins.xpath:pyang_plugin_init',
            'redisearch_pyang_plugin=plugins.redisearch:pyang_plugin_init',
        ]
    }
)
