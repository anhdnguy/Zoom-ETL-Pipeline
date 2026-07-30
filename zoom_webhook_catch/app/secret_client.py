import boto3
import os
import json
import logging
from app.exceptions import ConfigurationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ["REGION"]

def get_secret(secret_name):
    region_name = REGION
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except Exception as e:
        logger.error(f"Unexpected error retrieving secret: {e}", exc_info=True)
        raise ConfigurationError(f"Unexpected error: {str(e)}") from e