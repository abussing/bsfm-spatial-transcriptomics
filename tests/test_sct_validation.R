# Run with isolated Rscript --vanilla tests/test_sct_validation.R REPO_ROOT
repo <- commandArgs(trailingOnly = TRUE)[[1]]
source(file.path(repo, "src/bsfm/preprocessing/sct_validation.R"))
raw <- Matrix::Matrix(matrix(c(1,2,3,4,5,6), 2,
  dimnames = list(c("a","b"), c("c1","c2","c3"))), sparse=TRUE)
validate_counts(raw)
expect_failure <- function(x) stopifnot(inherits(try(validate_counts(x), silent=TRUE), "try-error"))
negative <- raw; negative[1,1] <- -1; expect_failure(negative)
fraction <- raw; fraction[1,1] <- .5; expect_failure(fraction)
nonfinite <- raw; nonfinite[1,1] <- Inf; expect_failure(nonfinite)
zero <- raw; zero[,1] <- 0; expect_failure(zero)
duplicate <- raw; colnames(duplicate) <- c("c1","c1","c3"); expect_failure(duplicate)
missing <- raw; rownames(missing) <- NULL; expect_failure(missing)
cat("PASS: R count validation, negative/fractional/nonfinite/zero/duplicate/missing failures\n")
