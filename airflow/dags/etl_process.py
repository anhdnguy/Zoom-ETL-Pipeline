"""
Zoom Data ETL Pipeline - Extracts users, meetings, and participants to S3
Daily scheduled pipeline with comprehensive error handling and data quality checks
"""

from airflow.sdk import dag, task, TaskGroup
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import Variable

from datetime import datetime, timedelta
from typing import List, Dict
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Import client
from src.bootstrap import build_zoom_client

# Import services for extract and load
from src.services.meeting_service import MeetingService
from src.services.user_service import UserService
from src.services.participant_service import ParticipantService
from src.services.retry import RetryExecutor
from src.storage.s3_writer import S3Writer

from src.config import AppConfig

# Default parameters for Airflow
MAX_RETRIES=AppConfig.max_retries
default_args={
    'owner': 'Anh',
    'depends_on_past': False,
    'retries': MAX_RETRIES,
    'retry_delay': timedelta(minutes=10),
    'start_date': datetime(2026, 3, 20)
}

@dag('Zoom_ETL', schedule='0 4 * * *', default_args=default_args,
     catchup=False, tags=['Zoom'], description='Extracting Data from Zoom')
def etl_process():
    @task
    def check_variable() -> None:
        try:
            logger.info("Validating environment configuration...")
            AppConfig.validate()
            logger.info("✓ Configuration validated")
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {str(e)}")
            raise

    @task
    def get_all_user_ids(**kwargs) -> List[str]:
        """Task to get all users IDs."""
        client = build_zoom_client()
        retry = RetryExecutor(MAX_RETRIES, logger)
        service = UserService(client, retry)
        return service.fetch_all_user_ids()
    
    @task
    def process_user_chunk(chunk: List[str]) -> List[Dict]:
        """Task to process a chunk of user IDs and return user info."""
        client = build_zoom_client()
        retry = RetryExecutor(MAX_RETRIES, logger)
        service = UserService(client, retry)
        return service.fetch_user_details(chunk)

    @task
    def process_meeting_chunk(chunk: List[str], last_run_timestamp: str) -> List[Dict]:
        """Task to process a chunk of user IDs and return meeting info."""
        client = build_zoom_client()
        retry = RetryExecutor(MAX_RETRIES, logger)
        service = MeetingService(client, retry)
        last_run_dt = datetime.fromisoformat(last_run_timestamp)
        return service.fetch_user_meetings_since(chunk, last_run_dt)

    @task
    def process_meeting_details(meeting_infos: List[Dict]) -> List[Dict]:
        """Task to get meeting details and save to metadata directory."""
        client = build_zoom_client()
        retry = RetryExecutor(MAX_RETRIES, logger)
        service = MeetingService(client, retry)
        return service.fetch_meeting_details(meeting_infos)
    
    @task
    def process_meeting_participants(meeting_infos: List[Dict]) -> List[Dict]:
        """Task to get meeting participants and save to metadata directory."""
        client = build_zoom_client()
        retry = RetryExecutor(MAX_RETRIES, logger)
        service = ParticipantService(client, retry)
        return service.fetch_meeting_participants(meeting_infos)
    
    @task
    def get_last_run_timestamp() -> str:
        """Task to get the last time that the pipeline ran"""
        """Get the timestamp of the last pipeline run."""
        last_run = Variable.get("last_pipeline_run")
        return last_run if last_run else datetime.now().isoformat()
    
    @task
    def set_last_run_timestamp() -> str:
        """Task to set the current time"""
        """Set the current timestamp as the last pipeline run."""
        Variable.set("last_pipeline_run", datetime.now().isoformat())
    
    @task
    def load_users(user_infos_list: List[List[Dict]]) -> None:
        """Task to load user data into the datalake."""
        loader = S3Writer(AppConfig)
        loader._load_generic(
            records=user_infos_list,
            dataset_name='users'
        )

    @task
    def load_meetings(meeting_details_list: List[List[Dict]]) -> None:
        """Task to load meeting data into the datalake."""
        loader = S3Writer(AppConfig)
        loader._load_generic(
            records=meeting_details_list,
            dataset_name='meetings'
        )

    @task
    def load_participants(participants_list: List[List[Dict]]) -> None:
        """Task to load participant data into the database."""
        loader = S3Writer(AppConfig)
        loader._load_generic(
            records=participants_list,
            dataset_name='participants'
        )

    @task
    def transform_to_silver_zone(dataset_name: str) -> None:
        """Task to transform the raw data from bronze to silver zone"""
        loader = S3Writer(AppConfig)
        loader._transform_to_silver(dataset_name)

    @task
    def transform_users_to_gold() -> None:
        """Task to transform silver zone users to gold zone"""
        loader = S3Writer(AppConfig)
        loader._build_gold_users()

    @task
    def transform_meetings_to_gold() -> None:
        """Task to transform silver zone meetings to gold zone"""
        loader = S3Writer(AppConfig)
        loader._build_gold_meetings()

    @task
    def transform_participants_to_gold() -> None:
        """Task to transform silver zone participants to gold zone"""
        loader = S3Writer(AppConfig)
        loader._build_gold_participants()
    
    start = EmptyOperator(task_id='start')
    end = EmptyOperator(task_id='end')

    # Starter
    check_status = check_variable()

    # Get last run timestamp
    last_run = get_last_run_timestamp()

    # Get all users
    user_ids = get_all_user_ids()

    # Process user information for each chunk -> List[List[Dict]]
    with TaskGroup(group_id='process_user_info') as user_info_group:
        user_infos = process_user_chunk.expand(chunk=user_ids)

    # Process user meetings for each chunk -> List[List[Dict]]
    with TaskGroup(group_id='process_user_meetings') as user_meetings_group:
        user_meetings = process_meeting_chunk.partial(last_run_timestamp=last_run).expand(chunk=user_ids)

    # Process meeting details and participants using dynamic task mapping
    with TaskGroup(group_id='meeting_details') as meeting_detail_group:
        meeting_details_tasks = process_meeting_details.expand(meeting_infos=user_meetings)
    
    with TaskGroup(group_id='meeting_participants') as meeting_participant_group:
        meeting_participants_tasks = process_meeting_participants.expand(meeting_infos=user_meetings)
    
    # Load data into the database
    load_users_task = load_users(user_infos)

    load_meetings_task = load_meetings(meeting_details_tasks)

    load_participants_task = load_participants(meeting_participants_tasks)

    # Transform bronze to silver zone
    with TaskGroup(group_id='silver_transforms') as silver_group:
        silver_users = transform_to_silver_zone("users")
        silver_meetings = transform_to_silver_zone("meetings")
        silver_participants = transform_to_silver_zone("participants")

    # Transform silver to gold zone
    with TaskGroup(group_id='gold_transforms') as gold_group:
        gold_users = transform_users_to_gold()
        gold_meetings = transform_meetings_to_gold()
        gold_participants = transform_participants_to_gold()

    # Set last run timestamp after all processing is complete
    set_last_run = set_last_run_timestamp()

    # Define task dependencies
    start >> check_status >> last_run >> user_ids
    user_ids >> user_info_group
    [user_ids, last_run] >> user_meetings_group
    user_meetings_group >> [meeting_detail_group, meeting_participant_group]

    # Load data after extraction
    user_info_group >> load_users_task
    meeting_detail_group >> load_meetings_task
    meeting_participant_group >> load_participants_task
    
    # Final dependency chain
    [load_users_task, load_meetings_task, load_participants_task] >> silver_group
    silver_group >> gold_group >> set_last_run >> end

etl_process()