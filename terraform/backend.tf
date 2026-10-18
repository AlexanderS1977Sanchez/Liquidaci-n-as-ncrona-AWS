terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket       = "agrolink-terraform-state-362040073178"
    key          = "liquidaciones/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}