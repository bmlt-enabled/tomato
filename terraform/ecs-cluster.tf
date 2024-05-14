resource "aws_ecs_cluster" "aggregator" {
  name = "aggregator"
}

resource "aws_autoscaling_group" "aggregator_cluster" {
  name                = local.aggregator_cluster_name
  vpc_zone_identifier = data.aws_subnets.main.ids
  min_size            = 2
  max_size            = 2
  desired_capacity    = 2

  launch_template {
    id      = aws_launch_template.aggregator_cluster.id
    version = "$Latest"
  }

  dynamic "tag" {
    for_each = [
      {
        key   = "Name"
        value = "aggregator"
      },
      {
        key   = "application"
        value = "aggregator"
      },
      {
        key   = "environment"
        value = "production"
      },
    ]
    content {
      key                 = tag.value.key
      value               = tag.value.value
      propagate_at_launch = true
    }
  }
}

locals {
  aggregator_cluster_name = aws_ecs_cluster.aggregator.name
}

resource "aws_launch_template" "aggregator_cluster" {
  name_prefix   = local.aggregator_cluster_name
  image_id      = data.aws_ami.ecs.image_id
  instance_type = "t3a.small"
  key_name      = data.aws_key_pair.this.key_name
  user_data     = data.cloudinit_config.aggregator_cluster.rendered

  iam_instance_profile {
    name = data.aws_iam_instance_profile.ecs.name
  }

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [data.aws_security_group.ecs_clusters.id]
  }

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 30
      volume_type           = "gp3"
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "aggregator"
      application = "true"
      environment = "production"
    }
  }

  tag_specifications {
    resource_type = "volume"
    tags = {
      Name        = "aggregator"
      application = "true"
      environment = "production"
    }
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [image_id]
  }
}
