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

"""Serve the bridge with uvicorn (``python -m bridge``)."""

from __future__ import annotations

import logging

import uvicorn

from bridge import app, config


def main() -> None:
    """Configures logging and runs the bridge server with uvicorn."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
    logging.getLogger('httpx').setLevel(logging.WARNING)

    # Required fields are sourced from the environment by pydantic-settings.
    settings = config.Settings()  # type: ignore[call-arg]
    uvicorn.run(app.build_app(settings), host='0.0.0.0', port=settings.port)  # noqa: S104


if __name__ == '__main__':
    main()
