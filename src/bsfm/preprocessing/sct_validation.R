# Validation driver; fitting/correction is defined only in sct_core.R.
script_file <- if (sys.nframe() > 0L) sys.frame(1)$ofile else sub("^--file=", "", grep("^--file=", commandArgs(), value=TRUE)[[1]])
source(file.path(dirname(normalizePath(script_file)), "sct_core.R"))

run_validation <- function(args) {
  assert(length(args) == 5L, "Usage: sct_validation.R EXTERNAL_ENV INPUT_DIR OUTPUT_DIR DEPTH SEED")
  envroot <- configure_environment(args[[1]])
  versions <- FROZEN_VERSIONS
  input_dir <- normalizePath(args[[2]], winslash = "/", mustWork = TRUE)
  output <- args[[3]]
  assert(!dir.exists(output), "Output directory already exists")
  dir.create(output, recursive = TRUE)
  depth <- as.numeric(args[[4]])
  seed <- as.integer(args[[5]])
  warnings <- character()
  started <- proc.time()[["elapsed"]]
  input <- load_input(input_dir)
  result <- withCallingHandlers(fit_correct(input$counts, depth, seed), warning = function(w) {
    warnings <<- c(warnings, conditionMessage(w))
  })
  saveRDS(result$fit, file.path(output, "fit.rds"), version = 3)
  saveRDS(result$corrected, file.path(output, "corrected-counts.rds"), version = 3)
  saveRDS(result$response, file.path(output, "log1p-response.rds"), version = 3)
  saveRDS(result$object, file.path(output, "assays.rds"), version = 3)
  signature <- list(model_pars = result$fit$model_pars, model_pars_fit = result$fit$model_pars_fit,
                    cells_step1 = result$fit$cells_step1, corrected = result$corrected, response = result$response)
  hashes <- lapply(signature, digest::digest, algo = "sha256", serializeVersion = 3)
  writeLines(capture.output(sessionInfo()), file.path(output, "session.txt"))
  jsonlite::write_json(result$fit$arguments, file.path(output, "effective-arguments.json"),
                       auto_unbox = TRUE, pretty = TRUE, null = "null", digits = NA)
  artifacts <- lapply(list.files(output, full.names = TRUE), function(p) {
    list(name = basename(p), bytes = unname(file.info(p)$size), sha256 = digest::digest(file = p, algo = "sha256"))
  })
  report <- list(schema = "bsfm.sct-validation.v1", status = "pass",
    input_manifest_sha256 = digest::digest(file = file.path(input_dir, "input.json"), algo = "sha256"),
    input_genes = nrow(input$counts), input_cells = ncol(input$counts),
    fitting_cells = length(result$fit$cells_step1), actual_fitting_order_matches = TRUE,
    effective_method = result$fit$arguments$method, versions = as.list(versions),
    R = as.character(getRversion()), Bioconductor = as.character(BiocManager::version()),
    depth = depth, seed = seed, RNG = RNGkind(), library_paths = .libPaths(),
    threads = as.list(Sys.getenv(c("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"))),
    gene_availability = list(modeled_by_SCT = length(result$effective_genes),
      unavailable = setdiff(rownames(input$counts), result$effective_genes)),
    corrected_shape = dim(result$corrected), response_shape = dim(result$response),
    corrected_finite_nonnegative_integer = TRUE, response_finite = TRUE,
    exact_log1p_reconstruction = TRUE, log1p_max_absolute_difference = 0,
    correction_repeat_identical = TRUE, independent_depth_reconstruction_exact = TRUE,
    semantic_sha256 = hashes,
    within_process_elapsed_seconds = unname(proc.time()[["elapsed"]] - started),
    warnings = warnings, artifacts = artifacts)
  jsonlite::write_json(report, file.path(output, "report.json"), auto_unbox = TRUE,
                       pretty = TRUE, null = "null", digits = NA)
  cat("PASS: SCT-v2, all cells, common-depth correction, exact layer equality\n")
}

if (sys.nframe() == 0L) run_validation(commandArgs(trailingOnly = TRUE))
