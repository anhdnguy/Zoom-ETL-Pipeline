output "endpoint" {
  description = "Redis endpoint address"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "port" {
  description = "Redis port"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].port
}

output "cluster_id" {
  description = "Redis cluster ID"
  value       = aws_elasticache_cluster.redis.id
}