terraform {
  backend "s3" {
    bucket       = "iot-wetterdaten-pipeline-terraform-state-jakob-20260613"
    key          = "infra/bootstrap/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
