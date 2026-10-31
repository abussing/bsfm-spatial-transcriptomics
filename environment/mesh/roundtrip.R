# Read only the tiny synthetic Python round-trip products, never real meshes.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==2L,getRversion()=="4.5.3")
lib <- normalizePath(file.path(args[1],"r-library"),winslash="/")
Sys.setenv(R_LIBS_USER=lib,R_LIBS_SITE=lib)
.libPaths(c(lib,.Library),include.site=FALSE)
library(Matrix,lib.loc=lib)
for(i in 1:2) {
  dest <- file.path(args[2],paste0("fresh-",i))
  a <- as(readMM(file.path(dest,"projector.mtx")),"CsparseMatrix")
  b <- as(readMM(file.path(dest,"python-projector.mtx")),"CsparseMatrix")
  stopifnot(identical(dim(a),dim(b)),identical(a@p,b@p),identical(a@i,b@i),identical(a@x,b@x))
}
cat("PYTHON_TO_R_SPARSE_ROUNDTRIP_EXACT\n")
