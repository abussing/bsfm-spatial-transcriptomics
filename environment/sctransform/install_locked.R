# Install authenticated Windows archives; optional second argument lists packages
# verified by audit_installed.py. No dependency resolution or package downloads.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) %in% c(1L, 2L), getRversion() == "4.5.3")
root <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
lib <- file.path(root, "library")
dir.create(lib, showWarnings = FALSE)
.libPaths(c(lib, .Library), include.site = FALSE)
stopifnot(all(startsWith(normalizePath(.libPaths(), winslash = "/"), root)))
options(timeout = 120, repos = NULL)
archives <- list.files(file.path(root, "downloads/binary"), "[.]zip$", full.names = TRUE)
stopifnot(length(archives) > 0L, file.exists(file.path(root, "source-lock.json")))
verified <- if (length(args) == 2L) readLines(args[[2]]) else NULL
complete <- vapply(archives, function(path) {
  pkg <- sub("_.*", "", basename(path))
  desc <- file.path(lib, pkg, "DESCRIPTION")
  if (!file.exists(desc) || !file.exists(file.path(lib, pkg, "Meta/package.rds"))) return(FALSE)
  version <- tryCatch(read.dcf(desc)[1, "Version"], error = function(e) NA_character_)
  if (is.na(version)) return(FALSE)
  identical(basename(path), paste0(pkg, "_", version, ".zip")) &&
    if (is.null(verified)) isTRUE(tools::checkMD5sums(dir = file.path(lib, pkg))) else pkg %in% verified
}, logical(1))
cat("Already complete:", sum(complete), "remaining:", sum(!complete), "\n")
if (any(!complete)) install.packages(archives[!complete], lib = lib, repos = NULL, type = "win.binary")
lock <- jsonlite::read_json(file.path(root, "source-lock.json"), simplifyVector = FALSE)
for (entry in lock$packages) {
  stopifnot(packageDescription(entry$package, lib.loc = lib, fields = "Version") == entry$version)
  stopifnot(digest::digest(file = entry$binary$path, algo = "sha256") == entry$binary$sha256)
}
versions <- c(Seurat="5.4.0", SeuratObject="5.4.0", sctransform="0.4.3", Matrix="1.7-4", glmGamPoi="1.22.0")
for (pkg in names(versions)) stopifnot(packageDescription(pkg, fields = "Version") == versions[[pkg]])
stopifnot(as.character(BiocManager::version()) == "3.22")
invisible(lapply(names(versions), loadNamespace))
writeLines(capture.output(sessionInfo()), file.path(root, "installed-session.txt"))
write.csv(installed.packages(lib.loc = .libPaths()), file.path(root, "installed-packages.csv"), row.names = FALSE)
options(repos = c(CRAN="https://cran.r-project.org", BioCsoft="https://bioconductor.posit.co/packages/3.22/bioc"))
renv::snapshot(project = root, library = .libPaths(), lockfile = file.path(root, "renv.lock"), type = "all", prompt = FALSE, force = TRUE)
cat("Installed and verified frozen environment; lockfile written\n")
