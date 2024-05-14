terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    cloudinit = {
      source  = "hashicorp/cloudinit"
      version = "~> 2.3"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  backend "s3" {
    bucket  = "mvana-account-terraform"
    key     = "aggregator/state.json"
    region  = "us-east-1"
    profile = "mvana"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "mvana"
}
