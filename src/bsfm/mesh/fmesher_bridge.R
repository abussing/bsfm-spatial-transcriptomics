# Narrow geometry/projector bridge. No FEM, covariance, fitting or legacy code.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==3L,getRversion()=="4.5.3")
root <- normalizePath(args[1],winslash="/",mustWork=TRUE)
work <- args[2]; output <- args[3]
lib <- normalizePath(file.path(root,"r-library"),winslash="/",mustWork=TRUE)
Sys.setenv(R_LIBS_USER=lib,R_LIBS_SITE=lib)
.libPaths(c(lib,.Library),include.site=FALSE)
stopifnot(identical(.libPaths(),normalizePath(c(lib,.Library),winslash="/")))
library(fmesher,lib.loc=lib);library(Matrix,lib.loc=lib);library(jsonlite,lib.loc=lib)
stopifnot(as.character(packageVersion("fmesher"))=="0.7.0")
options(warn=1)
withCallingHandlers({
  cfg <- jsonlite::read_json(file.path(work,"spec.json"),simplifyVector=TRUE)
  xy <- function(name) as.matrix(read.csv(file.path(work,name),header=FALSE))
  boundary <- xy("boundary.csv"); loc <- xy("locations.csv"); query <- xy("observations.csv")
  qboundary <- scan(file.path(work,"boundary-quality.txt"),quiet=TRUE)
  qloc <- scan(file.path(work,"location-quality.txt"),quiet=TRUE)
  stopifnot(length(qboundary)==nrow(boundary),length(qloc)==nrow(loc),all(qloc>0),all(qboundary>0))
  segm <- fm_segm(loc=boundary,idx=cbind(seq_len(nrow(boundary)),c(2:nrow(boundary),1L)),is.bnd=TRUE)
  mesh <- fm_rcdt_2d_inla(loc=loc,boundary=segm,extend=FALSE,cutoff=cfg$cutoff,
    quality.spec=list(segm=qboundary,loc=qloc),
    refine=list(min.angle=cfg$minimum_angle,max.edge=cfg$edge_cap,max.edge.extra=cfg$edge_cap))
  a <- as(fm_basis(mesh,loc=query),"CsparseMatrix")
  stopifnot(all(is.finite(a@x)),all(abs(rowSums(a)-1)<cfg$projector_tolerance))
  dir.create(output,recursive=TRUE,showWarnings=FALSE)
  writeBin(as.double(t(mesh$loc[,1:2])),file.path(output,"vertices.f64"),size=8,endian="little")
  writeBin(as.integer(t(mesh$graph$tv-1L)),file.path(output,"triangles.i32"),size=4,endian="little")
  writeMM(a,file.path(output,"projector.mtx"))
  write_json(list(vertices=nrow(mesh$loc),triangles=nrow(mesh$graph$tv),index_base=0L,
    axis_order=c("center_y","center_x"),fmesher=as.character(packageVersion("fmesher")),
    libraries=.libPaths()),file.path(output,"result.json"),auto_unbox=TRUE,pretty=TRUE)
},warning=function(w) { if(grepl("stack imbalance",conditionMessage(w),ignore.case=TRUE))stop(w) })
