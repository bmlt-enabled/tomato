/*
resource "aws_elasticache_subnet_group" "tomato" {
  name       = "tomato"
  subnet_ids = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

resource "aws_elasticache_cluster" "tomato" {
  cluster_id           = "tomato"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis5.0"
  engine_version       = "5.0.6"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.tomato.name
  security_group_ids   = [aws_security_group.tomato_redis.id]
}

resource "aws_security_group" "tomato_redis" {
  name   = "tomato-redis"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [aws_subnet.public_a.cidr_block, aws_subnet.public_b.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_cluster" "tomato_memcached" {
  cluster_id           = "tomato-memcached"
  engine               = "memcached"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.memcached1.5"
  engine_version       = "1.5.16"
  port                 = 11211
  subnet_group_name    = aws_elasticache_subnet_group.tomato.name
  security_group_ids   = [aws_security_group.tomato_redis.id]
}

resource "aws_security_group" "tomato_memcached" {
  name   = "tomato-memcached"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 11211
    to_port     = 11211
    protocol    = "tcp"
    cidr_blocks = [aws_subnet.public_a.cidr_block, aws_subnet.public_b.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
*/
