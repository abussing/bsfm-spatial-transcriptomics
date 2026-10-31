# Canonical bounded validation. No gene-panel selection or response centering.
assert <- function(ok, message) {
  if (!isTRUE(ok)) stop(message, call. = FALSE)
}

validate_counts <- function(x) {
  assert(length(dim(x)) == 2L && all(dim(x) > 1L), "Need a genes-by-cells matrix")
  assert(!is.null(rownames(x)) && !is.null(colnames(x)), "Missing identifiers")
  assert(!anyDuplicated(rownames(x)) && !anyDuplicated(colnames(x)), "Duplicate identifiers")
  assert(all(nzchar(rownames(x))) && all(nzchar(colnames(x))), "Empty identifiers")
  values <- if (inherits(x, "sparseMatrix")) x@x else as.vector(x)
  assert(all(is.finite(values) & values >= 0 & values == floor(values)), "Invalid raw counts")
  assert(all(Matrix::colSums(x) > 0), "Zero-total fitting cell")
  invisible(TRUE)
}

load_input <- function(directory) {
  meta <- jsonlite::read_json(file.path(directory, "input.json"), simplifyVector = FALSE)
  assert(meta$schema == "bsfm.sct-validation-input.v1", "Unsupported input schema")
  for (entry in meta$files) {
    path <- file.path(directory, entry$name)
    assert(file.info(path)$size == entry$bytes, "Input file size mismatch")
    assert(digest::digest(file = path, algo = "sha256") == entry$sha256, "Input file hash mismatch")
  }
  genes <- jsonlite::read_json(file.path(directory, "genes.json"), simplifyVector = TRUE)
  cells <- jsonlite::read_json(file.path(directory, "cells.json"), simplifyVector = TRUE)
  shape <- as.integer(unlist(meta$shape))
  assert(identical(shape, c(length(genes), length(cells))), "Axis length mismatch")
  connection <- file(file.path(directory, "counts.f64"), "rb")
  on.exit(close(connection))
  values <- readBin(connection, "double", n = prod(shape), size = 8L, endian = "little")
  assert(length(values) == prod(shape) && file.info(file.path(directory, "counts.f64"))$size == prod(shape)*8, "Count payload length mismatch")
  x <- Matrix::Matrix(matrix(values, nrow = shape[[1]], dimnames = list(genes, cells)), sparse = TRUE)
  validate_counts(x)
  list(counts = as(x, "dgCMatrix"), metadata = meta)
}

fit_correct <- function(raw, depth, seed) {
  validate_counts(raw)
  assert(is.finite(depth) && depth > 0, "Invalid common correction depth")
  assert(requireNamespace("glmGamPoi", quietly = TRUE), "glmGamPoi required; fallback forbidden")
  RNGkind("Mersenne-Twister", "Inversion", "Rejection")
  set.seed(seed)
  future::plan(future::sequential)
  # Matrix dispatch preserves cells_step1 and the complete vst model. Initial
  # wrapper correction is disabled; final correction always uses raw counts.
  fit <- Seurat::SCTransform(
    object = raw, cell.attr = data.frame(row.names = colnames(raw)),
    vst.flavor = "v2", ncells = ncol(raw), n_genes = NULL,
    return.only.var.genes = FALSE, do.correct.umi = FALSE,
    vars.to.regress = NULL, latent.data = NULL, latent_var = "log_umi",
    min_cells = 5L, bin_size = 500L, do.scale = FALSE, do.center = FALSE,
    clip.range = c(-sqrt(ncol(raw)/30), sqrt(ncol(raw)/30)),
    seed.use = seed, verbose = TRUE
  )
  assert(identical(fit$arguments$method, "glmGamPoi_offset"), "Effective method is not glmGamPoi_offset")
  assert(identical(fit$cells_step1, colnames(raw)), "Actual fitting cells/order differ from requested cells")
  assert(identical(rownames(fit$cell_attr), colnames(raw)), "Cell-attribute order mismatch")
  assert(identical(fit$model_str, "y ~ log_umi"), "Unexpected regression formula")
  assert(is.null(fit$arguments$n_genes), "Gene subsampling enabled")
  expected_genes <- rownames(raw)[Matrix::rowSums(raw > 0) >= 5L]
  assert(setequal(rownames(fit$model_pars_fit), expected_genes), "Unexpected model gene availability")
  corrected <- sctransform::correct_counts(fit, umi = raw, scale_factor = depth, verbosity = 1)
  corrected_again <- sctransform::correct_counts(fit, umi = raw, scale_factor = depth, verbosity = 0)
  assert(identical(corrected, corrected_again), "Correction is not deterministic")
  assert(identical(rownames(corrected), expected_genes) && identical(colnames(corrected), colnames(raw)), "Correction axes changed")
  assert(all(is.finite(corrected@x) & corrected@x >= 0 & corrected@x == floor(corrected@x)), "Invalid corrected counts")
  # Independent scalar NB reconstruction checks the target depth, rather than
  # merely repeating calls to the same package function.
  observed_depth <- Matrix::colSums(raw)
  assert(identical(unname(fit$cell_attr$log_umi), unname(log10(observed_depth))), "Fit depth denominator changed")
  for (gene in rownames(corrected)) {
    pars <- fit$model_pars_fit[gene, ]
    old_mean <- exp(pars[["(Intercept)"]] + pars[["log_umi"]] * log10(observed_depth))
    new_mean <- exp(pars[["(Intercept)"]] + pars[["log_umi"]] * log10(depth))
    residual <- (as.numeric(raw[gene, ]) - old_mean) / sqrt(old_mean + old_mean^2/pars[["theta"]])
    expected <- pmax(0, round(new_mean + residual * sqrt(new_mean + new_mean^2/pars[["theta"]])))
    assert(all(as.numeric(corrected[gene, ]) == expected), "Independent common-depth reconstruction failed")
  }
  response <- log1p(corrected)
  assert(all(is.finite(response@x)), "Nonfinite response")
  # Fresh SCT layers contain only the final common-depth response. Preserve
  # the original fitted model separately and set correction-depth metadata.
  assay_fit <- fit
  assay_fit$arguments$sct.clip.range <- c(-sqrt(ncol(raw)/30), sqrt(ncol(raw)/30))
  assay <- Seurat::CreateSCTAssayObject(counts = corrected, SCTModel.list = assay_fit)
  assay <- SeuratObject::SetAssayData(assay, layer = "data", new.data = response)
  Seurat::SCTResults(assay, slot = "median_umi") <- depth
  object <- SeuratObject::CreateSeuratObject(counts = raw, assay = "RNA", min.cells = 0, min.features = 0)
  object[["SCT"]] <- assay
  SeuratObject::DefaultAssay(object) <- "SCT"
  extracted_counts <- SeuratObject::GetAssayData(object, assay = "SCT", layer = "counts")
  extracted_data <- SeuratObject::GetAssayData(object, assay = "SCT", layer = "data")
  assert(identical(extracted_counts, corrected), "SCT/counts extraction changed values or axes")
  assert(identical(extracted_data, log1p(extracted_counts)), "SCT/data != log1p(SCT/counts)")
  assert(identical(SeuratObject::GetAssayData(object, assay = "RNA", layer = "counts"), raw), "RNA counts changed")
  list(fit = fit, corrected = corrected, response = response, object = object,
       effective_genes = expected_genes)
}

run_validation <- function(args) {
  assert(length(args) == 5L, "Usage: sct_validation.R EXTERNAL_ENV INPUT_DIR OUTPUT_DIR DEPTH SEED")
  envroot <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
  .libPaths(c(file.path(envroot, "library"), .Library), include.site = FALSE)
  assert(all(startsWith(normalizePath(.libPaths(), winslash = "/"), envroot)), "Library isolation failure")
  assert(getRversion() == "4.5.3", "Wrong R version")
  versions <- c(Seurat="5.4.0", SeuratObject="5.4.0", sctransform="0.4.3", Matrix="1.7-4", glmGamPoi="1.22.0")
  for (pkg in names(versions)) assert(packageDescription(pkg, fields = "Version") == versions[[pkg]], paste("Version mismatch", pkg))
  assert(as.character(BiocManager::version()) == "3.22", "Wrong Bioconductor release")
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
