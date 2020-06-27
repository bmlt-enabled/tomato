terraform {
  backend "s3" {
    bucket  = "tomato-terraform-state-mvana"
    key     = "state"
    region  = "us-east-1"
    profile = "mvana"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "mvana"
}

