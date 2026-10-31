# Local authenticated archives only. No network resolution or user libraries.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==1L, getRversion()=="4.5.3")
root <- normalizePath(args[1],winslash="/",mustWork=TRUE)
lib <- file.path(root,"r-library")
dir.create(lib,showWarnings=FALSE)
Sys.setenv(R_LIBS_USER=lib,R_LIBS_SITE=lib)
.libPaths(c(lib,.Library),include.site=FALSE)
stopifnot(identical(.libPaths(),normalizePath(c(lib,.Library),winslash="/")))
plan <- read.csv(file.path(root,"install-plan.csv"),stringsAsFactors=FALSE)
constraints <- read.csv(file.path(root,"dependency-constraints.csv"),stringsAsFactors=FALSE)
for (i in seq_len(nrow(constraints))) {
  r <- constraints[i,]
  cmp <- compareVersion(r$actual,r$required)
  pass <- switch(r$operator,">="=cmp>=0,"<="=cmp<=0,">"=cmp>0,"<"=cmp<0,"=="=cmp==0,stop("Unknown operator"))
  if (!pass) stop("Unsatisfied dependency: ",r$package," -> ",r$dependency)
}
for (i in seq_len(nrow(plan))) {
  p <- plan[i,]
  dest <- file.path(lib,p$package)
  if (dir.exists(dest)) {
    stopifnot(as.character(packageVersion(p$package,lib.loc=lib))==as.character(package_version(p$version)))
  } else {
    install.packages(p$binary,lib=lib,repos=NULL,type="win.binary",quiet=FALSE)
  }
  stopifnot(as.character(packageVersion(p$package,lib.loc=lib))==as.character(package_version(p$version)))
}
write.csv(installed.packages(lib.loc=lib),file.path(root,"installed-R-packages.csv"),row.names=FALSE)
writeLines(capture.output(sessionInfo()),file.path(root,"installation-session.txt"))
cat("INSTALL_COMPLETE",nrow(plan),"packages\n")
