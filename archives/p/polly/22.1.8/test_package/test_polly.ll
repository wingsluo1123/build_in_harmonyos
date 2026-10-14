; test_polly.ll — 供 test_package 用 opt 加载 LLVMPolly.so 验证 SCoP 检测。
; 单层 affine 循环 for (i = 0; i < 1024; i++) A[i] = B[c]; 是 Polly 可检测的标准 SCoP
; （参照上游 polly/test/ScopDetect/aliasing_parametric_simple_1.ll）。
target datalayout = "e-m:e-i64:64-f80:128-n8:16:32:64-S128"

define void @jd(ptr %A, ptr %B, i32 %c) {
entry:
  br label %for.cond

for.cond:
  %indvars.iv = phi i64 [ %indvars.iv.next, %for.inc ], [ 0, %entry ]
  %exitcond = icmp ne i64 %indvars.iv, 1024
  br i1 %exitcond, label %for.body, label %for.end

for.body:
  %idxprom = sext i32 %c to i64
  %arrayidx = getelementptr inbounds i32, ptr %B, i64 %idxprom
  %tmp = load i32, ptr %arrayidx, align 4
  %arrayidx2 = getelementptr inbounds i32, ptr %A, i64 %indvars.iv
  store i32 %tmp, ptr %arrayidx2, align 4
  br label %for.inc

for.inc:
  %indvars.iv.next = add nuw nsw i64 %indvars.iv, 1
  br label %for.cond

for.end:
  ret void
}
