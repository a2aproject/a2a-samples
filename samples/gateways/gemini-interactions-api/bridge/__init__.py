# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A2A-to-Vertex Interactions bridge package.

This module monkey-patches ``FieldDescriptor.label`` because a2a-sdk's
``proto_utils`` still references the attribute that protobuf>=7 removed.
The patch covers whichever FieldDescriptor implementation (upb or
pure-python) is active at import time.

TODO: Remove the patch when a2a-sdk no longer references
``FieldDescriptor.label``.
"""

from a2a import types as _a2a_types


# protobuf FieldDescriptor label enum values (descriptor.proto).
_LABEL_OPTIONAL = 1
_LABEL_REPEATED = 3

_fd_type = type(_a2a_types.Part.DESCRIPTOR.fields[0])
if not hasattr(_fd_type, 'label'):
    _fd_type.label = property(lambda self: _LABEL_REPEATED if self.is_repeated else _LABEL_OPTIONAL)

del _a2a_types, _fd_type
