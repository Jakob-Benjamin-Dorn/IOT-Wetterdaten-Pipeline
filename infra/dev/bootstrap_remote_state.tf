data "terraform_remote_state" "bootstrap" {
  backend = "s3"

  config = {
    bucket = "iot-wetterdaten-pipeline-terraform-state-jakob-20260613"
    key    = "infra/bootstrap/terraform.tfstate"
    region = "eu-central-1"
  }
}
