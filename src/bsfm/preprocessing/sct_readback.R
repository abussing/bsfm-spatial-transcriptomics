# Independent saved-model readback/recorrection. Never fits SCTransform.
script <- sub("^--file=", "", grep("^--file=", commandArgs(), value=TRUE)[[1]])
source(file.path(dirname(normalizePath(script)), "sct_core.R"))
args <- commandArgs(trailingOnly=TRUE)
assert(length(args) %in% c(5L, 6L), "Usage: ENV INPUT FIT OUTPUT DEPTH [ACCEPTED_OUTPUT]")
configure_environment(args[[1]])
input <- load_input(args[[2]])
fit <- readRDS(args[[3]])
output <- args[[4]]
assert(!dir.exists(output), "Readback output already exists")
dir.create(output, recursive=TRUE)
raw <- input$counts
assert(identical(fit$cells_step1, colnames(raw)), "Saved fit cells/order differ")
assert(identical(rownames(fit$cell_attr), colnames(raw)), "Saved fit cell attributes differ")
assert(identical(rownames(fit$model_pars_fit), rownames(raw)), "Saved fit lacks full gene axis")
assert(fit$arguments$method == "glmGamPoi_offset", "Saved fit method changed")
assert(fit$arguments$vst.flavor == "v2" && is.null(fit$arguments$n_genes), "Saved fit specification changed")
assert(fit$arguments$n_cells == ncol(raw) && fit$model_str == "y ~ log_umi", "Saved fitting population/formula changed")
assert(identical(unname(fit$cell_attr$log_umi), unname(log10(Matrix::colSums(raw)))), "Saved raw depth changed")
warnings <- character()
corrected <- withCallingHandlers(
  sctransform::correct_counts(fit, umi=raw, scale_factor=as.numeric(args[[5]]), verbosity=0),
  warning=function(w) { warnings <<- c(warnings, conditionMessage(w)) })
response <- log1p(corrected)
assert(identical(dimnames(corrected), dimnames(raw)), "Readback correction axes differ")
assert(all(is.finite(corrected@x) & corrected@x >= 0 & corrected@x == floor(corrected@x)), "Invalid recorrection")
assert(all(is.finite(response@x)), "Invalid log1p")
assert(!any(grepl("stack imbalance", warnings, ignore.case=TRUE)), "Stack imbalance in readback")
signature <- list(model_pars=fit$model_pars, model_pars_fit=fit$model_pars_fit,
                  cells_step1=fit$cells_step1, corrected=corrected, response=response)
hashes <- lapply(signature, digest::digest, algo="sha256", serializeVersion=3)
equivalence <- NULL
if (length(args) == 6L) {
  old <- args[[6]]
  old_fit <- readRDS(file.path(old, "fit.rds"))
  old_c <- readRDS(file.path(old, "corrected-counts.rds"))
  old_l <- readRDS(file.path(old, "log1p-response.rds"))
  equivalence <- list(corrected=identical(corrected, old_c),
    response=identical(response, old_l), fitting_cells=identical(fit$cells_step1, old_fit$cells_step1),
    genes=identical(rownames(corrected), rownames(old_c)),
    effective_arguments=identical(fit$arguments, old_fit$arguments))
  assert(all(unlist(equivalence)), "Accepted artifact equivalence failed")
}
# Canonical logical C-order genes x cells bytes, independent of RDS serialization.
for (name in c("corrected", "response")) {
  connection <- file(file.path(output, paste0(name, ".f64")), "wb")
  writeBin(as.vector(t(as.matrix(get(name)))), connection, size=8L, endian="little")
  close(connection)
}
jsonlite::write_json(fit$cells_step1, file.path(output, "fitting-cells.json"), auto_unbox=FALSE)
jsonlite::write_json(rownames(corrected), file.path(output, "genes.json"), auto_unbox=FALSE)
report <- list(status="pass", schema="bsfm.sct-saved-model-readback.v1",
  depth=as.numeric(args[[5]]), effective_arguments=fit$arguments, semantic_sha256=hashes,
  warnings=warnings, accepted_equivalence=equivalence,
  payload_sha256=lapply(c("corrected", "response"), function(n)
    digest::digest(file=file.path(output,paste0(n,".f64")),algo="sha256")))
jsonlite::write_json(report, file.path(output, "report.json"), auto_unbox=TRUE,
                    pretty=TRUE, null="null", digits=NA)
cat("PASS: independent saved-fit recorrection and canonical payload export\n")
