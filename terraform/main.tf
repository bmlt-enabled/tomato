terraform {
  backend "s3" {
    bucket  = "tomato-terraform-state"
    key     = "state"
    region  = "us-east-1"
    profile = "bmlt"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "bmlt"
}

