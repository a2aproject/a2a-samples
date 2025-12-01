import os
import re

from typing import Any

from braintrust import init_logger, set_masking_function
from braintrust.wrappers.litellm import patch_litellm
from dotenv import load_dotenv


patch_litellm()

load_dotenv()


def mask_sensitive_data(data: Any) -> Any:
    """Mask sensitive data."""
    if isinstance(data, str):
        return re.sub(
            r'\b(api[_-]?key|password|token)[\s:=]+\S+',
            r'\1: [REDACTED]',
            data,
            flags=re.IGNORECASE,
        )

    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if re.match(
                r'^(api[_-]?key|password|secret|token|auth|credential)$',
                key,
                re.IGNORECASE,
            ):
                masked[key] = '[REDACTED]'
            else:
                masked[key] = mask_sensitive_data(value)
        return masked

    if isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]

    return data


set_masking_function(mask_sensitive_data)

logger = init_logger(
    project='My Project', api_key=os.getenv('BRAINTRUST_API_KEY')
)
