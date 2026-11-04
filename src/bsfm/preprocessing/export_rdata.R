# Data-only bridge: explicit list object/fields, no normalization or historical code.
# Input, object, expression field, coordinate field, group field, staging directory.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==6)
e <- new.env(parent=baseenv());load(args[1],envir=e)
stopifnot(exists(args[2],envir=e,inherits=FALSE))
d <- get(args[2],envir=e,inherits=FALSE)
stopifnot(is.list(d))
x <- d[[args[3]]];xy <- d[[args[4]]];groups <- d[[args[5]]]
stopifnot(is.matrix(x),is.numeric(x),all(is.finite(x)),length(dim(x))==2)
stopifnot(!is.null(rownames(x)),!is.null(colnames(x)))
stopifnot(!anyDuplicated(rownames(x)),!anyDuplicated(colnames(x)))
stopifnot(all(nzchar(rownames(x))),all(nzchar(colnames(x))))
xy <- as.matrix(xy)
stopifnot(is.numeric(xy),identical(dim(xy),c(ncol(x),2L)),all(is.finite(xy)))
stopifnot(is.character(groups),length(groups)==ncol(x),!anyNA(groups),all(nzchar(groups)))
out <- args[6];stopifnot(dir.exists(out))
con <- file(file.path(out,'expression.f64'),'wb')
writeBin(as.double(x),con,size=8,endian='little');close(con)
write.csv(data.frame(gene=rownames(x)),file.path(out,'genes.csv'),row.names=FALSE)
write.csv(data.frame(cell=colnames(x),group=groups,axis0=xy[,1],axis1=xy[,2],
                     source_row=seq_len(ncol(x))-1L),file.path(out,'cells.csv'),row.names=FALSE)
writeLines(capture.output(sessionInfo()),file.path(out,'R-session.txt'))
