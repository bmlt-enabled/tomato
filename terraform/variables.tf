variable "rds_password" {
  default = "1234567890"
}

variable "secret_key" {
  default = "1234567890"
}

variable memory {
  type    = string
  default = 2048
}

variable cpu {
  type    = string
  default = 1024
}
