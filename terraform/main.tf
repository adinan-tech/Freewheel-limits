locals {
  archive_bucket_name = var.archive_bucket_name == null ? (
    oci_objectstorage_bucket.archive[0].name
  ) : data.oci_objectstorage_bucket.existing[0].name
  archive_bucket_compartment_id = var.archive_bucket_name == null ? (
    oci_objectstorage_bucket.archive[0].compartment_id
  ) : data.oci_objectstorage_bucket.existing[0].compartment_id
  archive_object_name = "${var.name_prefix}_checker.zip"
}

module "functions" {
  source = "./modules/functions"

  app_params = {
    checker = {
      compartment_id             = var.function_compartment_id
      display_name               = "${var.name_prefix}_app"
      subnet_ids                 = [var.subnet_id]
      network_security_group_ids = []
      shape                      = "GENERIC_X86"
    }
  }
}

data "oci_objectstorage_namespace" "current" {
  compartment_id = var.tenancy_id
}

resource "oci_objectstorage_bucket" "archive" {
  count          = var.archive_bucket_name == null ? 1 : 0
  compartment_id = var.function_compartment_id
  namespace      = data.oci_objectstorage_namespace.current.namespace
  name           = "${var.name_prefix}_${replace(var.region, "-", "_")}_${substr(sha1(var.function_compartment_id), 0, 8)}"
  access_type    = "NoPublicAccess"
}

data "oci_objectstorage_bucket" "existing" {
  count     = var.archive_bucket_name == null ? 0 : 1
  namespace = data.oci_objectstorage_namespace.current.namespace
  name      = var.archive_bucket_name
}

resource "oci_identity_policy" "archive_read" {
  provider       = oci.home
  compartment_id = var.tenancy_id
  name           = "${var.name_prefix}_archive_read"
  description    = "Allow Functions applications in the compartment to read the selected ZIP archive bucket"
  statements = [
    "Allow any-user to read objects in compartment id ${local.archive_bucket_compartment_id} where all {request.principal.type = 'fnapp', request.principal.compartment.id = '${var.function_compartment_id}', target.bucket.name = '${local.archive_bucket_name}', target.object.name = '${local.archive_object_name}'}",
  ]

  lifecycle {
    precondition {
      condition     = var.archive_bucket_name == null ? true : data.oci_objectstorage_bucket.existing[0].access_type == "NoPublicAccess"
      error_message = "The existing archive bucket must have NoPublicAccess."
    }
  }
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
      function_id           = var.function_id
      dynamic_group_name    = "${var.name_prefix}_reader"
      policy_name           = "${var.name_prefix}_read_limits"
      metric_compartment_id = var.function_compartment_id
    }
  }
}

resource "oci_ons_notification_topic" "limit_warnings" {
  count = var.function_id == null ? 0 : 1

  compartment_id = var.function_compartment_id
  name           = "${var.name_prefix}_alerts"
  description    = "Limit warning email notifications"
}

resource "oci_ons_subscription" "email" {
  for_each = var.function_id == null ? toset([]) : toset(var.email_recipients)

  compartment_id = var.function_compartment_id
  topic_id       = oci_ons_notification_topic.limit_warnings[0].topic_id
  protocol       = "EMAIL"
  endpoint       = each.value
}

resource "oci_monitoring_alarm" "limit_warning" {
  for_each = var.function_id == null ? {} : var.monitors

  compartment_id        = var.function_compartment_id
  metric_compartment_id = var.function_compartment_id
  display_name          = substr("${var.name_prefix}_${each.key}_warning", 0, 255)
  namespace             = "limit_warnings"
  query                 = "LimitUsagePercent[1m]{monitor = \"${each.key}\"}.max() >= ${each.value.warning_percent}"
  severity              = "WARNING"
  is_enabled            = true
  destinations          = [oci_ons_notification_topic.limit_warnings[0].topic_id]
  pending_duration      = "PT1M"
  resolution            = "1m"
  notification_title    = "OCI limit warning: ${each.key}"
  body                  = "Service ${each.value.service_name}/${each.value.limit_name}, region ${var.region}, threshold ${each.value.warning_percent}%"
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
      schedule_compartment_id = var.function_compartment_id
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
