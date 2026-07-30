# =============================================================================
# LOAD BALANCER MODULE
# Purpose: Create an internal application load balancer
# =============================================================================

resource "aws_lb" "airflow" {
  name               = "${var.project_name}-${var.environment}"
  internal           = true
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.private_subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-alb"
  }
}

resource "aws_lb_target_group" "webserver" {
  name        = "${var.project_name}-${var.environment}-web"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip" # REQUIRED for Fargate (not "instance")

  health_check {
    enabled             = true
    path                = "/api/v2/version"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    matcher             = "200"
  }

  # GOTCHA: Fargate tasks take 30-60s to start. If the
  # deregistration delay is too short, in-flight requests
  # get dropped during deployments.
  deregistration_delay = 60

  tags = {
    Name = "${var.project_name}-${var.environment}-webserver-tg"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.airflow.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.webserver.arn
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-lb-listener"
  }
}