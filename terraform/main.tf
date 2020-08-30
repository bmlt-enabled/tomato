terraform {
  required_version = ">= 0.13"

  backend "s3" {
    bucket  = "tomato-terraform-state-patrick"
    key     = "state"
    region  = "us-east-1"
    profile = "patrick"
  }
}

provider "aws" {
  version = "~> 3.0"
  region  = "us-east-1"
  profile = "patrick"
}
