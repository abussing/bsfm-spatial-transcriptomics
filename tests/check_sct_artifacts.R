# Read back the actual saved smoke artifacts, not just in-memory producer values.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2L)
.libPaths(c(file.path(args[[1]], "library"), .Library), include.site = FALSE)
directory <- args[[2]]
object <- readRDS(file.path(directory, "assays.rds"))
fit <- readRDS(file.path(directory, "fit.rds"))
counts <- readRDS(file.path(directory, "corrected-counts.rds"))
response <- readRDS(file.path(directory, "log1p-response.rds"))
raw <- SeuratObject::GetAssayData(object, assay = "RNA", layer = "counts")
stopifnot(identical(dim(counts), c(300L,20719L)), identical(response, log1p(counts)))
stopifnot(identical(counts, SeuratObject::GetAssayData(object, assay="SCT", layer="counts")))
stopifnot(identical(response, SeuratObject::GetAssayData(object, assay="SCT", layer="data")))
stopifnot(identical(fit$cells_step1, colnames(raw)))
stopifnot(all(is.finite(counts@x)), all(is.finite(response@x)))
stopifnot(Seurat::SCTResults(object[["SCT"]], slot="median_umi") == 124)
reconstructed <- sctransform::correct_counts(fit, umi=raw, scale_factor=124, verbosity=0)
stopifnot(identical(counts, reconstructed))
result <- list(schema="bsfm.sct-artifact-readback.v1", status="pass",
               cells=20719L, input_genes=nrow(raw), SCT_model_genes=nrow(fit$model_pars_fit),
               initial_parameter_genes=nrow(fit$model_pars),
               exact_serialized_layer_equality=TRUE, exact_saved_model_recorrection=TRUE,
               recorded_correction_depth=124)
jsonlite::write_json(result, file.path(directory, "readback.json"), auto_unbox=TRUE, pretty=TRUE)
cat("PASS: saved S00 objects, layer equality and model recorrection\n")
