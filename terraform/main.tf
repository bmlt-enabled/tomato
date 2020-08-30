terraform {
  required_version = ">= 0.13"

  backend "s3" {
    bucket  = "tomato-terraform-state-mvana"
    key     = "state"
    region  = "us-east-1"
    profile = "mvana"
  }
}

provider "aws" {
  version = "~> 3.0"
  region  = "us-east-1"
  profile = "mvana"
}
