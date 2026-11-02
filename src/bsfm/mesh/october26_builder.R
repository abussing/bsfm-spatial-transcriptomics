# Conservative port of A/F build_preview.R, SHA-256
# a343fcb0e819976b3982f6d1d77e89faa021c5ccd13dc508f8170f428832a66f.
# Geometry/adaptation only; plotting and the 19-section loop are omitted.
# Coordinates and inherited boundary ordering are deliberately not canonicalized.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==6L)
lib <- normalizePath(file.path(args[1], 'r-library'), winslash='/')
.libPaths(c(lib, .Library), include.site=FALSE)
suppressPackageStartupMessages({library(fmesher);library(Matrix);library(sf);library(jsonlite)})
for (pkg in c('fmesher','Matrix','sf','jsonlite')) {
  stopifnot(startsWith(normalizePath(find.package(pkg), winslash='/'), paste0(lib,'/')))
}
cfg <- fromJSON(args[2])
# fmesher 0.7.0's native reader requires NumericVector, not IntegerVector;
# JSON 25 otherwise leaves the native 21-degree default in effect.
cfg$minimum_angle <- as.double(cfg$minimum_angle)
stopifnot(as.character(packageVersion('fmesher'))==cfg$fmesher_version)
cells <- read.csv(args[3]); xy <- as.matrix(cells[,c('x','y')])
oldv <- as.matrix(read.csv(args[4])); oldt <- as.matrix(read.csv(args[5]))+1L
out <- args[6]; if(dir.exists(out)) stop('Refusing existing output')
dir.create(out)
stopifnot(ncol(xy)==2L, all(is.finite(xy)), ncol(oldv)==2L,
          all(is.finite(oldv)), ncol(oldt)==3L, all(oldt>=1L), all(oldt<=nrow(oldv)))
edge_set <- function(tv) {
  ee <- rbind(tv[,c(1,2)],tv[,c(2,3)],tv[,c(3,1)])
  ss <- t(apply(ee,1,sort)); key <- paste(ss[,1],ss[,2],sep=':')
  ee[!(duplicated(key)|duplicated(key,fromLast=TRUE)),,drop=FALSE]
}
be <- edge_set(oldt); bi <- sort(unique(as.vector(be)))
outer <- fm_segm(loc=oldv[bi,,drop=FALSE],idx=matrix(match(be,bi),ncol=2),is.bnd=TRUE)
hulls <- lapply(cfg$padding,function(pad) fm_nonconvex_hull(xy,convex=pad,
  concave=cfg$concave,method='fm',format='sf',resolution=cfg$resolution,eps=cfg$eps))
contours <- lapply(hulls,fm_as_segm); bounds <- c(contours,list(outer))
h <- cfg$initial_h; attempts <- list(); chosen <- NULL
for(attempt in seq_len(cfg$maximum_attempts)) {
  edges <- c(h,pmax(cfg$edge_floors,cfg$edge_multipliers*h))
  stopifnot(all(diff(edges)>0)); mesh <- NULL
  for(layer in seq_along(bounds)) {
    kept <- if(is.null(mesh)) NULL else fm_segm(fm_segm(mesh,boundary=TRUE),fm_segm(mesh,boundary=FALSE),is.bnd=FALSE)
    locs <- if(is.null(mesh)) xy else rbind(xy,mesh$loc[,1:2])
    mesh <- fm_rcdt_2d(loc=locs,boundary=bounds[[layer]],interior=kept,
      cutoff=cfg$cutoff_multiplier*h,extend=FALSE,
      refine=list(min.angle=cfg$minimum_angle,max.edge=edges[layer],max.edge.extra=edges[layer]))
  }
  A <- fm_basis(mesh,loc=xy); A@x[abs(A@x)<cfg$projector_zero_threshold] <- 0; A <- drop0(A)
  active <- which(colSums(abs(A))>0)
  attempts[[attempt]] <- list(h=h,edges=edges,active=length(active),total=mesh$n)
  cand <- list(mesh=mesh,A=A,active=active,edges=edges,h=h)
  if(is.null(chosen)||abs(length(active)-cfg$target_active)<abs(length(chosen$active)-cfg$target_active)) chosen <- cand
  if(length(active)>=cfg$acceptable_active[1] && length(active)<=cfg$acceptable_active[2]) break
  h <- h*sqrt(length(active)/cfg$target_active)
}
mesh <- chosen$mesh; A <- chosen$A; v <- mesh$loc[,1:2]; tv <- mesh$graph$tv
stopifnot(max(abs(rowSums(A)-1))<cfg$projector_tolerance,
  max(abs(A%*%v-xy))<cfg$projector_tolerance,min(A@x)>-cfg$projector_tolerance)
write.csv(data.frame(x=v[,1],y=v[,2]),file.path(out,'mesh_loc.csv'),row.names=FALSE)
write.csv(data.frame(v1=tv[,1]-1L,v2=tv[,2]-1L,v3=tv[,3]-1L),file.path(out,'mesh_tv.csv'),row.names=FALSE)
writeMM(A,file.path(out,'A_proj.mtx'))
saveRDS(mesh,file.path(out,'mesh.rds'))
writeBin(as.double(t(v)),file.path(out,'vertices.f64'),size=8,endian='little')
writeBin(as.integer(t(tv-1L)),file.path(out,'triangles.i32'),size=4,endian='little')
writeLines(toJSON(list(attempts=attempts,chosen_h=chosen$h,edges=chosen$edges,
  vertices=nrow(v),triangles=nrow(tv),active=length(chosen$active),index_base=0,
  axis_order=cfg$axis_order,units=cfg$units,library_paths=.libPaths(),
  packages=lapply(c('fmesher','sf','Matrix','jsonlite'),function(p) list(name=p,version=as.character(packageVersion(p))))),
  pretty=TRUE,auto_unbox=TRUE,digits=16),file.path(out,'geometry.json'))
writeLines(capture.output(sessionInfo()),file.path(out,'session.txt'))
