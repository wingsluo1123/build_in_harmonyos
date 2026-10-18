## r-base 4.5.1.2 端到端消费者用例（rule12）
##
## 流程：生产者进程生成数据集并落盘 CSV → 通过 system2 派生一个独立的
## Rscript 子进程作为"真实消费者"（读取 CSV → 拟合线性模型 → 把系数与
## 预测值回写结果文件）→ 生产者回读结果文件并验证。
##
## 与纯断言测试的区别：跨越两个真实 R 进程，包含文件 IO（CSV/TSV/RDS 读写）、
## 统计引擎（lm/predict）、子进程调度与数据往返，覆盖一条完整的
## "生产-消费"数据流，而非仅对内存对象做 stopifnot 断言。

work <- commandArgs(TRUE)[1]
stopifnot(!is.na(work), dir.exists(work))

## ── 阶段 1：生产者生成数据集 ────────────────────────────────────────
set.seed(42)
n <- 200L
x <- seq(0, 10, length.out = n)
y <- 2 + 3 * x + rnorm(n, sd = 0.5)
dataset <- data.frame(x = x, y = y)
csv_path <- file.path(work, "dataset.csv")
write.csv(dataset, csv_path, row.names = FALSE)
stopifnot(file.exists(csv_path), file.info(csv_path)$size > 0)

## ── 阶段 2：独立 Rscript 子进程作为真实消费者 ──────────────────────
worker <- file.path(work, "consumer_worker.R")
writeLines(c(
  "args <- commandArgs(TRUE)",
  "data <- read.csv(args[1], stringsAsFactors = FALSE)",
  "stopifnot(identical(dim(data), c(200L, 2L)))",
  "fit <- lm(y ~ x, data = data)",
  "coefs <- coef(fit)",
  "pred <- predict(fit, newdata = data.frame(x = 10.0))",
  "saveRDS(fit, args[2])",
  "write.table(data.frame(intercept = coefs[['(Intercept)']],",
  "                     slope = coefs[['x']],",
  "                     prediction_at_10 = pred),",
  "            file = args[3], row.names = FALSE, sep = '\t', quote = FALSE)"
), worker)

rscript <- file.path(R.home("bin"), "Rscript")
stopifnot(file.exists(rscript))
model_path <- file.path(work, "model.rds")
result_path <- file.path(work, "result.tsv")
status <- system2(rscript,
                  c("--vanilla", shQuote(worker), shQuote(csv_path),
                    shQuote(model_path), shQuote(result_path)))
stopifnot(identical(status, 0L), file.exists(result_path),
          file.info(result_path)$size > 0)

## ── 阶段 3：回读消费者产出并验证（含 RDS 序列化往返） ──────────────
result <- read.table(result_path, header = TRUE)
stopifnot(identical(nrow(result), 1L),
          abs(result$intercept - 2) < 0.2,
          abs(result$slope - 3) < 0.05,
          abs(result$prediction_at_10 - 32) < 0.5)

## 消费者训练好的模型对象经 saveRDS 落盘、父进程 readRDS 还原后，
## 预测能力必须等价（序列化往返不丢失信息）
refit <- readRDS(model_path)
stopifnot(inherits(refit, "lm"),
          isTRUE(all.equal(unname(predict(refit, newdata = data.frame(x = 10.0))),
                           unname(result$prediction_at_10), tolerance = 1e-8)),
          isTRUE(all.equal(unname(coef(refit)),
                           c(result$intercept, result$slope), tolerance = 1e-8)))

cat("R_BASE_E2E_CONSUMER=PASS\n")
unlink(work, recursive = TRUE)
