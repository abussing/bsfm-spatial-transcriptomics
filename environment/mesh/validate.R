# Tiny environment test only: no canonical coordinates or study geometry.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==2L,getRversion()=="4.5.3")
root <- normalizePath(args[1],winslash="/",mustWork=TRUE)
dest <- args[2]
if(dir.exists(dest)) stop("Fresh validation destination required")
dir.create(dest,recursive=TRUE)
lib <- normalizePath(file.path(root,"r-library"),winslash="/")
Sys.setenv(R_LIBS_USER=lib,R_LIBS_SITE=lib)
.libPaths(c(lib,.Library),include.site=FALSE)
stopifnot(identical(.libPaths(),normalizePath(c(lib,.Library),winslash="/")))
plan <- read.csv(file.path(root,"install-plan.csv"),stringsAsFactors=FALSE)
for(i in seq_len(nrow(plan))) {
  stopifnot(as.character(packageVersion(plan$package[i],lib.loc=lib))==
    as.character(package_version(plan$version[i])))
}
options(warn=1)
warnings_seen <- character()
withCallingHandlers({
  for(p in c("fmesher","sf","Matrix","jsonlite")) {
    library(p,character.only=TRUE,lib.loc=lib)
    stopifnot(startsWith(normalizePath(find.package(p),winslash="/"),paste0(lib,"/")))
  }
  stopifnot(as.character(packageVersion("fmesher"))=="0.7.0")
  xy <- rbind(c(0,0),c(1,0),c(1,1),c(0,1))
  bnd <- fmesher::fm_segm(loc=xy,idx=cbind(1:4,c(2:4,1)),is.bnd=TRUE)
  mesh <- fmesher::fm_rcdt_2d_inla(loc=matrix(c(.5,.5),ncol=2),boundary=bnd,
    extend=FALSE,cutoff=1e-12,refine=list(min.angle=21,max.edge=.6))
  v <- mesh$loc[,1:2,drop=FALSE]; tv <- mesh$graph$tv
  stopifnot(min(tv)==1L,max(tv)<=nrow(v),nrow(v)<200,nrow(tv)<400)
  q <- rbind(v[1,],colMeans(v[tv[1,1:2],,drop=FALSE]),colMeans(v[tv[1,],,drop=FALSE]))
  A <- as(fmesher::fm_basis(mesh,loc=q),"dgCMatrix")
  row_error <- max(abs(rowSums(A)-1)); coordinate_error <- max(abs(A%*%v-q))
  stopifnot(row_error<1e-12,coordinate_error<1e-12,min(A@x)>=-1e-12,
    abs(A[1,1]-1)<1e-12,max(abs(A[2,tv[1,1:2]]-.5))<1e-12,
    max(abs(A[3,tv[1,]]-1/3))<1e-12)
  Matrix::writeMM(A,file.path(dest,"projector.mtx"))
  restored <- as(Matrix::readMM(file.path(dest,"projector.mtx")),"CsparseMatrix")
  mm_error <- max(abs(as.matrix(restored)-as.matrix(A)))
  stopifnot(mm_error<1e-15)
  # Explicit row-major little-endian wire artifacts; internal R triangles are one-based.
  writeBin(as.double(t(v)),file.path(dest,"vertices.f64"),size=8,endian="little")
  writeBin(as.integer(t(tv-1L)),file.path(dest,"triangles.i32"),size=4,endian="little")
  writeBin(as.double(t(q)),file.path(dest,"queries.f64"),size=8,endian="little")
  writeBin(as.double(t(as.matrix(A))),file.path(dest,"projector.f64"),size=8,endian="little")
  ns <- loadedNamespaces()
  ns_paths <- vapply(ns,function(p)normalizePath(if(p=="base")find.package(p) else getNamespaceInfo(p,"path"),winslash="/"),character(1))
  base_names <- installed.packages(lib.loc=.Library)
  base_names <- rownames(base_names)[!is.na(base_names[,"Priority"]) & base_names[,"Priority"]=="base"]
  stopifnot(all(startsWith(ns_paths[!ns %in% base_names],paste0(lib,"/"))))
  result <- list(status="pass",scope="tiny synthetic environment validation only",
    axes=c("coordinate_0","coordinate_1"),coordinate_units="synthetic",
    wire_order="row_major",wire_byte_order="little",triangle_index_base=0L,
    r_internal_triangle_index_base=1L,vertices=nrow(v),triangles=nrow(tv),
    queries=nrow(q),projector_dim=dim(A),projector_nnz=length(A@x),
    row_sum_error=row_error,affine_error=coordinate_error,matrix_market_error=mm_error,
    libraries=.libPaths(),packages=as.list(vapply(c("fmesher","sf","Matrix","jsonlite"),
       function(p)as.character(packageVersion(p)),character(1))),
    package_paths=as.list(vapply(c("fmesher","sf","Matrix","jsonlite"),find.package,character(1))),
    loaded_namespace_paths=as.list(ns_paths),
    sf_external=as.list(sf::sf_extSoftVersion()),warnings=warnings_seen)
  jsonlite::write_json(result,file.path(dest,"result.json"),pretty=TRUE,auto_unbox=TRUE,digits=17)
  writeLines(capture.output(sessionInfo()),file.path(dest,"session.txt"))
},warning=function(w) {
  warnings_seen <<- c(warnings_seen,conditionMessage(w))
  if(grepl("stack imbalance",conditionMessage(w),ignore.case=TRUE))stop(w)
})
cat("SYNTHETIC_ENVIRONMENT_PASS\n")
