# app/secrets_manager.py
import boto3
import json
from typing import Dict
from botocore.exceptions import ClientError
from app.exceptions import SecretsManagerError
from app.logger import setup_logger
from app.config import Config

logger = setup_logger(__name__)

class SecretsManager:
    """Manages retrieval of secrets from AWS Secrets Manager"""
    
    def __init__(self):
        self.client = boto3.client('secretsmanager', region_name=Config.AWS_REGION)
        self._cache = {}  # Cache secrets to avoid repeated API calls
    
    def get_cloudfront_keys(self) -> Dict[str, str]:
        """
        Retrieve Zoom OAuth credentials from Secrets Manager.
        
        Returns:
            Dict with keys: 'access_token', 'refresh_token', 'expires_at', etc.
        
        Raises:
            SecretsManagerError: If secret cannot be retrieved
        """
        secret_name = Config.CLOUDFRONT_SECRET_NAME
        
        # Check cache first
        if secret_name in self._cache:
            logger.debug(f"Using cached credentials for {secret_name}")
            return self._cache[secret_name]
        
        try:
            logger.info(f"Retrieving secret: {secret_name}")
            response = self.client.get_secret_value(SecretId=secret_name)
            
            # Parse secret (assumed to be JSON)
            if 'SecretString' in response:
                secret_data = json.loads(response['SecretString'])
                
                # Validate expected fields
                required_fields = ['key_pair_id', 'private_key']
                missing_fields = [f for f in required_fields if f not in secret_data]
                
                if missing_fields:
                    raise SecretsManagerError(
                        f"Secret missing required fields: {missing_fields}"
                    )
                
                # Cache for future use
                self._cache[secret_name] = secret_data
                
                logger.info(f"Successfully retrieved secret: {secret_name}")
                return secret_data
            else:
                raise SecretsManagerError("Secret does not contain SecretString")
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ResourceNotFoundException':
                raise SecretsManagerError(f"Secret not found: {secret_name}")
            elif error_code == 'AccessDeniedException':
                raise SecretsManagerError(f"Access denied to secret: {secret_name}")
            else:
                raise SecretsManagerError(f"Failed to retrieve secret: {str(e)}")
        
        except json.JSONDecodeError as e:
            raise SecretsManagerError(f"Secret is not valid JSON: {str(e)}")
    
    def invalidate_cache(self):
        """Clear cached secrets (useful if token expires)"""
        self._cache.clear()
        logger.info("Secrets cache cleared")

# Global instance (singleton pattern)
secrets_manager = SecretsManager()