resource "aws_db_subnet_group" "tomato" {
  name       = "tomato"
  subnet_ids = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

resource "aws_db_instance" "tomato" {
  identifier          = "tomato"
  allocated_storage   = 100
  engine              = "postgres"
  engine_version      = "9.6.18"
  instance_class      = "db.t3.micro"
  storage_type        = "gp2"
  deletion_protection = true
  multi_az            = true

  name     = "tomato"
  username = "tomato"
  password = var.rds_password
  port     = 5432

  apply_immediately       = true
  publicly_accessible     = true
  vpc_security_group_ids  = [aws_security_group.tomato_rds.id]
  db_subnet_group_name    = aws_db_subnet_group.tomato.name
  backup_retention_period = 7

  snapshot_identifier = "arn:aws:rds:us-east-1:198201167080:snapshot:tomato"
  skip_final_snapshot = false

  tags = {
    Name = "tomato"
  }

  lifecycle {
    ignore_changes = [snapshot_identifier]
  }
}

resource "aws_security_group" "tomato_rds" {
  name   = "tomato-rds"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 5432
    to_port     = 5432
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

