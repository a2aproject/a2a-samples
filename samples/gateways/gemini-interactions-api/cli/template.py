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

"""Upload the local ``agent-template/`` tree to a GCS bucket."""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

import google.cloud.storage as gcs


if TYPE_CHECKING:
    import pathlib


logger = logging.getLogger(__name__)


def sync(bucket: str, src: pathlib.Path, prefix: str = 'agent-template') -> int:
    """Uploads every file under *src* to ``gs://{bucket}/{prefix}/``.

    Returns the number of objects written.
    """
    client = gcs.Client()
    gcs_bucket = client.bucket(bucket)
    count = 0
    for path in sorted(src.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(src).as_posix()
        blob_name = f'{prefix}/{rel}'
        gcs_bucket.blob(blob_name).upload_from_filename(path)
        logger.info('uploaded gs://%s/%s', bucket, blob_name)
        count += 1
    return count
