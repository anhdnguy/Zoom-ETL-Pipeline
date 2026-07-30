from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from botocore.signers import CloudFrontSigner
from app.logger import setup_logger
from app.config import Config

logger = setup_logger(__name__)

class CloudFrontClient:
    """Handles for Cloud Front Distribution"""

    def __init__(self):
        self.domain = Config.CLOUDFRONT_DOMAIN
        self.default_expiration = Config.CLOUDFRONT_URL_EXPIRATION
        
        # Cache credentials to avoid repeated Secrets Manager calls
        self._key_pair_id = Config.CLOUDFRONT_KEY_PAIR_ID
        self._private_key = Config.CLOUDFRONT_PRIVATE_KEY
        self._private_key = self._private_key.replace("\\n", "\n")
        self._cf_signer = None
        
    def _get_signer(self) -> CloudFrontSigner:
        """
        Get or create a CloudFrontSigner instance.
        
        Returns:
            Configured CloudFrontSigner
        """

        if self._cf_signer:
            return self._cf_signer

        def rsa_signer(message):
            """Sign message with RSA private key"""
            private_key_obj = serialization.load_pem_private_key(
                self._private_key.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            return private_key_obj.sign(
                message,
                padding.PKCS1v15(),
                hashes.SHA1()
            )
        
        self._cf_signer = CloudFrontSigner(
            self._key_pair_id,  # Key pair ID
            rsa_signer  # The signing function we just created
        )

        return self._cf_signer

    def generate_cloud_presigned_url(
        self,
        s3_key: str,
        expiration_seconds: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> str:
        # Build CloudFront URL
        url = f"https://{self.domain}/{s3_key}"

        # Calculate expiration time
        if expiration_seconds is None:
            expiration_seconds = self.default_expiration

        expire_date = datetime.now(timezone.utc) + timedelta(seconds=expiration_seconds)

        logger.info(f"Generating signed URL for: {s3_key}")
        logger.info(f"  Expires at: {expire_date.isoformat()} UTC ({expiration_seconds}s from now)")

        # Get signer
        signer = self._get_signer()

        # Generate signed URL
        signed_url = signer.generate_presigned_url(
            url,
            date_less_than=expire_date
        )

        logger.info(f"Successfully generated signed URL")
        return signed_url
    
    def generate_multiple_urls(
        self,
        s3_keys: list,
        expiration_seconds: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Generate signed URLs for multiple recordings.
        
        Returns:
            Dict mapping S3 key to signed URL
        """

        urls = {}

        for s3_key in s3_keys:
            try:
                urls[s3_key] = self.generate_cloud_presigned_url(
                    s3_key=s3_key,
                    expiration_seconds=expiration_seconds
                )
            except Exception as e:
                logger.error(f"Failed to generate URL for {s3_key}: {str(e)}")
                urls[s3_key] = None

        return urls
    
# Global instance
cloudfront_signer = CloudFrontClient()
        