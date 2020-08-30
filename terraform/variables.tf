variable "rds_password" {
}

variable "secret_key" {
}

variable memory {
  type    = string
  default = 4096
}

variable cpu {
  type    = string
  default = 2048
}
