terraform {
  backend "s3" {
    bucket  = "tomato-terraform-state-patrick"
    key     = "state"
    region  = "us-east-1"
    profile = "patrick"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "patrick"
}
