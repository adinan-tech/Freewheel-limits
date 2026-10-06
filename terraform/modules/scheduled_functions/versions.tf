terraform {
  required_version = ">= 1.3.0"

  required_providers {
    oci = {
      source                = "oracle/oci"
      version               = ">= 7.0.0"
      configuration_aliases = [oci.home]
    }
  }
}
