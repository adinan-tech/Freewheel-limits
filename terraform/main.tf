locals {
  schedule_compartment_id = coalesce(var.schedule_compartment_id, var.function_compartment_id)
  runtime_config = jsonencode({
    region             = var.region
    tenancy_id         = var.tenancy_id
    subscription_id    = var.subscription_id
    check_schedule_utc = var.check_schedule_utc
    email_recipients   = var.email_recipients
    monitors           = var.monitors
  })
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

  fn_params = {
    checker = {
      application_key             = "checker"
      display_name                = "${var.name_prefix}_checker"
      image                       = var.function_image
      image_digest                = var.function_image_digest
      memory_in_mbs               = 256
      timeout_in_seconds          = 120
      detached_timeout_in_seconds = 120
      config = {
        LIMIT_CHECKER_CONFIG = local.runtime_config
      }
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
  source = "./modules/function_reader_iam"
  providers = {
    oci = oci.home
  }

  tenancy_id = var.tenancy_id
  reader_params = {
    checker = {
      function_id        = module.functions.function_ids["checker"]
      dynamic_group_name = "${var.name_prefix}_reader"
      policy_name        = "${var.name_prefix}_read_limits"
    }
  }
}

module "scheduled_functions" {
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
      function_id             = module.functions.function_ids["checker"]
      recurrence_type         = "CRON"
      recurrence_details      = var.check_schedule_utc
      time_starts             = var.schedule_start_utc
      dynamic_group_name      = "${var.name_prefix}_schedule"
      policy_name             = "${var.name_prefix}_invoke"
    }
  }
}
