import asyncio
import logging
import os
import time
import uuid

from collections.abc import AsyncIterable
from typing import Any
from urllib.parse import urlparse

import google.auth

from google import genai
from google.cloud import storage
from google.genai import types as genai_types


logger = logging.getLogger(__name__)


class VideoGenerationAgent:
    """An agent that generates video from a text prompt using VEO,
    providing periodic updates and a final GCS URL for the video.
    """

    SUPPORTED_INPUT_CONTENT_TYPES = ['text', 'text/plain']
    SUPPORTED_OUTPUT_CONTENT_TYPES = ['text/plain', 'video/mp4']

    VEO_MODEL_NAME = os.getenv('VEO_MODEL_NAME', 'veo-2.0-generate-001')
    VEO_POLLING_INTERVAL_SECONDS = int(
        os.getenv('VEO_POLLING_INTERVAL_SECONDS', '5')
    )
    VEO_SIMULATED_TOTAL_GENERATION_TIME_SECONDS = int(
        os.getenv('VEO_SIMULATED_TOTAL_GENERATION_TIME_SECONDS', '120')
    )  # 2 minutes for simulated progress
    VEO_DEFAULT_PERSON_GENERATION = 'dont_allow'
    VEO_DEFAULT_ASPECT_RATIO = '16:9'

    GCS_BUCKET_NAME_ENV_VAR = 'VIDEO_GEN_GCS_BUCKET'
    SIGNED_URL_EXPIRATION_SECONDS = 3600 * 48
    SIGNER_SERVICE_ACCOUNT_EMAIL_ENV_VAR = 'SIGNER_SERVICE_ACCOUNT_EMAIL'

    def __init__(self):
        logger.info('Initializing VideoGenerationAgent...')
        try:
            self.genai_client = genai.Client()
            logger.info('Google GenAI client initialized.')
        except Exception as e:
            logger.error(f'Failed to initialize Google GenAI client: {e}')
            self.genai_client = None
            raise

        self.gcs_bucket_name = os.getenv(self.GCS_BUCKET_NAME_ENV_VAR)
        if not self.gcs_bucket_name:
            logger.error(
                f'{self.GCS_BUCKET_NAME_ENV_VAR} environment variable not set. '
                'Video upload to GCS will not be possible.'
            )
            raise
        if not storage:
            logger.error(
                'google-cloud-storage library not found, but GCS bucket is set. '
                'Video upload to GCS will fail. Please install google-cloud-storage.'
            )
            raise
        try:
            self.credentials, self.project_id = google.auth.default(
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            logger.info('Successfully obtained ADC for GCS.')
            self.storage_client = storage.Client(
                credentials=self.credentials, project=self.project_id
            )
            logger.info('Google Cloud Storage client initialized.')
        except google.auth.exceptions.DefaultCredentialsError:
            logger.error(
                'Could not get Application Default Credentials for GCS. '
                "Please run 'gcloud auth application-default login' or set GOOGLE_APPLICATION_CREDENTIALS."
            )
            raise
        except Exception as e:
            logger.error(
                f'Failed to initialize Google Cloud Storage client: {e}'
            )
            raise

        sa_email_from_env = os.getenv(self.SIGNER_SERVICE_ACCOUNT_EMAIL_ENV_VAR)
        self.signer_service_account_email = (
            sa_email_from_env.strip('\'"') if sa_email_from_env else None
        )
        if self.signer_service_account_email:
            logger.info(
                f"Will use service account '{self.signer_service_account_email}' for signing GCS URLs."
            )
        else:
            logger.info(
                'No SIGNER_SERVICE_ACCOUNT_EMAIL set. Will use ambient gcloud credentials for signing GCS URLs.'
            )

        logger.info('VideoGenerationAgent initialized.')

    async def _generate_signed_url(
        self, blob_name: str, bucket_name: str, expiration_seconds: int
    ) -> str:
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        try:
            signed_url = blob.generate_signed_url(
                version='v4',
                expiration=expiration_seconds,
                method='GET',
                service_account_email=self.signer_service_account_email,  # None if not set, uses ambient creds
            )
            logger.info(
                f'Successfully generated signed URL for gs://{bucket_name}/{blob_name}'
            )
            return signed_url
        except Exception as e:
            logger.error(
                f'Error generating signed URL for gs://{bucket_name}/{blob_name}: {e}. '
                f"Check permissions (e.g., 'Service Account Token Creator' if using impersonation). "
                f'Falling back to GCS URI.'
            )
            return f'gs://{bucket_name}/{blob_name}'

    async def stream(
        self, prompt: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """Handles streaming requests for video generation.
        Yields progress updates and the final video URL.
        `session_id` is the A2A Task ID, used here for logging and unique naming.
        """
        logger.info(
            f"VideoGenerationAgent stream started for session_id: {session_id}, prompt: '{prompt}'"
        )

        yield {
            'is_task_complete': False,
            'updates': f"Received prompt: '{prompt}'. Starting VEO video generation.",
            'progress_percent': 0,
        }

        start_time = time.monotonic()
        operation_kicked_off = False
        veo_operation_name_for_reporting = 'N/A'
        try:
            logger.info(
                f'[{session_id}] Calling VEO with model: {self.VEO_MODEL_NAME}'
            )
            # Dynamically construct the output GCS URI for VEO
            veo_output_subpath = (
                f'{session_id}/veo_direct_output/{uuid.uuid4()}'
            )
            dynamic_output_gcs_uri = f'gs://{self.gcs_bucket_name}/{veo_output_subpath}/'  # Use configured bucket
            logger.info(
                f'[{session_id}] VEO will output to: {dynamic_output_gcs_uri}'
            )

            veo_operation = await asyncio.to_thread(
                self.genai_client.models.generate_videos,
                model=self.VEO_MODEL_NAME,
                prompt=prompt,
                config=genai_types.GenerateVideosConfig(
                    person_generation=self.VEO_DEFAULT_PERSON_GENERATION,
                    aspect_ratio=self.VEO_DEFAULT_ASPECT_RATIO,
                    output_gcs_uri=dynamic_output_gcs_uri,  # Pass the dynamic URI to VEO
                ),
            )
            if hasattr(veo_operation, 'name') and veo_operation.name:
                veo_operation_name_for_reporting = veo_operation.name
            else:
                logger.warning(
                    f"[{session_id}] Initial VEO operation object lacks a 'name' attribute or it's empty. Object: {str(veo_operation)[:200]}"
                )

            operation_kicked_off = True
            logger.info(
                f'[{session_id}] VEO operation started: {veo_operation_name_for_reporting}'
            )
            yield {
                'is_task_complete': False,
                'updates': f"VEO operation '{veo_operation_name_for_reporting}' started. Polling for completion...",
                'progress_percent': 5,  # Small initial progress
            }

            while True:
                if not hasattr(veo_operation, 'done'):
                    error_msg = f"[{session_id}] VEO operation variable is not a valid operation object before 'done' check. Type: {type(veo_operation)}, Value: {str(veo_operation)[:200]}"
                    logger.error(error_msg)
                    raise TypeError(error_msg)

                if veo_operation.done:
                    break  # Exit polling loop

                await asyncio.sleep(self.VEO_POLLING_INTERVAL_SECONDS)

                polled_data = await asyncio.to_thread(
                    self.genai_client.operations.get, veo_operation
                )

                if hasattr(polled_data, 'done') and hasattr(
                    polled_data, 'name'
                ):
                    veo_operation = polled_data
                    if veo_operation.name:
                        veo_operation_name_for_reporting = veo_operation.name
                else:
                    error_msg = f"[{session_id}] VEO polling for '{veo_operation_name_for_reporting}' returned unexpected data type: {type(polled_data)}. Value: {str(polled_data)[:200]}"
                    logger.error(error_msg)
                    # Yield an error and exit stream, as we can't continue polling
                    yield {
                        'is_task_complete': True,
                        'content': error_msg,
                        'final_message_text': 'Video generation polling encountered an API issue.',
                        'progress_percent': 100,
                    }
                    return

                elapsed_time = time.monotonic() - start_time
                simulated_progress = min(
                    int(
                        (
                            elapsed_time
                            / self.VEO_SIMULATED_TOTAL_GENERATION_TIME_SECONDS
                        )
                        * 100
                    ),
                    99,
                )
                current_progress = max(5, simulated_progress)
                yield {
                    'is_task_complete': False,
                    'updates': f'Video generation in progress (Operation: {veo_operation_name_for_reporting}). Simulated progress: {current_progress}%',
                    'progress_percent': current_progress,
                }

            logger.info(
                f'[{session_id}] VEO operation {veo_operation.name} is_done: {veo_operation.done}'
            )

            if veo_operation.error:
                error_message_detail = getattr(
                    veo_operation.error, 'message', str(veo_operation.error)
                )
                error_message = (
                    f'VEO video generation failed: {error_message_detail}'
                )
                logger.error(
                    f'[{session_id}] {error_message} (Raw error: {veo_operation.error})'
                )
                yield {
                    'is_task_complete': True,
                    'content': error_message,
                    'is_error': True,
                    'final_message_text': error_message,
                    'progress_percent': 100,
                }
                return

            logger.debug(
                f'[{session_id}] VEO operation completed. Response: {str(veo_operation.response)[:500]}...'
            )  # Log truncated response

            if (
                veo_operation.response
                and veo_operation.response.generated_videos
            ):
                # Assuming we use the first generated video
                generated_video_info = veo_operation.response.generated_videos[
                    0
                ]
                video_obj = (
                    generated_video_info.video
                )  # Assumption: video_obj is always present

                mime_type = 'video/mp4'

                mime_type = video_obj.mime_type or mime_type
                veo_provided_gcs_uri = video_obj.uri

                logger.info(
                    f'[{session_id}] Video object received. VEO GCS URI: {veo_provided_gcs_uri}, MimeType: {mime_type}'
                )

                if (
                    not veo_provided_gcs_uri
                    or not veo_provided_gcs_uri.startswith('gs://')
                ):
                    logger.error(
                        f'[{session_id}] Critical assumption violated: VEO response video_obj has no valid GCS URI. URI: {veo_provided_gcs_uri}'
                    )
                    yield {
                        'is_task_complete': True,
                        'content': f'VEO response video_obj has no valid GCS URI ({veo_provided_gcs_uri}), cannot proceed.',
                        'is_error': True,
                        'final_message_text': 'Video processing failed due to missing GCS URI from VEO.',
                        'progress_percent': 100,
                    }
                    return

                # Parse the GCS URI provided by VEO
                try:
                    parsed_uri = urlparse(veo_provided_gcs_uri)
                    veo_bucket_name = parsed_uri.netloc
                    veo_blob_name = parsed_uri.path.lstrip('/')
                    logger.info(
                        f'[{session_id}] Parsed VEO GCS URI. Bucket: {veo_bucket_name}, Blob: {veo_blob_name}'
                    )
                except Exception as e:
                    logger.error(
                        f"[{session_id}] Failed to parse VEO GCS URI '{veo_provided_gcs_uri}': {e}"
                    )
                    yield {
                        'is_task_complete': True,
                        'content': f'Failed to parse VEO GCS URI: {veo_provided_gcs_uri}',
                        'is_error': True,
                        'final_message_text': 'Video processing error.',
                        'progress_percent': 100,
                    }
                    return

                if veo_bucket_name and veo_blob_name:
                    # Attempt to sign the GCS URI
                    signed_gcs_url = await self._generate_signed_url(
                        veo_blob_name,
                        veo_bucket_name,  # Use the bucket name from VEO's output URI
                        self.SIGNED_URL_EXPIRATION_SECONDS,
                    )

                    video_filename_for_artifact = veo_provided_gcs_uri.split(
                        '/'
                    )[-1]
                    artifact_description = f"Generated video for prompt: '{prompt}'. Original GCS location: {veo_provided_gcs_uri}"
                    completion_message = f'Video generation successful. Access video at link (expires): {signed_gcs_url}. Original GCS location: {veo_provided_gcs_uri}'

                    if (
                        signed_gcs_url == veo_provided_gcs_uri
                    ):  # Signing failed or was not applicable, and it returned the original GCS URI
                        completion_message = f'Video generation successful. Video stored at GCS: {veo_provided_gcs_uri}. A signed URL could not be generated.'
                        logger.warning(
                            f'[{session_id}] Signed URL generation might have failed or was not applicable, using GCS URI: {veo_provided_gcs_uri}'
                        )

                    logger.info(
                        f'[{session_id}] Yielding final success. Signed GCS URL: {signed_gcs_url}, Artifact Name: {video_filename_for_artifact}'
                    )
                    yield {
                        'is_task_complete': True,
                        'file_part_data': {
                            'uri': signed_gcs_url,
                            'mimeType': mime_type,
                        },
                        'artifact_name': video_filename_for_artifact,
                        'artifact_description': artifact_description,
                        'final_message_text': completion_message,
                        'progress_percent': 100,
                    }
                else:
                    err_message = "VEO generation completed, but failed to parse bucket/blob from VEO's GCS URI for signing."
                    logger.error(
                        f'[{session_id}] {err_message} (VEO GCS URI was {veo_provided_gcs_uri})'
                    )
                    yield {
                        'is_task_complete': True,
                        'content': err_message,
                        'is_error': True,
                        'final_message_text': err_message,
                        'progress_percent': 100,
                    }

            elif (
                hasattr(veo_operation.response, 'rai_media_filtered_count')
                and veo_operation.response.rai_media_filtered_count > 0
            ):
                reasons = getattr(
                    veo_operation.response,
                    'rai_media_filtered_reasons',
                    ['Unknown safety filter.'],
                )
                message = f'Video generation was blocked by safety filters. Reasons: {", ".join(str(r) for r in reasons)}'
                logger.warning(f'[{session_id}] {message}')
                yield {
                    'is_task_complete': True,
                    'content': message,
                    'is_error': True,
                    'final_message_text': message,
                    'progress_percent': 100,
                }
            else:
                message = 'VEO generation completed, but no video was returned in the response and no explicit safety filter indicated.'
                logger.error(
                    f'[{session_id}] {message} Full response: {str(veo_operation.response)[:500]}'
                )
                yield {
                    'is_task_complete': True,
                    'content': message,
                    'is_error': True,
                    'final_message_text': message,
                    'progress_percent': 100,
                }

        except Exception as e:
            error_context_msg = (
                f'VEO operation name: {veo_operation_name_for_reporting}'
                if operation_kicked_off
                else 'VEO operation not started.'
            )
            error_message = f'An error occurred during video generation stream for session_id {session_id}: {e}. Context: {error_context_msg}'
            logger.exception(error_message)  # Log with traceback
            yield {
                'is_task_complete': True,
                'content': error_message,
                'is_error': True,
                'final_message_text': f'An unexpected error occurred: {e}',
                'progress_percent': 100,
            }
