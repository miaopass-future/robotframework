#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os

from robot.errors import DataError
from robot.utils import JYTHON, JAVA_VERSION, get_error_message

from .robotbuilder import LibraryDocBuilder, ResourceDocBuilder
from .specbuilder import SpecDocBuilder
from .jsonbuilder import JsonDocBuilder
if JYTHON:
    if JAVA_VERSION < (1, 9):
        from .javabuilder import JavaDocBuilder
    else:
        from .java9builder import JavaDocBuilder
else:
    def JavaDocBuilder():
        raise DataError('Documenting Java test libraries requires Jython.')


RESOURCE_EXTENSIONS = ('resource', 'robot', 'txt', 'tsv', 'rst', 'rest')
SPEC_EXTENSIONS = ('xml', 'libspec')


def LibraryDocumentation(library_or_resource, name=None, version=None,
                         doc_format=None):
    builder = DocumentationBuilder(library_or_resource)
    libdoc = _build(builder, library_or_resource)
    if name:
        libdoc.name = name
    if version:
        libdoc.version = version
    if doc_format:
        libdoc.doc_format = doc_format
    return libdoc


def _build(builder, source):
    try:
        return builder.build(source)
    except DataError:
        # Possible resource file in PYTHONPATH. Something like `xxx.resource` that
        # did not exist has been considered to be a library earlier, now we try to
        # parse it as a resource file.
        if (isinstance(builder, LibraryDocBuilder)
                and not os.path.exists(source)
                and _get_extension(source) in RESOURCE_EXTENSIONS):
            return _build(ResourceDocBuilder(), source)
        raise
    except:
        raise DataError("Building library '%s' failed: %s"
                        % (source, get_error_message()))


def _get_extension(source):
    return os.path.splitext(source)[1][1:].lower()


def DocumentationBuilder(library_or_resource):
    if os.path.exists(library_or_resource):
        extension = _get_extension(library_or_resource)
        if extension in RESOURCE_EXTENSIONS:
            return ResourceDocBuilder()
        if extension in SPEC_EXTENSIONS:
            return SpecDocBuilder()
        if extension == 'json':
            return JsonDocBuilder()
        if extension == 'java':
            return JavaDocBuilder()
    return LibraryDocBuilder()
