locals {
  schedule_compartment_id = coalesce(var.schedule_compartment_id, var.function_compartment_id)
}

module "functions" {
  source = "./modules/functions"

  app_params = {
    checker = {
      compartment_id             = var.function_compartment_id
      display_name               = "${var.name_prefix}_app"
      subnet_ids                 = var.subnet_ids
      network_security_group_ids = var.network_security_group_ids
      shape                      = "GENERIC_X86"
    }
  }
}

data "oci_objectstorage_namespace" "current" {
  compartment_id = var.tenancy_id
}

resource "oci_objectstorage_bucket" "archive" {
  compartment_id = var.function_compartment_id
  namespace      = data.oci_objectstorage_namespace.current.namespace
  name           = "${var.name_prefix}_${replace(var.region, "-", "_")}_${substr(sha1(var.function_compartment_id), 0, 8)}"
  access_type    = "NoPublicAccess"
}

resource "oci_identity_policy" "archive_read" {
  provider       = oci.home
  compartment_id = var.tenancy_id
  name           = "${var.name_prefix}_archive_read"
  description    = "Allow Functions applications in the compartment to read the dedicated ZIP archive bucket"
  statements = [
    "Allow any-user to read objects in compartment id ${var.function_compartment_id} where all {request.principal.type = 'fnapp', request.principal.compartment.id = '${var.function_compartment_id}', target.bucket.name = '${oci_objectstorage_bucket.archive.name}'}",
  ]
}

module "function_logging" {
  source = "./modules/function_logging"

  log_params = {
    checker = {
      compartment_id   = var.function_compartment_id
      application_id   = module.functions.application_ids["checker"]
      application_name = "${var.name_prefix}_app"
      group_name       = "${var.name_prefix}_logs"
      log_name         = "${var.name_prefix}_invoke"
      retention_days   = 30
    }
  }
}

module "function_reader_iam" {
  count  = var.function_id == null ? 0 : 1
  source = "./modules/function_reader_iam"
  providers = {
    oci = oci.home
  }

  tenancy_id = var.tenancy_id
  reader_params = {
    checker = {
      function_id        = var.function_id
      dynamic_group_name = "${var.name_prefix}_reader"
      policy_name        = "${var.name_prefix}_read_limits"
    }
  }
}

module "scheduled_functions" {
  count  = var.function_id == null ? 0 : 1
  source = "./modules/scheduled_functions"
  providers = {
    oci      = oci
    oci.home = oci.home
  }

  tenancy_id = var.tenancy_id
  schedule_params = {
    checker = {
      display_name            = "${var.name_prefix}_schedule"
      description             = "Run the OCI service-limit checker"
      schedule_compartment_id = local.schedule_compartment_id
      function_compartment_id = var.function_compartment_id
      function_id             = var.function_id
      recurrence_type         = "CRON"
      recurrence_details      = var.check_schedule_utc
      time_starts             = var.schedule_start_utc
      dynamic_group_name      = "${var.name_prefix}_schedule"
      policy_name             = "${var.name_prefix}_invoke"
    }
  }
}
