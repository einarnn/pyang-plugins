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
from os import path
from pip.req import parse_requirements
from setuptools import find_packages
from setuptools import setup
from codecs import open

thisdir = path.abspath(path.dirname(__file__))
pip_reqs = parse_requirements(path.join(thisdir, "requirements.txt"),
                              session=False)
inst_reqs = [str(ir.req) for ir in pip_reqs]

setup(
    name="cisco-pyang-plugins",
    version="0.1.0",
    description=("Cisco pyang plugins"),
    url="https://github3.cisco.com/einarnn/pyang-plugins",
    author="Einar Nilsen-Nygaard",
    author_email="einarnn@cisco.com",
    license="Apache",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Telecommunications Industry",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2 :: Only"
    ],
    packages=find_packages(),
    install_requires=inst_reqs,
    include_package_data=True,
    keywords=["yang", "pyang", "cisco"],
    zip_safe=False,
    data_files=[ ('lib/python2.7/site-packages/pyang/plugins', ['pyang/plugins/xpath.py']) ]
)
