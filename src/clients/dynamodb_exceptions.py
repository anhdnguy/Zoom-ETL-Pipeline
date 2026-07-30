class DynamoDBError (Exception):
    """Base exception for all Dynamo DB errors"""

class DeleteStatusTypeError (DynamoDBError):
    """Wrong type for delete_status column"""
    pass

class ScanTableError(DynamoDBError):
    """Scan Table error"""
    pass

class UpdateTableError (DynamoDBError):
    """Update Table error"""
    pass